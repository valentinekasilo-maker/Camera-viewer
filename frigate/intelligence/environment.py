"""Low-Frequency 30-Minute Environmental Snapshot System for Long-Term Scene Context."""

import datetime
import logging
import os
import threading
import time
from typing import Any, Callable, Optional

import cv2
import numpy as np

from frigate.models import EventRecord

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = os.path.abspath("config/environment_snapshots")
INTERVAL_SECONDS = 1800.0  # 30 minutes


class EnvironmentSnapshotScheduler:
    """
    Captures representative scene snapshots every 30 minutes for long-term scene context.
    Does not run expensive continuous VLM or send frames to cloud.
    """

    def __init__(
        self,
        frame_provider: Optional[Callable[[str], np.ndarray | None]] = None,
        camera_list: Optional[list[str]] = None,
        interval_seconds: float = INTERVAL_SECONDS,
    ):
        self.frame_provider = frame_provider
        self.camera_list = camera_list or [f"camera_{i}" for i in range(1, 9)]
        self.interval_seconds = interval_seconds
        self.snapshots_dir = SNAPSHOT_DIR
        os.makedirs(self.snapshots_dir, exist_ok=True)

        self.last_capture_times: dict[str, float] = {}
        self.recent_snapshots: list[dict[str, Any]] = []

        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()

    def capture_snapshot(self, camera_name: str, frame: Optional[np.ndarray] = None) -> Optional[dict[str, Any]]:
        """Capture and store a local representative environment snapshot for a camera."""
        now = time.time()
        dt_now = datetime.datetime.fromtimestamp(now)
        timestamp_str = dt_now.strftime("%Y%m%d_%H%M%S")
        filename = f"{camera_name}_{timestamp_str}.jpg"
        file_path = os.path.join(self.snapshots_dir, filename)

        if frame is None and self.frame_provider:
            try:
                frame = self.frame_provider(camera_name)
            except Exception as e:
                logger.debug("Error getting frame from provider for %s: %s", camera_name, e)

        if frame is not None:
            try:
                cv2.imwrite(file_path, frame)
            except Exception as e:
                logger.warning("Failed to write environment snapshot to %s: %s", file_path, e)
                return None
        else:
            # Create a placeholder scene snapshot if camera frame is unavailable
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            img[:] = (35, 30, 25)
            cv2.putText(
                img,
                f"{camera_name.upper()} - 30MIN ENV SNAPSHOT",
                (30, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                img,
                dt_now.strftime("%Y-%m-%d %H:%M:%S"),
                (30, 280),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (180, 180, 180),
                1,
            )
            cv2.imwrite(file_path, img)

        self.last_capture_times[camera_name] = now
        snapshot_id = f"env_{camera_name}_{int(now)}"

        record = {
            "id": snapshot_id,
            "camera": camera_name,
            "timestamp": dt_now.isoformat(),
            "file_path": file_path,
            "filename": filename,
            "type": "environment_snapshot",
        }

        self.recent_snapshots.insert(0, record)
        if len(self.recent_snapshots) > 100:
            self.recent_snapshots.pop()

        # Save to EventRecord
        try:
            EventRecord.create(
                id=snapshot_id,
                camera=camera_name,
                location=None,
                event_type="environment_snapshot",
                timestamp=dt_now,
                tracking_id=None,
                identity_name=None,
                confidence=1.0,
                evidence_snapshot=file_path,
                metadata={"filename": filename, "interval_s": self.interval_seconds},
            )
        except Exception as ex:
            logger.debug("Error saving environment snapshot event record: %s", ex)

        logger.info("Captured 30-min environment snapshot for %s -> %s", camera_name, filename)
        return record

    def get_recent_snapshots(self, camera: Optional[str] = None, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent environmental snapshots."""
        if camera:
            return [s for s in self.recent_snapshots if s["camera"] == camera][:limit]
        return self.recent_snapshots[:limit]

    def _scheduler_loop(self):
        """Background loop ensuring all cameras are snapshotted every 30 minutes."""
        # Initial capture pass on startup
        time.sleep(5.0)
        for cam in self.camera_list:
            try:
                self.capture_snapshot(cam)
            except Exception as e:
                logger.debug("Startup snapshot error for %s: %s", cam, e)

        while self._running:
            time.sleep(30.0)
            now = time.time()
            for cam in self.camera_list:
                last_time = self.last_capture_times.get(cam, 0)
                if now - last_time >= self.interval_seconds:
                    try:
                        self.capture_snapshot(cam)
                    except Exception as e:
                        logger.debug("Periodic snapshot error for %s: %s", cam, e)


_env_snapshot_scheduler: Optional[EnvironmentSnapshotScheduler] = None


def get_environment_snapshot_scheduler(
    frame_provider: Optional[Callable[[str], np.ndarray | None]] = None,
    camera_list: Optional[list[str]] = None,
) -> EnvironmentSnapshotScheduler:
    global _env_snapshot_scheduler
    if _env_snapshot_scheduler is None:
        _env_snapshot_scheduler = EnvironmentSnapshotScheduler(
            frame_provider=frame_provider, camera_list=camera_list
        )
    return _env_snapshot_scheduler
