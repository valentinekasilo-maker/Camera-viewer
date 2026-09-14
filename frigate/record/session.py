"""Intelligent Motion-Based Recording Session Controller with 5-Minute Grace Period."""

import datetime
import logging
import threading
import time
from typing import Any, Callable, Optional

from frigate.models import EventRecord
from frigate.motion.vegetation_filter import get_vegetation_filter

logger = logging.getLogger(__name__)

# 5-minute grace period (300 seconds)
RECORDING_GRACE_PERIOD_SECONDS = 300.0


class CameraRecordingSession:
    """Represents a continuous recording session for a camera."""

    def __init__(self, camera_name: str, session_id: str, start_time: float, trigger_reason: str):
        self.camera_name = camera_name
        self.session_id = session_id
        self.start_time = start_time
        self.last_activity_time = start_time
        self.end_time: Optional[float] = None
        self.trigger_reason = trigger_reason
        self.is_active = True
        self.activity_count = 1


class MotionRecordingManager:
    """
    Manages intelligent event-based recording across all cameras.
    Ensures recordings start on meaningful activity, stay active during activity,
    wait 5 minutes after activity stops, and extend seamlessly if new activity occurs.
    """

    def __init__(self, on_record_command: Optional[Callable[[str, bool], None]] = None):
        self.on_record_command = on_record_command
        self.sessions: dict[str, CameraRecordingSession] = {}
        self.lock = threading.Lock()
        self.grace_period_seconds = RECORDING_GRACE_PERIOD_SECONDS
        self._checker_running = True
        self._checker_thread = threading.Thread(target=self._session_watchdog_loop, daemon=True)
        self._checker_thread.start()

    def process_camera_activity(
        self,
        camera_name: str,
        detections: list[dict[str, Any]],
        raw_motion_boxes: list[tuple[int, int, int, int]] | None = None,
        is_gate_transition: bool = False,
    ) -> bool:
        """
        Process frame activity from a camera. Returns True if recording is active or started.
        """
        veg_filter = get_vegetation_filter(camera_name)
        is_meaningful, reason = veg_filter.is_meaningful_activity(
            detections=detections,
            raw_motion_boxes=raw_motion_boxes,
            is_gate_transition=is_gate_transition,
        )

        now = time.time()

        with self.lock:
            current_session = self.sessions.get(camera_name)

            if is_meaningful:
                if current_session and current_session.is_active:
                    # Meaningful activity continuing or occurred during 5-min grace period: extend session!
                    current_session.last_activity_time = now
                    current_session.activity_count += 1
                else:
                    # Start brand new recording session
                    session_id = f"rec_{camera_name}_{int(now)}"
                    new_session = CameraRecordingSession(
                        camera_name=camera_name,
                        session_id=session_id,
                        start_time=now,
                        trigger_reason=reason,
                    )
                    self.sessions[camera_name] = new_session
                    logger.info(
                        "Started intelligent recording session for %s (trigger: %s, session: %s)",
                        camera_name,
                        reason,
                        session_id,
                    )

                    # Trigger hardware/backend recording command
                    if self.on_record_command:
                        self.on_record_command(camera_name, True)

                    # Log to EventRecord
                    try:
                        EventRecord.create(
                            id=session_id,
                            camera=camera_name,
                            location=None,
                            event_type="recording_started",
                            timestamp=datetime.datetime.fromtimestamp(now),
                            tracking_id=None,
                            identity_name=None,
                            confidence=0.95,
                            evidence_snapshot=None,
                            metadata={"trigger_reason": reason, "grace_period_s": self.grace_period_seconds},
                        )
                    except Exception as ex:
                        logger.debug("Error recording session start record: %s", ex)

                return True

            # If no meaningful activity in this frame, but session exists and within 5-min grace window:
            if current_session and current_session.is_active:
                time_since_activity = now - current_session.last_activity_time
                if time_since_activity < self.grace_period_seconds:
                    # Still in 5-minute grace period, continue recording
                    return True

        return False

    def is_camera_recording(self, camera_name: str) -> bool:
        """Check if recording session is currently active for camera."""
        with self.lock:
            session = self.sessions.get(camera_name)
            if session and session.is_active:
                time_since_act = time.time() - session.last_activity_time
                return time_since_act < self.grace_period_seconds
        return False

    def get_session_status(self, camera_name: str) -> dict[str, Any]:
        """Get recording session telemetry for camera."""
        with self.lock:
            session = self.sessions.get(camera_name)
            now = time.time()
            if session and session.is_active:
                time_since_act = now - session.last_activity_time
                remaining_grace = max(0.0, self.grace_period_seconds - time_since_act)
                return {
                    "camera": camera_name,
                    "is_recording": remaining_grace > 0,
                    "session_id": session.session_id,
                    "duration_s": round(now - session.start_time, 1),
                    "seconds_since_last_activity": round(time_since_act, 1),
                    "remaining_grace_seconds": round(remaining_grace, 1),
                    "trigger_reason": session.trigger_reason,
                    "activity_count": session.activity_count,
                }
            return {
                "camera": camera_name,
                "is_recording": False,
                "session_id": None,
                "duration_s": 0,
                "seconds_since_last_activity": 0,
                "remaining_grace_seconds": 0,
                "trigger_reason": None,
                "activity_count": 0,
            }

    def _session_watchdog_loop(self):
        """Background loop checking for sessions that have exceeded the 5-minute grace period."""
        while self._checker_running:
            time.sleep(2.0)
            now = time.time()
            sessions_to_close = []

            with self.lock:
                for cam, session in list(self.sessions.items()):
                    if session.is_active:
                        inactivity_duration = now - session.last_activity_time
                        if inactivity_duration >= self.grace_period_seconds:
                            session.is_active = False
                            session.end_time = now
                            sessions_to_close.append(session)

            for s in sessions_to_close:
                logger.info(
                    "Closed recording session for %s after 5-min inactivity (total duration: %.1fs)",
                    s.camera_name,
                    s.end_time - s.start_time if s.end_time else 0,
                )
                if self.on_record_command:
                    self.on_record_command(s.camera_name, False)

                # Log recording_stopped to EventRecord
                try:
                    EventRecord.create(
                        id=f"rec_end_{s.session_id}",
                        camera=s.camera_name,
                        location=None,
                        event_type="recording_stopped",
                        timestamp=datetime.datetime.fromtimestamp(now),
                        tracking_id=None,
                        identity_name=None,
                        confidence=0.95,
                        evidence_snapshot=None,
                        metadata={
                            "session_id": s.session_id,
                            "duration_s": round((s.end_time or now) - s.start_time, 1),
                            "activity_count": s.activity_count,
                        },
                    )
                except Exception as ex:
                    logger.debug("Error logging recording_stopped: %s", ex)


_motion_rec_manager: Optional[MotionRecordingManager] = None


def get_motion_recording_manager() -> MotionRecordingManager:
    global _motion_rec_manager
    if _motion_rec_manager is None:
        _motion_rec_manager = MotionRecordingManager()
    return _motion_rec_manager
