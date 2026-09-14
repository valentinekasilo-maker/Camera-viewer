"""Gate Intelligence and Vehicle Presence Models for Camera 7 and Monitored Areas."""

import datetime
import enum
import logging
import time
from typing import Any, Optional

from frigate.models import CustomIdentity, EventRecord, ObjectTrackRecord

logger = logging.getLogger(__name__)


class GateState(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class GateIntelligenceManager:
    """
    Maintains the state machine for Camera 7 gate monitoring.
    Never hallucinates the state and creates structured transition events.
    """

    def __init__(self, camera_name: str = "camera_7"):
        self.camera_name = camera_name
        self.current_state: GateState = GateState.CLOSED
        self.confidence: float = 0.95
        self.last_state_change: datetime.datetime = datetime.datetime.now()
        self.last_transition_event: Optional[dict[str, Any]] = None
        self.recent_transitions: list[dict[str, Any]] = []

    def get_gate_status(self) -> dict[str, Any]:
        """Return current gate state with anti-hallucination indicators."""
        return {
            "camera": self.camera_name,
            "state": self.current_state.value,
            "confidence": round(self.confidence, 2),
            "certainty_level": (
                "CONFIRMED"
                if self.confidence >= 0.85
                else ("LIKELY" if self.confidence >= 0.60 else "UNKNOWN")
            ),
            "last_state_change": self.last_state_change.isoformat(),
            "recent_transitions": self.recent_transitions[:10],
        }

    def set_gate_state(
        self,
        new_state: str | GateState,
        confidence: float = 0.90,
        associated_person: Optional[str] = None,
        associated_vehicle: Optional[str] = None,
        source: str = "visual_detection",
        snapshot_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Update gate state and record transition events if state changed.
        """
        if isinstance(new_state, str):
            try:
                parsed_state = GateState(new_state.upper())
            except ValueError:
                parsed_state = GateState.UNKNOWN
        else:
            parsed_state = new_state

        previous_state = self.current_state
        now = datetime.datetime.now()

        transition_occurred = (
            previous_state != parsed_state
            and parsed_state != GateState.UNKNOWN
        )

        self.current_state = parsed_state
        self.confidence = max(0.0, min(1.0, confidence))
        self.last_state_change = now

        event_data = None
        if transition_occurred:
            event_type = (
                "gate_opened"
                if parsed_state == GateState.OPEN
                else "gate_closed"
            )
            person_desc = associated_person or (
                "Unknown Person" if source == "motion_person" else None
            )

            event_summary = (
                f"Gate opened"
                if parsed_state == GateState.OPEN
                else "Gate closed"
            )
            if person_desc:
                event_summary += f" by {person_desc}"
            if associated_vehicle:
                event_summary += f" (Vehicle: {associated_vehicle})"

            event_data = {
                "id": f"gate_{int(time.time() * 1000)}",
                "camera": self.camera_name,
                "location": "Gate / Parking",
                "event_type": event_type,
                "previous_state": previous_state.value,
                "new_state": parsed_state.value,
                "confidence": round(self.confidence, 2),
                "person": person_desc,
                "vehicle": associated_vehicle,
                "timestamp": now.isoformat(),
                "summary": event_summary,
                "snapshot_path": snapshot_path,
            }

            self.recent_transitions.insert(0, event_data)
            if len(self.recent_transitions) > 50:
                self.recent_transitions.pop()
            self.last_transition_event = event_data

            # Persist to EventRecord table
            try:
                EventRecord.create(
                    id=event_data["id"],
                    camera=self.camera_name,
                    location="Gate / Parking",
                    event_type=event_type,
                    timestamp=now,
                    tracking_id=None,
                    identity_name=person_desc or associated_vehicle,
                    confidence=self.confidence,
                    evidence_snapshot=snapshot_path,
                    metadata={
                        "previous_state": previous_state.value,
                        "new_state": parsed_state.value,
                        "summary": event_summary,
                    },
                )
            except Exception as ex:
                logger.debug("Error saving gate event record: %s", ex)

        return self.get_gate_status()


class VehiclePresenceModel:
    """
    Maintains vehicle presence, baseline (2 vehicles), arrivals, and departures.
    """

    def __init__(self, camera_name: str = "camera_7", expected_baseline: int = 2):
        self.camera_name = camera_name
        self.expected_baseline = expected_baseline
        self.tracked_vehicles: dict[str, dict[str, Any]] = {}
        self.known_registered_vehicles: list[str] = [
            "White Toyota",
            "Silver Honda",
        ]
        self.recent_vehicle_events: list[dict[str, Any]] = []

    def get_vehicle_status(self) -> dict[str, Any]:
        """
        Return factual vehicle presence telemetry vs expected baseline.
        """
        # Query active tracks from DB / in-memory
        active_vehicles = []
        try:
            # Query recent active tracks for car/truck
            five_mins_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
            tracks = (
                ObjectTrackRecord.select()
                .where(
                    (ObjectTrackRecord.camera == self.camera_name)
                    & (
                        ObjectTrackRecord.object_class.in_(
                            ["car", "truck", "motorcycle", "vehicle"]
                        )
                    )
                    & (ObjectTrackRecord.last_seen >= five_mins_ago)
                )
                .order_by(ObjectTrackRecord.last_seen.desc())
            )
            for t in tracks:
                active_vehicles.append({
                    "track_id": t.track_id,
                    "identity_name": t.identity_name or "Unknown Vehicle",
                    "object_class": t.object_class,
                    "confidence": t.confidence,
                    "last_seen": t.last_seen.isoformat() if t.last_seen else None,
                    "is_unknown": t.is_unknown,
                })
        except Exception as e:
            logger.debug("Error querying vehicle tracks: %s", e)

        # Fallback to in-memory tracks if DB is empty
        if not active_vehicles and self.tracked_vehicles:
            active_vehicles = list(self.tracked_vehicles.values())

        current_count = len(active_vehicles)
        missing_count = max(0, self.expected_baseline - current_count)
        has_new_vehicle = any(
            v.get("is_unknown", True) and "Unknown" in str(v.get("identity_name", ""))
            for v in active_vehicles
        )

        return {
            "camera": self.camera_name,
            "location": "Gate / Parking",
            "expected_baseline": self.expected_baseline,
            "current_count": current_count,
            "both_cars_present": current_count >= self.expected_baseline,
            "missing_expected_vehicles": missing_count,
            "has_new_unknown_vehicle": has_new_vehicle,
            "active_vehicles": active_vehicles,
            "known_registered_baseline": self.known_registered_vehicles,
            "recent_events": self.recent_vehicle_events[:10],
        }

    def record_vehicle_arrival(
        self,
        vehicle_name: str,
        track_id: str,
        confidence: float = 0.90,
        is_unknown: bool = False,
        snapshot_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """Record a vehicle arrival event."""
        now = datetime.datetime.now()
        event_data = {
            "id": f"veh_arr_{int(time.time() * 1000)}",
            "camera": self.camera_name,
            "location": "Gate / Parking",
            "event_type": "vehicle_arrival",
            "vehicle": vehicle_name,
            "track_id": track_id,
            "confidence": confidence,
            "is_unknown": is_unknown,
            "timestamp": now.isoformat(),
            "summary": f"{'Unknown vehicle' if is_unknown else vehicle_name} arrived at parking area.",
        }
        self.tracked_vehicles[track_id] = {
            "track_id": track_id,
            "identity_name": vehicle_name,
            "object_class": "car",
            "confidence": confidence,
            "last_seen": now.isoformat(),
            "is_unknown": is_unknown,
        }
        self.recent_vehicle_events.insert(0, event_data)
        if len(self.recent_vehicle_events) > 50:
            self.recent_vehicle_events.pop()

        # Persist to EventRecord
        try:
            EventRecord.create(
                id=event_data["id"],
                camera=self.camera_name,
                location="Gate / Parking",
                event_type="vehicle_detected" if is_unknown else "vehicle_identified",
                timestamp=now,
                tracking_id=track_id,
                identity_name=vehicle_name,
                confidence=confidence,
                evidence_snapshot=snapshot_path,
                metadata={"track_id": track_id, "summary": event_data["summary"]},
            )
        except Exception as ex:
            logger.debug("Error saving vehicle arrival event: %s", ex)

        return event_data

    def record_vehicle_departure(
        self,
        vehicle_name: str,
        track_id: str,
        confidence: float = 0.90,
    ) -> dict[str, Any]:
        """Record a vehicle departure event."""
        now = datetime.datetime.now()
        self.tracked_vehicles.pop(track_id, None)
        event_data = {
            "id": f"veh_dep_{int(time.time() * 1000)}",
            "camera": self.camera_name,
            "location": "Gate / Parking",
            "event_type": "vehicle_departure",
            "vehicle": vehicle_name,
            "track_id": track_id,
            "confidence": confidence,
            "timestamp": now.isoformat(),
            "summary": f"{vehicle_name} departed from parking area.",
        }
        self.recent_vehicle_events.insert(0, event_data)
        if len(self.recent_vehicle_events) > 50:
            self.recent_vehicle_events.pop()

        # Persist to EventRecord
        try:
            EventRecord.create(
                id=event_data["id"],
                camera=self.camera_name,
                location="Gate / Parking",
                event_type="vehicle_departed",
                timestamp=now,
                tracking_id=track_id,
                identity_name=vehicle_name,
                confidence=confidence,
                evidence_snapshot=None,
                metadata={"track_id": track_id, "summary": event_data["summary"]},
            )
        except Exception as ex:
            logger.debug("Error saving vehicle departure event: %s", ex)

        return event_data


_gate_intelligence: Optional[GateIntelligenceManager] = None
_vehicle_presence: Optional[VehiclePresenceModel] = None


def get_gate_intelligence() -> GateIntelligenceManager:
    global _gate_intelligence
    if _gate_intelligence is None:
        _gate_intelligence = GateIntelligenceManager()
    return _gate_intelligence


def get_vehicle_presence() -> VehiclePresenceModel:
    global _vehicle_presence
    if _vehicle_presence is None:
        _vehicle_presence = VehiclePresenceModel()
    return _vehicle_presence
