"""Natural Language Question Understanding, Conversational Memory, and Query Planner for ANDRO-Vision."""

import datetime
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class StructuredQueryPlan:
    """Internal structured query representation separating question understanding from retrieval."""
    intent: str
    subject_type: Optional[str] = None
    subject: Optional[str] = None
    target_camera: Optional[str] = None
    target_location: Optional[str] = None
    time_range_seconds: int = 600
    time_description: str = "recent"
    required_evidence: list[str] = field(default_factory=list)
    requires_visual_inspection: bool = False
    is_followup: bool = False
    resolved_pronoun: Optional[str] = None
    comparison_type: Optional[str] = None
    original_question: str = ""


@dataclass
class ConversationTurn:
    question: str
    answer: str
    plan: StructuredQueryPlan
    timestamp: float


class ConversationalMemory:
    """Manages rolling short-term conversation context for multi-turn reasoning and coreference resolution."""

    def __init__(self, max_turns: int = 6):
        self.max_turns = max_turns
        self.sessions: dict[str, list[ConversationTurn]] = {}

    def get_history(self, session_id: str = "default") -> list[ConversationTurn]:
        return self.sessions.get(session_id, [])

    def record_turn(self, session_id: str, question: str, answer: str, plan: StructuredQueryPlan):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        turn = ConversationTurn(
            question=question,
            answer=answer,
            plan=plan,
            timestamp=datetime.datetime.now().timestamp(),
        )
        self.sessions[session_id].append(turn)
        if len(self.sessions[session_id]) > self.max_turns:
            self.sessions[session_id].pop(0)

    def get_last_subject(self, session_id: str = "default") -> Optional[tuple[str, str]]:
        """Returns (subject, subject_type) from recent turns."""
        turns = self.get_history(session_id)
        for t in reversed(turns):
            if t.plan.subject:
                return t.plan.subject, t.plan.subject_type or "object"
        return None

    def get_last_person(self, session_id: str = "default") -> Optional[str]:
        turns = self.get_history(session_id)
        for t in reversed(turns):
            if t.plan.subject_type == "person" and t.plan.subject and t.plan.subject.lower() not in ("person", "someone", "anyone", "he", "she"):
                return t.plan.subject
        for t in reversed(turns):
            if t.plan.subject_type == "person" and t.plan.subject:
                return t.plan.subject
        return None

    def get_last_vehicle(self, session_id: str = "default") -> Optional[str]:
        turns = self.get_history(session_id)
        for t in reversed(turns):
            if (t.plan.subject_type == "vehicle" or (t.plan.subject and any(w in t.plan.subject.lower() for w in ("car", "toyota", "honda", "vehicle", "harrier")))) and t.plan.subject:
                return t.plan.subject
        return None

    def get_last_camera(self, session_id: str = "default") -> Optional[tuple[str, str]]:
        turns = self.get_history(session_id)
        for t in reversed(turns):
            if t.plan.target_camera:
                return t.plan.target_camera, t.plan.target_location or ""
        return None


class QuestionUnderstandingEngine:
    """Analyzes natural language queries and builds structured execution plans."""

    CAMERA_KNOWLEDGE = {
        "camera_1": {"location": "Control Room", "keywords": ["control room", "server", "switch", "raspberry pi", "pc", "workstation", "wifi", "network", "equipment"]},
        "camera_2": {"location": "Dining", "keywords": ["tv", "television", "dining room tv", "screen", "tv screen", "dining"]},
        "camera_3": {"location": "Backyard", "keywords": ["backyard", "garden", "clothesline", "clothes", "hanging on the line", "line", "yard", "lawn", "plants", "foliage"]},
        "camera_4": {"location": "Veranda", "keywords": ["veranda", "porch", "play area", "patio", "kids", "children", "seating"]},
        "camera_5": {"location": "Dining / Kitchen Island", "keywords": ["dining", "kitchen island", "cabinets", "prep area", "island"]},
        "camera_6": {"location": "Entrance", "keywords": ["entrance", "front door", "doorstep", "front pathway", "porch steps", "door", "front", "entryway"]},
        "camera_7": {"location": "Gate / Parking", "keywords": ["gate", "parking", "driveway", "car", "cars", "vehicle", "vehicles", "toyota", "honda", "parking area", "bay"]},
        "camera_8": {"location": "Small Kitchen", "keywords": ["small kitchen", "washing area", "utility sink", "second kitchen", "kitchen sink", "back kitchen"]},
    }

    def __init__(self):
        self.memory = ConversationalMemory(max_turns=6)

    def parse_query(self, question: str, session_id: str = "default") -> StructuredQueryPlan:
        """Parse natural language question into structured query plan with conversational memory."""
        q_raw = question.strip()
        q_clean = q_raw.lower()

        # 1. Coreference & Pronoun Resolution
        resolved_subject, subject_type, is_followup, resolved_pronoun = self._resolve_pronouns(q_clean, session_id)

        # 2. Time Window & Sequence Resolution
        time_seconds, time_desc = self._parse_time_window(q_clean)

        # 3. Location / Camera Semantic Mapping
        target_cam, target_loc = self._resolve_camera_and_location(q_clean)

        # 4. Intent Classification & Subject Extraction
        intent, extracted_subject, extracted_type, comparison_type, req_visual = self._classify_intent_and_subject(
            q_clean, resolved_subject, subject_type
        )

        final_subject = extracted_subject or resolved_subject
        final_type = extracted_type or subject_type

        # Adjust target camera based on subject and visual semantic map if not explicitly specified
        if not target_cam:
            target_cam, target_loc = self._infer_camera_from_subject(final_subject, final_type, q_clean)

        # If still no camera, check if follow-up camera can be inherited
        if not target_cam and is_followup:
            last_cam_info = self.memory.get_last_camera(session_id)
            if last_cam_info:
                target_cam, target_loc = last_cam_info

        # Determine required evidence tools
        required_evidence = self._determine_required_evidence(intent, final_type, req_visual)

        return StructuredQueryPlan(
            intent=intent,
            subject_type=final_type,
            subject=final_subject,
            target_camera=target_cam,
            target_location=target_loc,
            time_range_seconds=time_seconds,
            time_description=time_desc,
            required_evidence=required_evidence,
            requires_visual_inspection=req_visual,
            is_followup=is_followup,
            resolved_pronoun=resolved_pronoun,
            comparison_type=comparison_type,
            original_question=q_raw,
        )

    def _resolve_pronouns(self, q_clean: str, session_id: str) -> tuple[Optional[str], Optional[str], bool, Optional[str]]:
        """Resolve pronouns ('it', 'he', 'she', 'they', 'both', 'that', 'that person', 'that car') using rolling memory."""
        words = set(re.findall(r"\b\w+\b", q_clean))

        # Check for person pronouns
        if "he" in words or "him" in words or "his" in words:
            last_person = self.memory.get_last_person(session_id)
            if last_person:
                return last_person, "person", True, "he"
            return "person", "person", True, "he"

        if "she" in words or "her" in words:
            last_person = self.memory.get_last_person(session_id)
            if last_person:
                return last_person, "person", True, "she"
            return "person", "person", True, "she"

        # Check for object / vehicle pronouns
        if "it" in words or "that" in words or "that car" in q_clean or "that vehicle" in q_clean or "this car" in q_clean:
            last_veh = self.memory.get_last_vehicle(session_id)
            if last_veh:
                return last_veh, "vehicle", True, "it"
            last_sub = self.memory.get_last_subject(session_id)
            if last_sub:
                return last_sub[0], last_sub[1], True, "it"
            return "vehicle", "vehicle", True, "it"

        if "both" in words or "both cars" in q_clean or "both vehicles" in q_clean:
            return "both vehicles", "vehicle", True, "both"

        if "they" in words or "them" in words:
            last_sub = self.memory.get_last_subject(session_id)
            if last_sub:
                return last_sub[0], last_sub[1], True, "they"

        return None, None, False, None

    def _parse_time_window(self, q_clean: str) -> tuple[int, str]:
        """Extract relative or absolute timeframe in seconds and human description."""
        # Minutes parsing: "last N minutes" or "N mins" or "past N minutes"
        m_match = re.search(r"(?:last|past|in the last|in the past)\s+(\d+)\s*(?:minutes|mins|m)\b", q_clean)
        if m_match:
            mins = int(m_match.group(1))
            return mins * 60, f"last {mins} minutes"

        if "last 5 minutes" in q_clean or "5 mins" in q_clean:
            return 300, "last 5 minutes"
        if "last 10 minutes" in q_clean or "10 mins" in q_clean or "past 10 minutes" in q_clean:
            return 600, "last 10 minutes"
        if "last 15 minutes" in q_clean or "15 mins" in q_clean:
            return 900, "last 15 minutes"
        if "last 30 minutes" in q_clean or "30 mins" in q_clean or "half hour" in q_clean:
            return 1800, "last 30 minutes"
        if "last hour" in q_clean or "past hour" in q_clean or "1 hour" in q_clean:
            return 3600, "last hour"
        if "today" in q_clean or "this morning" in q_clean or "this afternoon" in q_clean or "tonight" in q_clean or "all day" in q_clean:
            return 86400, "today"
        if "yesterday" in q_clean:
            return 172800, "yesterday"
        if "now" in q_clean or "currently" in q_clean or "right now" in q_clean or "at the moment" in q_clean or "presently" in q_clean:
            return 120, "now"
        if "recently" in q_clean or "earlier" in q_clean or "lately" in q_clean or "just now" in q_clean:
            return 1800, "recently"
        if "before the gate" in q_clean or "before that" in q_clean or "prior" in q_clean or "before" in q_clean:
            return 1800, "before event"
        if "after the gate" in q_clean or "after that" in q_clean or "since" in q_clean:
            return 1800, "after event"

        return 600, "recent"

    def _resolve_camera_and_location(self, q_clean: str) -> tuple[Optional[str], Optional[str]]:
        """Map camera mentions or area keywords to canonical camera ID and location name."""
        # Direct camera mentions ("camera 3", "cam 7", "kamera 2", "camera_5")
        cam_match = re.search(r"\b(?:camera|cam|kamera)[_\s]?(\d+)\b", q_clean)
        if cam_match:
            num = cam_match.group(1)
            cid = f"camera_{num}"
            if cid in self.CAMERA_KNOWLEDGE:
                return cid, self.CAMERA_KNOWLEDGE[cid]["location"]
            return cid, f"Camera {num}"

        # Match location keywords
        if "small kitchen" in q_clean or "utility sink" in q_clean or "second kitchen" in q_clean or "washing area" in q_clean:
            return "camera_8", "Small Kitchen"
        if "control room" in q_clean or "server room" in q_clean or "raspberry pi" in q_clean:
            return "camera_1", "Control Room"
        if "backyard" in q_clean or "garden" in q_clean or "clothesline" in q_clean or "clothes line" in q_clean:
            return "camera_3", "Backyard"
        if "veranda" in q_clean or "patio" in q_clean or "play area" in q_clean:
            return "camera_4", "Veranda"
        if "entrance" in q_clean or "front door" in q_clean or "porch steps" in q_clean or "front pathway" in q_clean:
            return "camera_6", "Entrance"
        if "gate" in q_clean or "parking" in q_clean or "driveway" in q_clean:
            return "camera_7", "Gate / Parking"
        if "tv" in q_clean or "television" in q_clean:
            return "camera_2", "Dining"
        if "kitchen" in q_clean or "kitchen island" in q_clean or "dining" in q_clean:
            return "camera_5", "Dining / Kitchen Island"

        return None, None

    def _infer_camera_from_subject(self, subject: Optional[str], subject_type: Optional[str], q_clean: str) -> tuple[Optional[str], Optional[str]]:
        """Infer target camera when question does not explicitly name one."""
        if not subject:
            return None, None

        sub_l = subject.lower()
        if subject_type == "vehicle" or any(w in sub_l for w in ("car", "toyota", "honda", "vehicle", "parking", "harrier", "sedan")):
            return "camera_7", "Gate / Parking"
        if any(w in sub_l for w in ("tv", "television")):
            return "camera_2", "Dining"
        if any(w in sub_l for w in ("clothes", "clothesline", "garden", "backyard")):
            return "camera_3", "Backyard"
        if any(w in sub_l for w in ("small kitchen", "utility")):
            return "camera_8", "Small Kitchen"
        if any(w in sub_l for w in ("veranda", "play area")):
            return "camera_4", "Veranda"
        if any(w in sub_l for w in ("control room", "server", "switch", "raspberry")):
            return "camera_1", "Control Room"
        if any(w in sub_l for w in ("entrance", "front door")):
            return "camera_6", "Entrance"
        if any(w in sub_l for w in ("gate", "driveway")):
            return "camera_7", "Gate / Parking"

        return None, None

    def _classify_intent_and_subject(
        self,
        q_clean: str,
        resolved_subject: Optional[str],
        resolved_type: Optional[str],
    ) -> tuple[str, Optional[str], Optional[str], Optional[str], bool]:
        """Classify user intent, subject, subject type, comparison type, and visual necessity."""

        # 1. Visual Inspection Triggers (requiring frame snapshot inspection)
        if any(phrase in q_clean for phrase in (
            "clothes on the line", "hanging on the line", "clothes hanging", "clothesline",
            "is the tv screen on", "is the tv on", "is anyone watching tv", "screen currently on", "is the tv currently on",
            "standing behind the car", "next to the door", "carrying a", "carrying the", "what is that object",
            "is the gate actually open", "is the gate physically open", "is the screen on"
        )):
            subject = resolved_subject or ("clothes" if "clothes" in q_clean else ("TV" if "tv" in q_clean else "scene"))
            return "visual_inspection", subject, "object", None, True

        # 2. Gate State & Gate Activity Queries
        if "gate" in q_clean:
            if any(w in q_clean for w in ("who opened", "who came through", "who went through", "who entered through", "who was at the gate", "who was there")):
                return "gate_transition_person", "gate", "gate", "actor", False
            if any(w in q_clean for w in ("what happened before", "what happened when", "what happened after", "what happened around the gate")):
                return "event_sequence", "gate", "gate", "sequence", False
            if any(w in q_clean for w in ("open", "closed", "state", "status", "is the gate", "was the gate", "opened today", "opened")):
                return "gate_status", "gate", "gate", None, False
            return "gate_status", "gate", "gate", None, False

        # 3. Vehicle Baseline, Departure, Arrival, Location Queries
        if any(w in q_clean for w in ("car", "cars", "vehicle", "vehicles", "toyota", "honda", "parking", "harrier", "sedan", "auto")):
            if any(w in q_clean for w in ("both", "both cars", "both vehicles", "are both", "all cars", "two cars")):
                return "vehicle_baseline", "both vehicles", "vehicle", "both", False
            if any(w in q_clean for w in ("which car left", "did a car leave", "did the car leave", "did it leave", "missing", "departed", "left")):
                car_name = self._extract_named_entity(q_clean, ["white toyota", "silver honda", "white car", "silver car", "toyota", "honda", "car", "vehicle"])
                return "vehicle_departure", car_name or resolved_subject or "vehicle", "vehicle", "departure", False
            if any(w in q_clean for w in ("new car", "unknown car", "unknown vehicle", "new vehicle", "arrive", "arrived", "somebody arrive", "did somebody arrive")):
                return "vehicle_arrival", resolved_subject or "vehicle", "vehicle", "arrival", False
            if any(w in q_clean for w in ("where is", "where was", "which camera saw", "last seen", "locate", "where's", "where did")):
                car_name = self._extract_named_entity(q_clean, ["white toyota", "silver honda", "white car", "silver car", "black car", "toyota", "honda", "car", "vehicle"])
                return "locate_entity", car_name or resolved_subject or "vehicle", "vehicle", None, False
            if any(w in q_clean for w in ("what changed", "changes in", "parking area")):
                return "activity_summary", "parking area", "location", "change", False
            if any(w in q_clean for w in ("still there", "still in", "parked", "present")):
                car_name = self._extract_named_entity(q_clean, ["white toyota", "silver honda", "white car", "silver car", "toyota", "honda", "car", "vehicle"])
                return "vehicle_presence", car_name or resolved_subject or "vehicle", "vehicle", None, False
            return "vehicle_presence", resolved_subject or "vehicle", "vehicle", None, False

        # 4. Last Person Detected Queries ("Who was the last person detected?", "Who was the last person seen?")
        if "last person" in q_clean or "last detected person" in q_clean or "who was the last person" in q_clean or "who was last seen" in q_clean:
            return "last_person_detected", "person", "person", "last_detected", False

        # 5. Person Location & Last Seen Queries ("Where was John last seen?", "Where is Alice?", "Where was he last?", "Which camera saw John?")
        if any(w in q_clean for w in ("where is", "where was", "which camera saw", "last seen", "where did", "where's", "where was he", "where was she", "where he was")):
            person_name = self._extract_named_entity(q_clean, ["john", "alice", "bob", "he", "she", "person", "someone", "visitor"])
            if person_name in ("he", "she") and resolved_subject:
                person_name = resolved_subject
            return "locate_entity", person_name or resolved_subject or "person", "person", None, False

        # 6. Departure Checks ("Did John leave?", "Did he leave?", "Did she leave?", "Did it leave?")
        if any(w in q_clean for w in ("did he leave", "did she leave", "did john leave", "did alice leave", "did bob leave", "did it leave", "did they leave", "has he left", "has she left", "has john left")):
            if resolved_type == "vehicle" or (resolved_subject and any(w in resolved_subject.lower() for w in ("car", "toyota", "honda", "vehicle"))):
                return "departure_check", resolved_subject or "vehicle", "vehicle", "departure", False
            person_name = self._extract_named_entity(q_clean, ["john", "alice", "bob", "he", "she"])
            if person_name in ("he", "she") and resolved_subject:
                person_name = resolved_subject
            return "departure_check", person_name or resolved_subject or "person", "person", "departure", False

        # 7. Presence & Room Activity Checks ("Did anyone enter the house?", "Is there anyone in the backyard?", "Did someone go into the small kitchen?", "Has anyone been in the veranda recently?")
        if any(w in q_clean for w in (
            "is there anyone", "is anyone", "is someone", "is somebody",
            "has anyone been", "has someone been", "has anyone",
            "did someone go", "did anyone enter", "did somebody go", "did anyone go",
            "anyone in", "someone in", "somebody in", "people in",
            "is someone in", "is anyone in"
        )):
            loc = self._extract_location_mention(q_clean)
            return "presence_check", loc or "house", "location", "presence", False

        # 8. Activity Summary & Time-Window Queries ("What happened in the last 10 minutes?", "Show me what happened around the gate", "What happened before that?")
        if any(w in q_clean for w in ("what happened", "recent activity", "show me what happened", "what occurred", "summary", "activity", "what changed", "show events")):
            loc = self._extract_location_mention(q_clean)
            return "activity_summary", loc or resolved_subject or "activity", "event", None, False

        # 9. Follow-up handling with conversational memory
        if resolved_subject:
            if any(w in q_clean for w in ("last seen", "when was", "where", "where was", "which camera")):
                return "locate_entity", resolved_subject, resolved_type or "object", None, False
            if any(w in q_clean for w in ("still there", "present", "exist", "is it there")):
                return "presence_check", resolved_subject, resolved_type or "object", "presence", False
            if any(w in q_clean for w in ("leave", "left", "depart", "gone")):
                return "departure_check", resolved_subject, resolved_type or "object", "departure", False

        # 10. General Reasoning Fallback
        return "general_reasoning", resolved_subject or "security_system", "system", None, False

    def _extract_named_entity(self, q_clean: str, candidates: list[str]) -> Optional[str]:
        for c in candidates:
            if c in q_clean:
                if c not in ("he", "she", "it", "person", "someone", "visitor", "car", "vehicle"):
                    return c.title()
                return c

        m = re.search(r"where\s+(?:is|was)\s+(?:the\s+)?([a-zA-Z0-9\s_]+)\??", q_clean)
        if m:
            val = m.group(1).strip()
            val = re.sub(r"\b(last seen|last|seen)\b", "", val).strip()
            if val and len(val) > 1:
                return val.title()
        return None

    def _extract_location_mention(self, q_clean: str) -> Optional[str]:
        if "small kitchen" in q_clean or "utility" in q_clean:
            return "Small Kitchen"
        if "control room" in q_clean or "server" in q_clean:
            return "Control Room"
        if "backyard" in q_clean or "garden" in q_clean:
            return "Backyard"
        if "veranda" in q_clean or "patio" in q_clean:
            return "Veranda"
        if "entrance" in q_clean or "front door" in q_clean:
            return "Entrance"
        if "gate" in q_clean or "parking" in q_clean or "driveway" in q_clean:
            return "Gate / Parking"
        if "dining" in q_clean:
            return "Dining"
        if "kitchen" in q_clean:
            return "Dining / Kitchen Island"
        if "house" in q_clean:
            return "House"
        return None

    def _determine_required_evidence(self, intent: str, subject_type: Optional[str], requires_visual: bool) -> list[str]:
        tools = []
        if requires_visual:
            tools.append("request_visual_analysis")

        if intent in ("gate_status", "gate_transition_person", "event_sequence"):
            tools.extend(["get_gate_state", "get_gate_events", "get_recent_events", "get_camera_state"])
        elif intent in ("vehicle_baseline", "vehicle_departure", "vehicle_arrival", "vehicle_presence"):
            tools.extend(["get_current_vehicles", "find_vehicle", "get_camera_state", "get_recent_events"])
        elif intent == "last_person_detected":
            tools.extend(["find_person", "get_recent_events", "get_last_seen"])
        elif intent in ("locate_entity", "departure_check"):
            if subject_type == "vehicle":
                tools.extend(["find_vehicle", "get_last_seen", "get_camera_state", "get_current_vehicles"])
            elif subject_type == "person":
                tools.extend(["find_person", "get_last_seen", "get_recent_events", "get_camera_state"])
            else:
                tools.extend(["find_object", "get_last_seen", "get_camera_state"])
        elif intent == "presence_check":
            tools.extend(["get_camera_state", "get_recent_events", "find_person"])
        elif intent == "activity_summary":
            tools.extend(["get_recent_events", "get_gate_events", "get_camera_state"])
        else:
            tools.extend(["get_camera_state", "get_recent_events"])

        return list(dict.fromkeys(tools))


_question_engine: Optional[QuestionUnderstandingEngine] = None


def get_question_understanding_engine() -> QuestionUnderstandingEngine:
    global _question_engine
    if _question_engine is None:
        _question_engine = QuestionUnderstandingEngine()
    return _question_engine
