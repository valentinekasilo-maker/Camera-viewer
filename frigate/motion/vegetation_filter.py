"""Vegetation and Environmental Motion Suppression Filter."""

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VegetationMotionFilter:
    """
    Intelligently filters out plant, tree, leaf, grass, and repetitive environmental
    motion while preserving detection of people, vehicles, animals, and gate changes.
    """

    MEANINGFUL_LABELS = {
        "person",
        "car",
        "truck",
        "motorcycle",
        "bus",
        "bicycle",
        "dog",
        "cat",
        "package",
        "gate",
        "door",
    }

    def __init__(self, camera_name: str = "camera_3"):
        self.camera_name = camera_name
        self.vegetation_suppression_enabled = True
        self.min_persistence_frames = 3
        self.min_confidence_threshold = 0.65
        self.motion_history: dict[str, list[float]] = {}
        self.last_suppressed_count = 0

    def is_meaningful_activity(
        self,
        detections: list[dict[str, Any]],
        raw_motion_boxes: list[tuple[int, int, int, int]] | None = None,
        is_gate_transition: bool = False,
    ) -> tuple[bool, str]:
        """
        Evaluate whether the detected activity represents meaningful activity.

        Returns:
            (is_meaningful, reason)
        """
        if is_gate_transition:
            return True, "gate_state_transition"

        # 1. Check for classified objects
        valid_objects = []
        for obj in detections:
            label = str(obj.get("label", "")).lower()
            sub_label = str(obj.get("sub_label", "")).lower()
            score = float(obj.get("score", obj.get("confidence", 0.85)))
            stationary = bool(obj.get("stationary", False))

            # Matched meaningful class with sufficient confidence
            if (label in self.MEANINGFUL_LABELS or any(m in sub_label for m in self.MEANINGFUL_LABELS)) and score >= self.min_confidence_threshold:
                if not stationary or label in ("person", "car", "package"):
                    valid_objects.append(obj)

        if valid_objects:
            primary_label = valid_objects[0].get("label") or "object"
            return True, f"classified_{primary_label}"

        # 2. If raw pixel motion exists but no classified object is detected:
        # In cameras with vegetation suppression (like camera_3 backyard or outdoor cameras),
        # unclassified flickering contours are considered environmental plant motion.
        if raw_motion_boxes and len(raw_motion_boxes) > 0:
            if self.vegetation_suppression_enabled:
                self.last_suppressed_count += len(raw_motion_boxes)
                return False, "suppressed_vegetation_motion"
            else:
                return True, "unclassified_motion"

        return False, "no_activity"

    def filter_detections(
        self, detections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter out false positives caused by foliage shadows or wind jitter."""
        filtered = []
        for obj in detections:
            label = str(obj.get("label", "")).lower()
            score = float(obj.get("score", obj.get("confidence", 0.0)))

            # If it's a person/vehicle, keep it
            if label in ("person", "car", "truck", "motorcycle", "package", "dog"):
                if score >= 0.50:
                    filtered.append(obj)
            elif score >= self.min_confidence_threshold:
                filtered.append(obj)

        return filtered


_vegetation_filters: dict[str, VegetationMotionFilter] = {}


def get_vegetation_filter(camera_name: str) -> VegetationMotionFilter:
    if camera_name not in _vegetation_filters:
        _vegetation_filters[camera_name] = VegetationMotionFilter(camera_name)
    return _vegetation_filters[camera_name]
