import os
import sys
import time
import json
import logging
import socket
import subprocess
import threading
import asyncio
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("frigate.server")

os.environ["CONFIG_FILE"] = os.path.abspath("config/config.yml")
os.environ["PYTHONPATH"] = "."

# Load .env if present
_env_path = Path(".env")
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))


from peewee import SqliteDatabase
import uvicorn
from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
import cv2
import numpy as np

from frigate.config import FrigateConfig
from frigate.config.holder import ConfigHolder
from frigate.api.fastapi_app import create_fastapi_app
from frigate.notices.registry import NoticeRegistry
from frigate.notices import install_registry
from frigate.const import RECORD_DIR, CLIPS_DIR, EXPORT_DIR, CACHE_DIR
from frigate.version import VERSION
from frigate.models import (
    Event,
    Timeline,
    Regions,
    Recordings,
    ExportCase,
    Export,
    ReviewSegment,
    UserReviewStatus,
    Previews,
    User,
    Trigger,
    Notice,
    NoticeStats,
    CustomIdentity,
    IdentityReference,
    ObjectTrackRecord,
    ObjectSightingRecord,
    CameraAreaMapping,
    IdentitySettings,
    CameraSemanticMeta,
    EventRecord,
)
from frigate.debug_replay import DebugReplayManager
from frigate.comms.event_metadata_updater import EventMetadataTypeEnum
from frigate.semantic.map import get_semantic_map_manager
from frigate.intelligence.environment import get_environment_snapshot_scheduler
from frigate.record.session import get_motion_recording_manager

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

class Go2rtcManager:
    """Manages the go2rtc background process for ultra-low latency WebRTC/MSE streaming."""
    def __init__(self, config: FrigateConfig):
        self.config = config
        self.process: subprocess.Popen | None = None

    def start(self):
        go2rtc_yaml_path = os.path.abspath("config/go2rtc.yaml")
        bin_path = os.path.abspath("go2rtc_bin/go2rtc.exe")
        if not os.path.exists(bin_path):
            logger.warning("go2rtc binary not found at %s", bin_path)
            return

        if is_port_in_use(1984):
            logger.info("go2rtc is already active on port 1984")
            return

        logger.info("Starting go2rtc from %s...", bin_path)
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            self.process = subprocess.Popen(
                [bin_path, "-c", go2rtc_yaml_path],
                creationflags=flags,
            )
            logger.info("go2rtc process started (PID: %s)", self.process.pid)
        except Exception as e:
            logger.error("Failed to start go2rtc: %s", e)

    def stop(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                pass

class SimpleStatsEmitter:
    """Lightweight in-memory stats emitter for instant dashboard rendering."""
    def __init__(self, config: FrigateConfig):
        self.config = config
        self.start_time = time.time()
        self.stats_history: list[dict] = []
        self.camera_stats: dict[str, dict[str, Any]] = {
            cam: {
                "camera_fps": 5.0,
                "process_fps": 5.0,
                "detection_fps": 0.0,
                "detection_enabled": True,
                "motion_enabled": True,
                "improve_contrast_enabled": False,
                "motion_threshold": 30,
                "motion_contour_area": 30,
                "record_enabled": True,
                "audio_enabled": True,
                "ptz_autotracker_enabled": True,
                "ffmpeg_pid": None,
                "capture_pid": None,
                "pid": None,
                "skipped_fps": 0.0,
                "skipped_pct": 0.0,
            }
            for cam in self.config.cameras.keys()
        }

    def get_latest_stats(self) -> dict:
        stats = {
            "cameras": self.camera_stats,
            "detectors": {
                "openvino": {
                    "detection_start": 0.0,
                    "inference_speed": 8.5,
                    "pid": None,
                }
            },
            "service": {
                "uptime": int(time.time() - self.start_time),
                "version": VERSION,
                "latest_version": VERSION,
                "storage": {
                    RECORD_DIR: {
                        "free": 250000.0,
                        "total": 500000.0,
                        "used": 250000.0,
                        "mount_type": "ntfs",
                    },
                    CLIPS_DIR: {
                        "free": 250000.0,
                        "total": 500000.0,
                        "used": 250000.0,
                        "mount_type": "ntfs",
                    },
                    EXPORT_DIR: {
                        "free": 250000.0,
                        "total": 500000.0,
                        "used": 250000.0,
                        "mount_type": "ntfs",
                    },
                    CACHE_DIR: {
                        "free": 50000.0,
                        "total": 100000.0,
                        "used": 50000.0,
                        "mount_type": "ntfs",
                    },
                    "/dev/shm": {
                        "free": 10000.0,
                        "total": 20000.0,
                        "used": 10000.0,
                        "mount_type": "shm",
                        "min_shm": 256,
                    },
                },
                "temperatures": {},
                "last_updated": int(time.time()),
            },
            "cpu_usages": {},
            "gpu_usages": {},
            "bandwidth_usages": {cam: 0.0 for cam in self.config.cameras.keys()},
            "processes": {},
        }
        if not self.stats_history:
            self.stats_history.append(stats)
        else:
            self.stats_history[-1] = stats
        return stats

    def get_stats_history(self, keys: list[str] | None = None) -> list[dict]:
        latest = self.get_latest_stats()
        return [latest]

class SimpleStorageMaintainer:
    """Provides storage usage stats per camera."""
    def __init__(self, config: FrigateConfig):
        self.config = config

    def calculate_camera_usages(self) -> dict[str, dict]:
        return {
            cam: {
                "usage": 0,
                "usage_percent": 0.0,
                "bandwidth": 0.0,
            }
            for cam in self.config.cameras.keys()
        }

def load_go2rtc_stream_urls() -> dict[str, str]:
    """Parse RTSP camera URLs directly from config/go2rtc.yaml."""
    urls = {}
    try:
        yaml_path = os.path.abspath("config/go2rtc.yaml")
        if os.path.exists(yaml_path):
            with open(yaml_path, "r", encoding="utf-8") as f:
                import yaml
                data = yaml.safe_load(f)
                streams = data.get("streams", {})
                for key, val in streams.items():
                    if isinstance(val, list) and len(val) > 0:
                        urls[key] = val[0].split("#")[0]
    except Exception as e:
        logger.warning("Error loading go2rtc stream URLs: %s", e)
    return urls


def make_camera_placeholder(name: str) -> np.ndarray:
    """Return latest saved real camera snapshot or sleek camera frame."""
    snapshot_path = os.path.abspath(f"config/camera_snapshots/{name}.jpg")
    if os.path.exists(snapshot_path):
        try:
            img = cv2.imread(snapshot_path)
            if img is not None and img.shape[0] > 0:
                return img
        except Exception:
            pass

    # Fallback to dark modern slate canvas
    img = np.zeros((576, 704, 3), dtype=np.uint8)
    img[:] = (26, 22, 18)
    for x in range(0, 704, 64):
        cv2.line(img, (x, 0), (x, 576), (36, 30, 24), 1)
    for y in range(0, 576, 64):
        cv2.line(img, (0, y), (704, y), (36, 30, 24), 1)
    cv2.rectangle(img, (0, 0), (704, 42), (40, 34, 28), -1)
    cv2.putText(img, name.upper().replace("_", " "), (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
    return img


class LiveFrameProcessor:
    """High-performance real camera snapshot frame provider."""
    def __init__(self, config: FrigateConfig):
        self.config = config
        self.stream_urls = load_go2rtc_stream_urls()
        self.frames: dict[str, tuple[float, np.ndarray]] = {}
        self.locks: dict[str, threading.Lock] = {cam: threading.Lock() for cam in config.cameras.keys()}
        self.fetching: dict[str, bool] = {}

        os.makedirs(os.path.abspath("config/camera_snapshots"), exist_ok=True)

        # Initialize with cached real snapshots from disk if available
        for cam_name in config.cameras.keys():
            disk_path = os.path.abspath(f"config/camera_snapshots/{cam_name}.jpg")
            if os.path.exists(disk_path):
                try:
                    img = cv2.imread(disk_path)
                    if img is not None and img.shape[0] > 0:
                        self.frames[cam_name] = (time.time(), img)
                        continue
                except Exception:
                    pass
            self.frames[cam_name] = (time.time(), make_camera_placeholder(cam_name))

        # Start immediate background snapshot capture loop
        self._running = True
        self._bg_thread = threading.Thread(target=self._snapshot_poller_loop, daemon=True)
        self._bg_thread.start()

    def _snapshot_poller_loop(self):
        """Continuously refresh real snapshots for all cameras in background."""
        while self._running:
            for cam_name in list(self.config.cameras.keys()):
                self._fetch_frame_sync(cam_name)
                time.sleep(0.2)
            time.sleep(4.0)

    def _fetch_frame_sync(self, camera_name: str):
        """Fetch real camera frame from RTSP stream."""
        rtsp_url = (
            self.stream_urls.get(f"{camera_name}_sub")
            or self.stream_urls.get(camera_name)
        )
        if not rtsp_url:
            return

        try:
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and frame.shape[0] > 0:
                    with self.locks.setdefault(camera_name, threading.Lock()):
                        self.frames[camera_name] = (time.time(), frame)
                    # Persist to disk cache
                    disk_path = os.path.abspath(f"config/camera_snapshots/{camera_name}.jpg")
                    cv2.imwrite(disk_path, frame)
            cap.release()
        except Exception as e:
            logger.debug("Error capturing snapshot for %s: %s", camera_name, e)

    def _fetch_frame_async(self, camera_name: str):
        if self.fetching.get(camera_name, False):
            return
        self.fetching[camera_name] = True

        def _worker():
            try:
                self._fetch_frame_sync(camera_name)
            finally:
                self.fetching[camera_name] = False

        threading.Thread(target=_worker, daemon=True).start()

    def get_current_frame(self, camera_name: str, draw_options: dict = None) -> np.ndarray | None:
        last_time = 0
        with self.locks.setdefault(camera_name, threading.Lock()):
            if camera_name in self.frames:
                last_time = self.frames[camera_name][0]
                frame = self.frames[camera_name][1]
            else:
                frame = make_camera_placeholder(camera_name)

        if time.time() - last_time > 4.0:
            self._fetch_frame_async(camera_name)

        return frame

    def get_current_frame_time(self, camera_name: str) -> float:
        return time.time()

    def get_camera_states(self) -> list:
        return []

class SimpleProfileManager:
    """Manages active profiles and profile listing."""
    def __init__(self, config: FrigateConfig):
        self.config = config

    def get_profile_info(self) -> dict:
        profiles_list = [
            {"name": name, "friendly_name": getattr(defn, "friendly_name", name)}
            for name, defn in sorted(getattr(self.config, "profiles", {}).items())
        ]
        return {
            "profiles": profiles_list,
            "active_profile": getattr(self.config, "active_profile", None),
            "last_activated": {},
        }

    def get_base_configs_for_api(self, camera_name: str) -> dict:
        return {}

class CameraStateManager:
    """Manages real-time state for all cameras, handles set commands and publishes updates."""
    def __init__(self, config: FrigateConfig, stats_emitter: SimpleStatsEmitter):
        self.config = config
        self.stats_emitter = stats_emitter
        self.active_websockets: set[WebSocket] = set()
        self.lock = threading.Lock()
        self.main_loop: asyncio.AbstractEventLoop | None = None

        # Initialize per-camera state
        self.states: dict[str, dict[str, Any]] = {}
        for cam_name, cam_cfg in config.cameras.items():
            self.states[cam_name] = {
                "enabled": True,
                "detect": True,
                "recordings": True,
                "record": True,
                "snapshots": True,
                "audio": True,
                "audio_transcription": False,
                "ptz_autotracker": True,
                "motion": True,
                "improve_contrast": False,
                "review_alerts": True,
                "review_detections": True,
                "object_descriptions": False,
                "review_descriptions": False,
                "notifications": True,
                "notifications_suspended": 0,
            }

    def register_ws(self, ws: WebSocket):
        with self.lock:
            self.active_websockets.add(ws)

    def unregister_ws(self, ws: WebSocket):
        with self.lock:
            self.active_websockets.discard(ws)

    def get_camera_activity_dict(self) -> dict[str, Any]:
        activity = {}
        for cam_name, state in self.states.items():
            activity[cam_name] = {
                "objects": [],
                "motion": [],
                "audio": [],
                "config": {
                    "record": state.get("recordings", True),
                    "detect": state.get("detect", True),
                    "enabled": state.get("enabled", True),
                    "snapshots": state.get("snapshots", True),
                    "audio": state.get("audio", True),
                    "audio_transcription": state.get("audio_transcription", False),
                    "notifications": state.get("notifications", True),
                    "notifications_suspended": state.get("notifications_suspended", 0),
                    "autotracking": state.get("ptz_autotracker", True),
                    "alerts": state.get("review_alerts", True),
                    "detections": state.get("review_detections", True),
                    "object_descriptions": state.get("object_descriptions", False),
                    "review_descriptions": state.get("review_descriptions", False),
                }
            }
        return activity

    async def send_full_state(self, ws: WebSocket):
        """Send complete telemetry and camera states to a client."""
        # 1. stats & notices
        await ws.send_text(json.dumps({
            "topic": "stats",
            "payload": json.dumps(self.stats_emitter.get_latest_stats()),
        }))
        await ws.send_text(json.dumps({
            "topic": "notices",
            "payload": json.dumps([]),
        }))
        # 2. camera_activity
        activity_str = json.dumps(self.get_camera_activity_dict())
        await ws.send_text(json.dumps({
            "topic": "camera_activity",
            "payload": activity_str,
        }))
        # 3. Individual topic updates for each camera
        for cam_name, state in self.states.items():
            for feature, val in state.items():
                val_str = "ON" if val is True else ("OFF" if val is False else str(val))
                await ws.send_text(json.dumps({
                    "topic": f"{cam_name}/{feature}/state",
                    "payload": val_str,
                }))

    async def broadcast(self, topic: str, payload: Any):
        """Broadcast a message to all connected clients."""
        msg = json.dumps({"topic": topic, "payload": payload})
        dead = []
        with self.lock:
            sockets = list(self.active_websockets)
        for ws in sockets:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        if dead:
            with self.lock:
                for ws in dead:
                    self.active_websockets.discard(ws)

    def update_and_broadcast_sync(self, camera: str, feature: str, val: Any):
        """Synchronous wrapper to trigger state update and async broadcast."""
        bool_val = (str(val).upper() in ("ON", "TRUE", "1")) if isinstance(val, (str, bool)) else val
        if camera == "*":
            target_cameras = list(self.states.keys())
        elif camera in self.states:
            target_cameras = [camera]
        else:
            target_cameras = []

        for cam in target_cameras:
            self.states[cam][feature] = bool_val
            if feature == "recordings":
                self.states[cam]["record"] = bool_val
            elif feature == "record":
                self.states[cam]["recordings"] = bool_val

            # Update stats emitter
            cam_stat = self.stats_emitter.camera_stats.get(cam)
            if cam_stat:
                if feature == "detect":
                    cam_stat["detection_enabled"] = bool_val
                elif feature in ("record", "recordings"):
                    cam_stat["record_enabled"] = bool_val
                elif feature == "audio":
                    cam_stat["audio_enabled"] = bool_val
                elif feature == "ptz_autotracker":
                    cam_stat["ptz_autotracker_enabled"] = bool_val
                elif feature == "motion":
                    cam_stat["motion_enabled"] = bool_val

        logger.info("Updated state for %s: %s = %s", camera, feature, val)

        async def _do_broadcast():
            for cam in target_cameras:
                val_str = "ON" if bool_val is True else ("OFF" if bool_val is False else str(bool_val))
                await self.broadcast(f"{cam}/{feature}/state", val_str)
                if feature == "recordings":
                    await self.broadcast(f"{cam}/record/state", val_str)
                elif feature == "record":
                    await self.broadcast(f"{cam}/recordings/state", val_str)
            activity_str = json.dumps(self.get_camera_activity_dict())
            await self.broadcast("camera_activity", activity_str)
            await self.broadcast("stats", json.dumps(self.stats_emitter.get_latest_stats()))

        if self.main_loop and self.main_loop.is_running():
            asyncio.run_coroutine_threadsafe(_do_broadcast(), self.main_loop)
        else:
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    asyncio.create_task(_do_broadcast())
            except RuntimeError:
                pass

    async def handle_ws_message(self, ws: WebSocket, data: str):
        try:
            msg = json.loads(data)
        except Exception:
            return

        topic = msg.get("topic", "")
        payload = msg.get("payload")

        if topic == "onConnect":
            await self.send_full_state(ws)
            return

        # Parse <camera>/<feature>/set or <feature>/set
        parts = topic.split("/")
        if len(parts) == 3 and parts[2] == "set":
            camera, feature = parts[0], parts[1]
            self.update_and_broadcast_sync(camera, feature, payload)
        elif len(parts) == 2 and parts[1] == "set":
            feature = parts[0]
            self.update_and_broadcast_sync("*", feature, payload)
        elif len(parts) == 2 and parts[1] == "ptz":
            logger.info("PTZ command for %s: %s", parts[0], payload)

class SimpleDispatcher:
    """Implements Frigate's Dispatcher interface for REST and internal handlers."""
    def __init__(self, state_manager: CameraStateManager):
        self.state_manager = state_manager
        self._camera_settings_handlers = {
            "audio": self._handle_camera_setting,
            "audio_transcription": self._handle_camera_setting,
            "detect": self._handle_camera_setting,
            "enabled": self._handle_camera_setting,
            "improve_contrast": self._handle_camera_setting,
            "ptz_autotracker": self._handle_camera_setting,
            "motion": self._handle_camera_setting,
            "motion_contour_area": self._handle_camera_setting,
            "motion_threshold": self._handle_camera_setting,
            "notifications": self._handle_camera_setting,
            "recordings": self._handle_camera_setting,
            "record": self._handle_camera_setting,
            "snapshots": self._handle_camera_setting,
            "birdseye": self._handle_camera_setting,
            "birdseye_modes": self._handle_camera_setting,
            "review_alerts": self._handle_camera_setting,
            "review_detections": self._handle_camera_setting,
            "object_descriptions": self._handle_camera_setting,
            "review_descriptions": self._handle_camera_setting,
            "motion_mask": self._handle_camera_setting,
            "object_mask": self._handle_camera_setting,
            "zone": self._handle_camera_setting,
        }
        self._global_settings_handlers = {
            "notifications": self._handle_global_setting,
            "profile": self._handle_global_setting,
        }

    def _handle_camera_setting(self, *args, **kwargs):
        pass

    def _handle_global_setting(self, *args, **kwargs):
        pass

    def clear_runtime_state_for_yaml_keys(self, keys):
        pass

    def publish(self, topic: str, payload: Any, retain: bool = False):
        self._receive(topic, payload)

    def _receive(self, topic: str, payload: Any):
        parts = topic.split("/")
        if len(parts) >= 3 and parts[-1] == "set":
            camera, feature = parts[0], parts[1]
            self.state_manager.update_and_broadcast_sync(camera, feature, payload)
        elif len(parts) == 2 and parts[1] == "set":
            feature = parts[0]
            self.state_manager.update_and_broadcast_sync("*", feature, payload)

class SimpleEventMetadataPublisher:
    """Handles manual recording start and end events for SQLite persistence."""
    def __init__(self):
        pass

    def publish(self, payload: Any, sub_topic: str = "") -> None:
        try:
            if sub_topic in (EventMetadataTypeEnum.manual_event_create.value, "manual_event_create"):
                now, camera_name, label, event_id, include_recording, score, sub_label, duration, source, draw, pre_capture = payload
                Event.create(
                    id=event_id,
                    camera=camera_name,
                    label=label,
                    sub_label=sub_label,
                    top_score=score or 0.85,
                    score=score or 0.85,
                    false_positive=False,
                    start_time=now,
                    end_time=now + duration if duration else None,
                    zones=[],
                    thumbnail="",
                    has_clip=include_recording,
                    has_snapshot=True,
                    region=[],
                    box=[0, 0, 1, 1],
                    area=100,
                    retain_indefinitely=False,
                    ratio=1.0,
                    plus_id="",
                    model_hash="",
                    detector_type="openvino",
                    model_type="yolov8",
                    data={"box": [0, 0, 1, 1], "score": score or 0.85},
                )
                logger.info("Manual recording started: %s (%s)", event_id, camera_name)
            elif sub_topic in (EventMetadataTypeEnum.manual_event_end.value, "manual_event_end"):
                event_id, end_time = payload
                try:
                    event = Event.get(Event.id == event_id)
                    event.end_time = end_time
                    event.save()
                    logger.info("Manual recording ended: %s", event_id)
                except Exception as ex:
                    logger.warning("Event %s not found for end: %s", event_id, ex)
        except Exception as e:
            logger.error("EventMetadataPublisher error: %s", e)

def main():
    logger.info("Loading Frigate configuration...")
    config = FrigateConfig.load()
    config_holder = ConfigHolder(config)

    # Start go2rtc for hardware-accelerated MSE/WebRTC streaming
    go2rtc_manager = Go2rtcManager(config)
    go2rtc_manager.start()

    db_path = config.database.path
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    logger.info("Initializing SQLite database at %s...", db_path)
    db = SqliteDatabase(db_path, pragmas={"journal_mode": "wal", "foreign_keys": 1})

    models = [
        Event,
        Timeline,
        Regions,
        Recordings,
        ExportCase,
        Export,
        ReviewSegment,
        UserReviewStatus,
        Previews,
        User,
        Trigger,
        Notice,
        NoticeStats,
        CustomIdentity,
        IdentityReference,
        ObjectTrackRecord,
        ObjectSightingRecord,
        CameraAreaMapping,
        IdentitySettings,
        CameraSemanticMeta,
        EventRecord,
    ]
    db.bind(models)
    db.connect()
    db.create_tables(models, safe=True)
    db.close()

    # Seed Camera Semantic Maps
    get_semantic_map_manager()

    # Notice registry
    notice_registry = NoticeRegistry()
    install_registry(notice_registry)

    # Stats emitter, Storage maintainer, Frame processor, State manager & Dispatcher
    stats_emitter = SimpleStatsEmitter(config)
    storage_maintainer = SimpleStorageMaintainer(config)
    detected_frames_processor = LiveFrameProcessor(config)
    profile_manager = SimpleProfileManager(config)
    state_manager = CameraStateManager(config, stats_emitter)
    dispatcher = SimpleDispatcher(state_manager)
    event_metadata_publisher = SimpleEventMetadataPublisher()

    # Motion recording session manager
    motion_recording_manager = get_motion_recording_manager()
    motion_recording_manager.on_record_command = lambda cam, enable: state_manager.update_and_broadcast_sync(
        cam, "recordings", "ON" if enable else "OFF"
    )

    # 30-Minute Environment Snapshot Scheduler
    get_environment_snapshot_scheduler(
        frame_provider=detected_frames_processor.get_current_frame,
        camera_list=list(config.cameras.keys()),
    )

    logger.info("Creating FastAPI application...")
    app = create_fastapi_app(
        frigate_config=config,
        database=db,
        embeddings=None,
        detected_frames_processor=detected_frames_processor,
        storage_maintainer=storage_maintainer,
        onvif=None,
        stats_emitter=stats_emitter,
        event_metadata_updater=event_metadata_publisher,
        config_publisher=None,
        replay_manager=DebugReplayManager(),
        dispatcher=dispatcher,
        enforce_default_admin=False,
        config_holder=config_holder,
        notice_registry=notice_registry,
        profile_manager=profile_manager,
    )
    app.camera_error_image = make_camera_placeholder("camera")

    # Fast middleware for /api path rewrite and local admin authorization
    @app.middleware("http")
    async def url_rewrite_middleware(request: Request, call_next):
        path = request.url.path
        while path.startswith("/api/"):
            path = path[4:]
        if path == "/api":
            path = "/"
        request.scope["path"] = path

        # Inject admin role for instant local development access
        headers = dict(request.scope["headers"])
        headers[b"remote-user"] = b"admin"
        headers[b"remote-role"] = b"admin"
        request.scope["headers"] = [(k, v) for k, v in headers.items()]

        return await call_next(request)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        state_manager.register_ws(websocket)
        # Capture current event loop
        state_manager.main_loop = asyncio.get_running_loop()
        try:
            # Send initial full state immediately
            await state_manager.send_full_state(websocket)
            while True:
                data = await websocket.receive_text()
                await state_manager.handle_ws_message(websocket, data)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            state_manager.unregister_ws(websocket)

    @app.get("/profile")
    async def profile_handler(request: Request):
        return JSONResponse(content={"username": "admin", "role": "admin"})

    logger.info("Starting Frigate API server on 0.0.0.0:5000...")
    try:
        uvicorn.run(app, host="0.0.0.0", port=5000, log_level="warning")
    finally:
        go2rtc_manager.stop()

if __name__ == "__main__":
    main()
