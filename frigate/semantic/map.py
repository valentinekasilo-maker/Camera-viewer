"""Camera Semantic Map Manager and Metadata Store."""

import datetime
import logging
from typing import Any, Optional

from frigate.models import CameraSemanticMeta

logger = logging.getLogger(__name__)

INITIAL_CAMERA_SEMANTICS: list[dict[str, Any]] = [
    {
        "camera": "camera_1",
        "name": "Control Room Cam",
        "location": "Control Room",
        "description": "Monitors the main control room, Wi-Fi and network switches, Raspberry Pi NVR node, and main PC workstation.",
        "visible_areas": [
            "Wi-Fi/network equipment",
            "Raspberry Pi NVR",
            "PC workstation",
            "control-room environment",
        ],
        "important_objects": ["person", "equipment"],
        "expected_vehicles": 0,
        "important_zones": ["server_rack", "desk"],
        "privacy_masks": [],
        "special_rules": {
            "server_room_monitoring": True,
            "presence_alert": True,
        },
        "environmental_motion_notes": "LED blinking and fan movement should not trigger motion events.",
    },
    {
        "camera": "camera_2",
        "name": "Dining Room Cam",
        "location": "Dining",
        "description": "Monitors the central dining room table and wall-mounted television screen.",
        "visible_areas": [
            "dining area",
            "television",
            "dining table",
        ],
        "important_objects": ["person", "tv", "chair"],
        "expected_vehicles": 0,
        "important_zones": ["dining_table", "tv_area"],
        "privacy_masks": [],
        "special_rules": {
            "tv_state_rule": "TV ON: visible illuminated/content-bearing screen. TV OFF: screen appears dark/black. Do not claim certainty if visibility is poor.",
            "tv_detection_enabled": True,
        },
        "environmental_motion_notes": "TV display flicker when on should be recognized as television activity.",
    },
    {
        "camera": "camera_3",
        "name": "Backyard Garden Cam",
        "location": "Backyard / Garden",
        "description": "Monitors the open backyard, garden perimeter, and outdoor clothesline.",
        "visible_areas": [
            "backyard",
            "garden",
            "clothesline",
            "perimeter fence",
        ],
        "important_objects": [
            "person",
            "clothes",
            "dog",
            "cat",
            "bird",
        ],
        "expected_vehicles": 0,
        "important_zones": ["clothesline_zone", "garden_path"],
        "privacy_masks": [],
        "special_rules": {
            "vegetation_suppression": True,
            "suppress_plant_motion": True,
            "clothes_on_line_detection": True,
        },
        "environmental_motion_notes": "Heavy tree, leaf, bush, and grass wind motion must be suppressed.",
    },
    {
        "camera": "camera_4",
        "name": "Veranda Cam",
        "location": "Veranda",
        "description": "Monitors the covered veranda, porch entrance, and open play/activity area.",
        "visible_areas": [
            "veranda",
            "play/activity area",
            "patio seating",
        ],
        "important_objects": ["person", "children", "pet", "bicycle"],
        "expected_vehicles": 0,
        "important_zones": ["play_zone", "patio"],
        "privacy_masks": [],
        "special_rules": {
            "activity_area_monitoring": True,
            "occupancy_tracking": True,
        },
        "environmental_motion_notes": "Shadows from awning during bright daylight.",
    },
    {
        "camera": "camera_5",
        "name": "Kitchen Island Cam",
        "location": "Dining / Kitchen Island",
        "description": "Monitors the open kitchen island, dining transition area, small kitchen entrance, washing area, and cabinets.",
        "visible_areas": [
            "dining",
            "kitchen island",
            "small kitchen",
            "washing area",
            "kitchen cabinets",
        ],
        "important_objects": ["person", "kitchen_items", "cup", "bottle"],
        "expected_vehicles": 0,
        "important_zones": ["island_counter", "prep_area"],
        "privacy_masks": [],
        "special_rules": {
            "kitchen_activity_monitoring": True,
            "entry_exit_tracking": True,
        },
        "environmental_motion_notes": "Steam from cooking and ceiling lighting reflections.",
    },
    {
        "camera": "camera_6",
        "name": "Entrance Cam",
        "location": "Entrance",
        "description": "Monitors the primary home entrance door, front pathway, and gate in the distance.",
        "visible_areas": [
            "gate in the distance",
            "entrance door",
            "front walkway",
            "porch steps",
        ],
        "important_objects": ["person", "package", "dog", "visitor"],
        "expected_vehicles": 0,
        "important_zones": ["doorstep", "front_path"],
        "privacy_masks": [],
        "special_rules": {
            "entry_exit_tracking": True,
            "door_activity_alert": True,
            "package_delivery_detection": True,
        },
        "environmental_motion_notes": "Distant gate movement or passing road vehicles in distant background.",
    },
    {
        "camera": "camera_7",
        "name": "Gate and Parking Cam",
        "location": "Gate / Parking",
        "description": "Primary gate intelligence and vehicle parking camera. Shows main motorized gate, driveway, and parking spaces.",
        "visible_areas": [
            "gate",
            "parking area",
            "driveway",
            "vehicles",
        ],
        "important_objects": [
            "car",
            "truck",
            "motorcycle",
            "person",
            "gate",
        ],
        "expected_vehicles": 2,
        "important_zones": ["gate_threshold", "parking_bay_1", "parking_bay_2"],
        "privacy_masks": [],
        "special_rules": {
            "gate_state_machine": True,
            "vehicle_presence_baseline": 2,
            "vehicle_arrival_departure_alert": True,
        },
        "environmental_motion_notes": "Passing headlights at night; tree branches near gate.",
    },
    {
        "camera": "camera_8",
        "name": "Small Kitchen Cam",
        "location": "Small Kitchen",
        "description": "Monitors the secondary/small kitchen, back washing areas, and kitchen utility access.",
        "visible_areas": [
            "second/small kitchen",
            "washing areas",
            "kitchen environment",
            "utility sink",
        ],
        "important_objects": ["person", "kitchen_items", "cleaning_tools"],
        "expected_vehicles": 0,
        "important_zones": ["washing_sink", "rear_door"],
        "privacy_masks": [],
        "special_rules": {
            "kitchen_activity_monitoring": True,
            "utility_area_tracking": True,
        },
        "environmental_motion_notes": "Water tap reflections and utility lighting changes.",
    },
]


class CameraSemanticMapManager:
    """Manages persistent semantic metadata for all cameras."""

    def __init__(self):
        self._init_seed_data()

    def _init_seed_data(self):
        """Seed initial camera semantic records if not already populated."""
        try:
            for seed in INITIAL_CAMERA_SEMANTICS:
                existing = (
                    CameraSemanticMeta.select()
                    .where(CameraSemanticMeta.camera == seed["camera"])
                    .first()
                )
                if not existing:
                    CameraSemanticMeta.create(
                        camera=seed["camera"],
                        name=seed["name"],
                        location=seed["location"],
                        description=seed["description"],
                        visible_areas=seed["visible_areas"],
                        important_objects=seed["important_objects"],
                        expected_vehicles=seed["expected_vehicles"],
                        important_zones=seed["important_zones"],
                        privacy_masks=seed["privacy_masks"],
                        special_rules=seed["special_rules"],
                        environmental_motion_notes=seed["environmental_motion_notes"],
                        updated_at=datetime.datetime.now(),
                    )
        except Exception as e:
            logger.debug("Database not yet migrated or seeded: %s", e)

    def get_all_camera_semantics(self) -> list[dict[str, Any]]:
        """Retrieve all camera semantic configurations."""
        try:
            records = list(
                CameraSemanticMeta.select().order_by(CameraSemanticMeta.camera.asc())
            )
            if not records:
                return INITIAL_CAMERA_SEMANTICS
            return [self._record_to_dict(r) for r in records]
        except Exception as e:
            logger.debug("Error fetching camera semantics: %s", e)
            return INITIAL_CAMERA_SEMANTICS

    def get_camera_semantic(self, camera: str) -> dict[str, Any]:
        """Retrieve semantic configuration for a single camera."""
        try:
            rec = (
                CameraSemanticMeta.select()
                .where(CameraSemanticMeta.camera == camera)
                .first()
            )
            if rec:
                return self._record_to_dict(rec)
        except Exception as e:
            logger.debug("Error fetching camera semantic for %s: %s", camera, e)

        # Fallback to initial seeds
        for s in INITIAL_CAMERA_SEMANTICS:
            if s["camera"] == camera:
                return s
        return {
            "camera": camera,
            "name": camera.title(),
            "location": camera.title(),
            "description": f"Camera {camera}",
            "visible_areas": [],
            "important_objects": ["person", "car"],
            "expected_vehicles": 0,
            "important_zones": [],
            "privacy_masks": [],
            "special_rules": {},
            "environmental_motion_notes": "",
        }

    def update_camera_semantic(
        self, camera: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update or create camera semantic metadata."""
        now = datetime.datetime.now()
        rec = (
            CameraSemanticMeta.select()
            .where(CameraSemanticMeta.camera == camera)
            .first()
        )
        if rec:
            if "name" in data:
                rec.name = data["name"]
            if "location" in data:
                rec.location = data["location"]
            if "description" in data:
                rec.description = data["description"]
            if "visible_areas" in data:
                rec.visible_areas = data["visible_areas"]
            if "important_objects" in data:
                rec.important_objects = data["important_objects"]
            if "expected_vehicles" in data:
                rec.expected_vehicles = int(data["expected_vehicles"])
            if "important_zones" in data:
                rec.important_zones = data["important_zones"]
            if "privacy_masks" in data:
                rec.privacy_masks = data["privacy_masks"]
            if "special_rules" in data:
                rec.special_rules = data["special_rules"]
            if "environmental_motion_notes" in data:
                rec.environmental_motion_notes = data["environmental_motion_notes"]
            rec.updated_at = now
            rec.save()
            return self._record_to_dict(rec)
        else:
            new_rec = CameraSemanticMeta.create(
                camera=camera,
                name=data.get("name", camera.title()),
                location=data.get("location", camera.title()),
                description=data.get("description", ""),
                visible_areas=data.get("visible_areas", []),
                important_objects=data.get("important_objects", []),
                expected_vehicles=int(data.get("expected_vehicles", 0)),
                important_zones=data.get("important_zones", []),
                privacy_masks=data.get("privacy_masks", []),
                special_rules=data.get("special_rules", {}),
                environmental_motion_notes=data.get(
                    "environmental_motion_notes", ""
                ),
                updated_at=now,
            )
            return self._record_to_dict(new_rec)

    def _record_to_dict(self, rec: CameraSemanticMeta) -> dict[str, Any]:
        return {
            "camera": rec.camera,
            "name": rec.name,
            "location": rec.location,
            "description": rec.description,
            "visible_areas": rec.visible_areas or [],
            "important_objects": rec.important_objects or [],
            "expected_vehicles": rec.expected_vehicles or 0,
            "important_zones": rec.important_zones or [],
            "privacy_masks": rec.privacy_masks or [],
            "special_rules": rec.special_rules or {},
            "environmental_motion_notes": rec.environmental_motion_notes or "",
            "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
        }


_semantic_map_mgr: Optional[CameraSemanticMapManager] = None


def get_semantic_map_manager() -> CameraSemanticMapManager:
    global _semantic_map_mgr
    if _semantic_map_mgr is None:
        _semantic_map_mgr = CameraSemanticMapManager()
    return _semantic_map_mgr
