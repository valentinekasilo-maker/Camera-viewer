"""Cross-Camera Spatial-Temporal Tracker & Presence Manager for ANDRO-Vision."""

import time
import logging
from dataclasses import dataclass, field
from typing import Any
import numpy as np

from .extractor import cosine_similarity
from .matcher import MatchResult

logger = logging.getLogger(__name__)

@dataclass
class TrackState:
    id: str  # Unique track id e.g. "kamera_1-1789302000-001"
    display_id: str  # e.g. "CAR #001", "PERSON #002"
    camera: str
    camera_location: str
    object_class: str
    identity_id: str | None
    identity_name: str
    confidence: float
    first_seen: float
    last_seen: float
    status: str  # "active", "ended", "reviewed", "ignored"
    snapshot_path: str | None = None
    embedding: np.ndarray | None = None
    sighting_count: int = 1
    is_unknown: bool = True
    last_sampled_time: float = 0.0
    history: list[dict[str, Any]] = field(default_factory=list)

class CrossCameraTracker:
    """
    Manages active object tracks across all cameras, computes presence states,
    and performs conservative cross-camera spatial-temporal correlation.
    """

    def __init__(
        self,
        presence_timeout_seconds: float = 300.0,       # 5 minutes -> Not Recently Seen
        away_timeout_seconds: float = 1800.0,           # 30 minutes -> Away
        cross_camera_window_seconds: float = 60.0,      # 1 minute cross-camera window
        cross_camera_threshold: float = 0.82,          # Strict similarity to merge cross-camera
        sample_cooldown_seconds: float = 3.0,          # Don't extract features more than once per 3s
    ):
        self.presence_timeout = presence_timeout_seconds
        self.away_timeout = away_timeout_seconds
        self.cross_camera_window = cross_camera_window_seconds
        self.cross_camera_threshold = cross_camera_threshold
        self.sample_cooldown = sample_cooldown_seconds

        self.active_tracks: dict[str, TrackState] = {}
        self.recently_ended_tracks: list[TrackState] = []
        self.track_counters: dict[str, int] = {}  # { 'car': 1, 'person': 2, ... }

    def get_next_display_id(self, object_class: str) -> str:
        cls_key = object_class.upper()
        self.track_counters[cls_key] = self.track_counters.get(cls_key, 0) + 1
        return f"{cls_key} #{self.track_counters[cls_key]:03d}"

    def update_track(
        self,
        camera: str,
        camera_location: str,
        object_class: str,
        raw_track_id: str | None,
        candidate_embedding: np.ndarray | None,
        match_result: MatchResult,
        snapshot_path: str | None = None,
    ) -> tuple[TrackState, bool]:
        """
        Update an ongoing track or initiate a new cross-camera / local track.
        Returns: (TrackState, is_new_event: bool)
        """
        now = time.time()
        track_key = f"{camera}_{raw_track_id}" if raw_track_id else f"{camera}_{object_class}_{int(now)}"
        is_new = False

        # 1. Check if track already active on this camera
        if track_key in self.active_tracks:
            track = self.active_tracks[track_key]
            track.last_seen = now
            track.sighting_count += 1
            if match_result.matched:
                track.identity_id = match_result.identity_id
                track.identity_name = match_result.identity_name
                track.confidence = max(track.confidence, match_result.confidence)
                track.is_unknown = False
            if snapshot_path:
                track.snapshot_path = snapshot_path
            if candidate_embedding is not None and (now - track.last_sampled_time >= self.sample_cooldown):
                track.embedding = candidate_embedding
                track.last_sampled_time = now
            return track, False

        # 2. Attempt Cross-Camera correlation with recently ended tracks
        correlated_track = None
        if candidate_embedding is not None:
            for past_track in reversed(self.recently_ended_tracks):
                if now - past_track.last_seen > self.cross_camera_window:
                    continue
                if past_track.object_class.lower() != object_class.lower():
                    continue
                if past_track.camera == camera:
                    continue  # Different camera required for cross-camera correlation

                if past_track.embedding is not None:
                    sim = cosine_similarity(candidate_embedding, past_track.embedding)
                    if sim >= self.cross_camera_threshold:
                        # High confidence correlation
                        correlated_track = past_track
                        logger.info(
                            "Cross-camera correlation: %s from %s (%s) -> %s (%s) (sim: %.2f)",
                            past_track.display_id,
                            past_track.camera,
                            past_track.camera_location,
                            camera,
                            camera_location,
                            sim,
                        )
                        break

        display_id = correlated_track.display_id if correlated_track else self.get_next_display_id(object_class)
        first_seen_time = correlated_track.first_seen if correlated_track else now

        track = TrackState(
            id=track_key,
            display_id=display_id,
            camera=camera,
            camera_location=camera_location,
            object_class=object_class,
            identity_id=match_result.identity_id,
            identity_name=match_result.identity_name,
            confidence=match_result.confidence,
            first_seen=first_seen_time,
            last_seen=now,
            status="active",
            snapshot_path=snapshot_path,
            embedding=candidate_embedding,
            sighting_count=1 + (correlated_track.sighting_count if correlated_track else 0),
            is_unknown=not match_result.matched,
            last_sampled_time=now,
        )

        track.history.append({
            "camera": camera,
            "location": camera_location,
            "timestamp": now,
            "confidence": match_result.confidence,
            "snapshot_path": snapshot_path,
        })

        self.active_tracks[track_key] = track
        is_new = (correlated_track is None)
        return track, is_new

    def cleanup_expired_tracks(self, inactive_threshold_seconds: float = 30.0) -> list[TrackState]:
        """Move inactive tracks from active registry to recently ended list."""
        now = time.time()
        expired_keys = []
        ended_tracks = []

        for key, track in self.active_tracks.items():
            if now - track.last_seen > inactive_threshold_seconds:
                expired_keys.append(key)
                track.status = "ended"
                ended_tracks.append(track)
                self.recently_ended_tracks.append(track)

        for key in expired_keys:
            del self.active_tracks[key]

        # Prune old ended tracks older than 10 minutes
        self.recently_ended_tracks = [
            t for t in self.recently_ended_tracks if now - t.last_seen < 600.0
        ]

        return ended_tracks

    def calculate_presence_status(self, last_seen_time: float | None) -> str:
        """
        Calculate presence state for an identity:
        - "present" (seen within presence_timeout, e.g. 5 min)
        - "not_recently_seen" (seen within away_timeout, e.g. 30 min)
        - "away" (seen > 30 min ago or never)
        """
        if not last_seen_time:
            return "not_recently_seen"
        elapsed = time.time() - last_seen_time
        if elapsed < self.presence_timeout:
            return "present"
        elif elapsed < self.away_timeout:
            return "not_recently_seen"
        else:
            return "away"


# Module-level aliases
IdentityTracker = CrossCameraTracker
