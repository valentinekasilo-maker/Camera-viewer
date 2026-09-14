"""Camera Context Planner and Internal Query Tools for ANDRO-Vision."""

import datetime
import logging
import os
from pathlib import Path
from typing import Any, Optional

from frigate.identity.manager import get_identity_manager
from frigate.intelligence.gate_vehicle import get_gate_intelligence, get_vehicle_presence
from frigate.intelligence.gemini_escalation import analyze_with_gemini_vision, resolve_camera_snapshot_path
from frigate.models import (
    CameraSemanticMeta,
    CustomIdentity,
    EventRecord,
    ObjectSightingRecord,
    ObjectTrackRecord,
)
from frigate.semantic.map import get_semantic_map_manager

logger = logging.getLogger(__name__)


class CameraContextPlanner:
    """Dispatches targeted internal tools to retrieve structured camera evidence."""

    def __init__(self):
        self.identity_mgr = get_identity_manager()
        self.semantic_map = get_semantic_map_manager()
        self.gate_mgr = get_gate_intelligence()
        self.vehicle_mgr = get_vehicle_presence()

    def get_camera_state(self, camera_id: str) -> dict[str, Any]:
        """Tool 1: Return current status, location, semantic visual area, active tracks, and recent sightings."""
        clean_cam = self._canonical_camera_name(camera_id)
        sem_meta = self.semantic_map.get_camera_semantic(clean_cam)
        location = sem_meta.get("location") or self.identity_mgr.get_camera_location(clean_cam)

        # Get active tracks on this camera
        active_tracks = []
        try:
            tracks = self.identity_mgr.get_active_tracks()
            active_tracks = [t for t in tracks if self._canonical_camera_name(t.get("camera", "")) == clean_cam]
        except Exception as e:
            logger.debug("Error getting active tracks for %s: %s", clean_cam, e)

        return {
            "camera": clean_cam,
            "location": location,
            "semantic_meta": sem_meta,
            "active_tracks": active_tracks,
            "active_count": len(active_tracks),
            "snapshot_available": resolve_camera_snapshot_path(clean_cam) is not None,
        }

    def get_recent_events(
        self,
        camera_id: Optional[str] = None,
        time_range_seconds: int = 600,
        event_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Tool 2: Query historical event database within a relative timeframe."""
        events = []
        since = datetime.datetime.now() - datetime.timedelta(seconds=time_range_seconds)
        try:
            query = EventRecord.select().where(EventRecord.timestamp >= since)
            if camera_id:
                clean_cam = self._canonical_camera_name(camera_id)
                query = query.where(EventRecord.camera == clean_cam)
            if event_type:
                query = query.where(EventRecord.event_type == event_type)

            records = list(query.order_by(EventRecord.timestamp.desc()).limit(limit))
            for r in records:
                events.append({
                    "id": r.id,
                    "camera": r.camera,
                    "location": r.location,
                    "event_type": r.event_type,
                    "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.timestamp else "",
                    "time_str": r.timestamp.strftime("%H:%M:%S") if r.timestamp else "",
                    "identity_name": r.identity_name,
                    "confidence": r.confidence,
                    "metadata": r.metadata,
                })
        except Exception as e:
            logger.debug("Error retrieving recent events: %s", e)

        return events

    def find_object(self, object_query: str) -> list[dict[str, Any]]:
        """Tool 3: Search objects across active tracks, recent sightings, and registered identities."""
        q_lower = object_query.lower().strip()
        results = []

        # 1. Search Custom Identities
        try:
            identities = list(CustomIdentity.select())
            for i in identities:
                match = (
                    q_lower in i.name.lower()
                    or (i.object_class and q_lower in i.object_class.lower())
                    or (i.category and q_lower in i.category.lower())
                    or (i.color and q_lower in i.color.lower())
                )
                if match:
                    results.append({
                        "source": "custom_identity",
                        "name": i.name,
                        "category": i.category,
                        "object_class": i.object_class,
                        "color": i.color,
                        "status": i.status,
                        "last_seen_camera": i.last_seen_camera,
                        "last_seen_location": i.last_seen_location,
                        "last_seen_time": i.last_seen_time.strftime("%H:%M:%S") if i.last_seen_time else None,
                    })
        except Exception as e:
            logger.debug("Error searching custom identities: %s", e)

        # 2. Search Active Tracks
        try:
            tracks = self.identity_mgr.get_active_tracks()
            for t in tracks:
                t_name = (t.get("identity_name") or "").lower()
                t_cls = (t.get("object_class") or "").lower()
                if q_lower in t_name or q_lower in t_cls:
                    results.append({
                        "source": "active_track",
                        "track_id": t.get("track_display_id"),
                        "identity_name": t.get("identity_name"),
                        "object_class": t.get("object_class"),
                        "camera": t.get("camera"),
                        "location": t.get("area"),
                        "confidence": t.get("confidence", 0.90),
                    })
        except Exception as e:
            logger.debug("Error searching active tracks: %s", e)

        return results

    def find_person(self, person_query: str = "") -> dict[str, Any]:
        """Tool 4: Search for person sightings, known registered persons, and unknown person reviews."""
        q_lower = person_query.lower().strip()
        matched_person = None

        # Search known identities
        try:
            persons = list(CustomIdentity.select().where(CustomIdentity.is_person == True))
            for p in persons:
                if not q_lower or q_lower in p.name.lower() or p.name.lower() in q_lower:
                    matched_person = {
                        "name": p.name,
                        "status": p.status,
                        "last_seen_camera": p.last_seen_camera,
                        "last_seen_location": p.last_seen_location,
                        "last_seen_time": p.last_seen_time.strftime("%H:%M:%S") if p.last_seen_time else None,
                        "last_seen_datetime": p.last_seen_time.isoformat() if p.last_seen_time else None,
                    }
                    break
        except Exception as e:
            logger.debug("Error searching persons: %s", e)

        # Active person tracks across all cameras
        active_persons = []
        try:
            tracks = self.identity_mgr.get_active_tracks()
            active_persons = [t for t in tracks if t.get("object_class") == "person"]
        except Exception:
            pass

        # Unknown person queue
        unknowns = []
        try:
            unknowns = self.identity_mgr.get_unknown_queue(limit=5)
            unknowns = [u for u in unknowns if u.get("object_class") == "person"]
        except Exception:
            pass

        return {
            "matched_person": matched_person,
            "active_persons": active_persons,
            "active_count": len(active_persons),
            "unknown_persons": unknowns,
        }

    def find_vehicle(self, vehicle_query: str = "") -> dict[str, Any]:
        """Tool 5: Search for vehicle status, registered cars, parking presence baseline."""
        veh_status = self.vehicle_mgr.get_vehicle_status()
        q_lower = vehicle_query.lower().strip()

        matched_vehicle = None
        try:
            vehicles = list(CustomIdentity.select().where(CustomIdentity.category == "vehicle"))
            for v in vehicles:
                name_l = v.name.lower()
                color_l = (v.color or "").lower()
                if (
                    not q_lower
                    or q_lower in name_l
                    or name_l in q_lower
                    or (color_l and color_l in q_lower)
                    or any(w in name_l for w in q_lower.split() if len(w) > 2)
                ):
                    matched_vehicle = {
                        "name": v.name,
                        "color": v.color,
                        "status": v.status,
                        "last_seen_camera": v.last_seen_camera or "Camera 7",
                        "last_seen_location": v.last_seen_location or "Gate / Parking",
                        "last_seen_time": v.last_seen_time.strftime("%H:%M:%S") if v.last_seen_time else "recent",
                    }
                    break
        except Exception as e:
            logger.debug("Error searching vehicles: %s", e)

        return {
            "vehicle_status": veh_status,
            "matched_vehicle": matched_vehicle,
            "both_cars_present": veh_status.get("both_cars_present", True),
            "expected_baseline": veh_status.get("expected_baseline", 2),
            "current_count": veh_status.get("current_count", 2),
            "missing_vehicles": veh_status.get("missing_expected_vehicles", []),
            "new_unknown_vehicle": veh_status.get("has_new_unknown_vehicle", False),
        }

    def get_last_seen(self, identity_name: str) -> Optional[dict[str, Any]]:
        """Tool 6: Find exact last seen camera, location, and timestamp for an enrolled identity."""
        q_lower = identity_name.lower().strip()
        try:
            identities = list(CustomIdentity.select())
            for i in identities:
                name_l = i.name.lower()
                color_l = (i.color or "").lower()
                class_l = (i.object_class or "").lower()
                if (
                    q_lower in name_l
                    or name_l in q_lower
                    or (color_l and color_l in q_lower)
                    or any(w in name_l for w in q_lower.split() if len(w) > 2)
                    or (color_l and class_l and f"{color_l} {class_l}" in q_lower)
                ):
                    time_ago_str = ""
                    if i.last_seen_time:
                        diff = int((datetime.datetime.now() - i.last_seen_time).total_seconds())
                        time_ago_str = f"{diff // 60}m ago" if diff >= 60 else f"{diff}s ago"

                    return {
                        "found": True,
                        "name": i.name,
                        "category": i.category,
                        "status": i.status,
                        "camera": i.last_seen_camera or "Camera 7",
                        "location": i.last_seen_location or "Gate / Parking",
                        "timestamp": i.last_seen_time.strftime("%H:%M:%S") if i.last_seen_time else None,
                        "time_ago": time_ago_str,
                        "confidence": 0.94,
                    }
        except Exception as e:
            logger.debug("Error retrieving last seen for %s: %s", identity_name, e)


        # Fallback to ObjectSightingRecord
        try:
            s = (
                ObjectSightingRecord.select()
                .where(ObjectSightingRecord.identity_name.contains(identity_name))
                .order_by(ObjectSightingRecord.timestamp.desc())
                .first()
            )
            if s:
                diff = int((datetime.datetime.now() - s.timestamp).total_seconds())
                time_ago_str = f"{diff // 60}m ago" if diff >= 60 else f"{diff}s ago"
                return {
                    "found": True,
                    "name": s.identity_name,
                    "category": "object",
                    "status": "present" if diff < 300 else "not_recently_seen",
                    "camera": s.camera,
                    "location": s.camera_location,
                    "timestamp": s.timestamp.strftime("%H:%M:%S"),
                    "time_ago": time_ago_str,
                    "confidence": s.confidence,
                }
        except Exception as e:
            logger.debug("Error retrieving sighting record for %s: %s", identity_name, e)

        return None

    def get_last_person_detected(self) -> Optional[dict[str, Any]]:
        """Tool 6b: Retrieve the most recently detected person across all cameras, sightings, and event records."""
        try:
            # 1. Active tracks with object_class == 'person'
            try:
                tracks = self.identity_mgr.get_active_tracks()
                person_tracks = [t for t in tracks if t.get("object_class") == "person"]
                if person_tracks:
                    t = person_tracks[0]
                    return {
                        "name": t.get("identity_name") or "Unrecognized Person",
                        "camera": t.get("camera"),
                        "location": t.get("area"),
                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                        "confidence": t.get("confidence", 0.92),
                        "is_active": True,
                    }
            except Exception:
                pass

            candidates = []

            # 2. Known person records
            try:
                persons = list(CustomIdentity.select().where(CustomIdentity.is_person == True))
                for p in persons:
                    if p.last_seen_time:
                        candidates.append((p.last_seen_time, {
                            "name": p.name,
                            "camera": p.last_seen_camera or "Camera 5",
                            "location": p.last_seen_location or "Dining / Kitchen Island",
                            "timestamp": p.last_seen_time.strftime("%H:%M:%S"),
                            "confidence": 0.94,
                            "is_active": False,
                        }))
            except Exception:
                pass

            # 3. ObjectTrackRecord for person
            try:
                tr = (
                    ObjectTrackRecord.select()
                    .where(ObjectTrackRecord.object_class == "person")
                    .order_by(ObjectTrackRecord.last_seen.desc())
                    .first()
                )
                if tr and tr.last_seen:
                    candidates.append((tr.last_seen, {
                        "name": tr.identity_name or "Unrecognized Person",
                        "camera": tr.camera,
                        "location": tr.camera_location,
                        "timestamp": tr.last_seen.strftime("%H:%M:%S"),
                        "confidence": tr.confidence or 0.92,
                        "is_active": False,
                    }))
            except Exception:
                pass

            # 4. Event Records specifically for person events
            try:
                ev = (
                    EventRecord.select()
                    .where(EventRecord.event_type.contains("person"))
                    .order_by(EventRecord.timestamp.desc())
                    .first()
                )
                if ev and ev.timestamp:
                    candidates.append((ev.timestamp, {
                        "name": ev.identity_name or "An unrecognized person",
                        "camera": ev.camera,
                        "location": ev.location,
                        "timestamp": ev.timestamp.strftime("%H:%M:%S"),
                        "confidence": ev.confidence or 0.94,
                        "is_active": False,
                    }))
            except Exception:
                pass

            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                return candidates[0][1]

        except Exception as e:
            logger.debug("Error retrieving last person detected: %s", e)
        return None

    def get_current_vehicles(self, camera_id: str = "camera_7") -> dict[str, Any]:
        """Tool 7: Query current parking vehicles and baseline."""
        return self.vehicle_mgr.get_vehicle_status()

    def get_gate_state(self, camera_id: str = "camera_7") -> dict[str, Any]:
        """Tool 8: Query gate state machine (OPEN, CLOSED, UNKNOWN), certainty, and last transition."""
        return self.gate_mgr.get_gate_status()

    def get_gate_events(self, time_range_seconds: int = 3600) -> list[dict[str, Any]]:
        """Tool 9: Query recent gate transition history with associated persons and vehicles."""
        gate_status = self.gate_mgr.get_gate_status()
        return gate_status.get("recent_transitions", [])

    def get_camera_snapshot(self, camera_id: str) -> Optional[str]:
        """Tool 10: Resolve latest image snapshot filepath for a given camera."""
        return resolve_camera_snapshot_path(camera_id)

    def search_event_history(self, query: str, time_range_seconds: int = 3600) -> list[dict[str, Any]]:
        """Tool 11: Free-form search of event records."""
        results = []
        since = datetime.datetime.now() - datetime.timedelta(seconds=time_range_seconds)
        q_lower = query.lower()
        try:
            records = (
                EventRecord.select()
                .where(EventRecord.timestamp >= since)
                .order_by(EventRecord.timestamp.desc())
                .limit(30)
            )
            for r in records:
                text = f"{r.camera} {r.location} {r.event_type} {r.identity_name}".lower()
                if any(w in text for w in q_lower.split()):
                    results.append({
                        "camera": r.camera,
                        "location": r.location,
                        "event_type": r.event_type,
                        "timestamp": r.timestamp.strftime("%H:%M:%S") if r.timestamp else "",
                        "identity_name": r.identity_name,
                        "confidence": r.confidence,
                    })
        except Exception as e:
            logger.debug("Error searching event history: %s", e)
        return results

    def request_visual_analysis(self, camera_id: str, question: str, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Tool 12: Escalate visual question directly to Gemini Multimodal Vision."""
        return analyze_with_gemini_vision(
            camera_id=camera_id,
            question=question,
            context=context,
        )

    def _canonical_camera_name(self, raw_cam: str) -> str:
        """Normalize camera names to standard 'camera_N' or 'kamera_N'."""
        if not raw_cam:
            return "camera_7"
        c = raw_cam.lower().strip()
        if c in ("gate", "parking", "front gate", "driveway"):
            return "camera_7"
        if c in ("dining", "tv", "living room"):
            return "camera_2"
        if c in ("backyard", "garden", "clothesline"):
            return "camera_3"
        if c in ("veranda", "patio", "play area"):
            return "camera_4"
        if c in ("small kitchen", "utility sink", "second kitchen"):
            return "camera_8"
        if c in ("kitchen", "kitchen island", "dining"):
            return "camera_5"
        if c in ("entrance", "front door", "porch"):
            return "camera_6"
        if c in ("control room", "server", "raspberry pi"):
            return "camera_1"

        if c.startswith("cam_"):
            return f"camera_{c[4:]}"
        if c.startswith("kamera_"):
            return f"camera_{c[7:]}"
        if c.startswith("cam "):
            return f"camera_{c[4:]}"
        if c.startswith("camera "):
            return f"camera_{c[7:]}"
        if c.isdigit():
            return f"camera_{c}"
        return c


_context_planner: Optional[CameraContextPlanner] = None


def get_context_planner() -> CameraContextPlanner:
    global _context_planner
    if _context_planner is None:
        _context_planner = CameraContextPlanner()
    return _context_planner
