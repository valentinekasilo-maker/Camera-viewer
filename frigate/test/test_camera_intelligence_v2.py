"""Comprehensive Unit Tests for Upgraded ANDRO-Vision Camera Intelligence Engine."""

import datetime
import unittest
from peewee import SqliteDatabase

from frigate.identity.manager import IdentityManager, get_identity_manager
from frigate.intelligence.context_planner import get_context_planner
from frigate.intelligence.engine import CameraIntelligenceEngine, get_intelligence_engine
from frigate.intelligence.gate_vehicle import get_gate_intelligence, get_vehicle_presence
from frigate.intelligence.question_understanding import get_question_understanding_engine
from frigate.models import (
    CameraAreaMapping,
    CameraSemanticMeta,
    CustomIdentity,
    EventRecord,
    IdentityReference,
    IdentitySettings,
    ObjectSightingRecord,
    ObjectTrackRecord,
)
from frigate.semantic.map import get_semantic_map_manager


class TestCameraIntelligenceV2(unittest.TestCase):
    def setUp(self):
        self.db = SqliteDatabase(":memory:")
        self.models = [
            CustomIdentity,
            IdentityReference,
            ObjectTrackRecord,
            ObjectSightingRecord,
            CameraAreaMapping,
            IdentitySettings,
            CameraSemanticMeta,
            EventRecord,
        ]
        self.db.bind(self.models)
        self.db.connect()
        self.db.create_tables(self.models)

        # Seed semantic maps
        get_semantic_map_manager()._init_seed_data()

        # Seed test data
        now = datetime.datetime.now()

        # Seed vehicles
        CustomIdentity.create(
            id="veh_01",
            name="White Toyota",
            category="vehicle",
            object_class="car",
            color="white",
            is_person=False,
            status="present",
            last_seen_camera="camera_7",
            last_seen_location="Gate / Parking",
            last_seen_time=now - datetime.timedelta(minutes=5),
            first_seen_time=now - datetime.timedelta(hours=2),
            created_at=now,
            updated_at=now,
        )
        CustomIdentity.create(
            id="veh_02",
            name="Silver Honda",
            category="vehicle",
            object_class="car",
            color="silver",
            is_person=False,
            status="present",
            last_seen_camera="camera_7",
            last_seen_location="Gate / Parking",
            last_seen_time=now - datetime.timedelta(minutes=3),
            first_seen_time=now - datetime.timedelta(hours=2),
            created_at=now,
            updated_at=now,
        )

        # Seed person (John)
        CustomIdentity.create(
            id="person_01",
            name="John",
            category="person",
            object_class="person",
            is_person=True,
            status="present",
            last_seen_camera="camera_5",
            last_seen_location="Dining / Kitchen",
            last_seen_time=now - datetime.timedelta(minutes=10),
            first_seen_time=now - datetime.timedelta(hours=1),
            created_at=now,
            updated_at=now,
        )

        # Initialize Gate & Vehicle managers
        self.gate_mgr = get_gate_intelligence()
        self.veh_mgr = get_vehicle_presence()
        self.engine = get_intelligence_engine()

        # Set known baseline
        self.gate_mgr.set_gate_state("OPEN", confidence=0.94, associated_person="John")
        self.veh_mgr.record_vehicle_arrival("White Toyota", "CAR_01")
        self.veh_mgr.record_vehicle_arrival("Silver Honda", "CAR_02")

    def tearDown(self):
        self.db.drop_tables(self.models)
        self.db.close()

    def test_natural_variations_vehicle_questions(self):
        """Test flexible natural language questions about vehicles without exact keyword matching."""
        # 1. "Where is the white car?"
        r1 = self.engine.ask_question("Where is the white car?")
        self.assertIn("white toyota", r1["answer"].lower())
        self.assertIn("camera 7", r1["answer"].lower())
        self.assertTrue(r1["hallucination_guarantee_passed"])

        # 2. "Which camera saw the white car last?"
        r2 = self.engine.ask_question("Which camera saw the white car last?")
        self.assertIn("camera 7", r2["answer"].lower())

        # 3. "Are both cars still there?"
        r3 = self.engine.ask_question("Are both cars still there?")
        self.assertIn("both expected vehicles", r3["answer"].lower())

        # 4. "What changed in the parking area?"
        r4 = self.engine.ask_question("What changed in the parking area?")
        self.assertIn("parking", r4["answer"].lower())

    def test_multi_turn_conversational_memory_and_pronouns(self):
        """Test follow-up questions with pronouns ('it', 'he', 'she')."""
        sess = "test_conv_session_1"

        # Turn 1: Ask about white car
        r1 = self.engine.ask_question("Where is the white car?", session_id=sess)
        self.assertIn("white toyota", r1["answer"].lower())

        # Turn 2: "When was it last seen?" -> 'it' should refer to white car
        r2 = self.engine.ask_question("When was it last seen?", session_id=sess)
        self.assertIn("white toyota", r2["answer"].lower())
        self.assertEqual(r2["debug"]["entities"]["resolved_pronoun"], "it")

        # Turn 3: "Did it leave?" -> 'it' should refer to white car
        r3 = self.engine.ask_question("Did it leave?", session_id=sess)
        self.assertIn("parking", r3["answer"].lower())

        # Turn 4: Switch subject to John
        r4 = self.engine.ask_question("Where was John last seen?", session_id=sess)
        self.assertIn("john", r4["answer"].lower())
        self.assertIn("camera 5", r4["answer"].lower())

        # Turn 5: "Did he leave?" -> 'he' should refer to John with grounded uncertainty
        r5 = self.engine.ask_question("Did he leave?", session_id=sess)
        self.assertIn("can't confirm", r5["answer"].lower())
        self.assertIn("john", r5["answer"].lower())
        self.assertEqual(r5["debug"]["entities"]["resolved_pronoun"], "he")

    def test_gate_questions_and_temporal_reasoning(self):
        """Test gate state and temporal sequence reasoning."""
        # "Was the gate opened today?"
        r1 = self.engine.ask_question("Was the gate opened today?")
        self.assertIn("gate", r1["answer"].lower())
        self.assertIn("camera 7", r1["answer"].lower())

        # "Who came through the gate?"
        r2 = self.engine.ask_question("Who came through the gate?")
        self.assertIn("john", r2["answer"].lower())

        # "What happened before the gate opened?"
        r3 = self.engine.ask_question("What happened before the gate opened?")
        self.assertIn("camera 7", r3["answer"].lower())

    def test_camera_semantic_boundaries(self):
        """Test questions mapped to specific room cameras enforcing semantic visual areas."""
        # Backyard (Camera 3)
        r_backyard = self.engine.ask_question("Is there anyone in the backyard?")
        self.assertIn("backyard", r_backyard["answer"].lower())
        self.assertIn("camera 3", r_backyard["answer"].lower())

        # Small Kitchen (Camera 8)
        r_kitchen = self.engine.ask_question("Did someone go into the small kitchen?")
        self.assertIn("kitchen", r_kitchen["answer"].lower())

        # Veranda (Camera 4)
        r_veranda = self.engine.ask_question("Has anyone been in the veranda recently?")
        self.assertIn("veranda", r_veranda["answer"].lower())

        # Control Room (Camera 1)
        r_ctrl = self.engine.ask_question("Is someone in the control room?")
        self.assertIn("control room", r_ctrl["answer"].lower())
        self.assertIn("camera 1", r_ctrl["answer"].lower())

    def test_tv_state_dining_reasoning(self):
        """Test TV state reasoning in dining room."""
        r_tv = self.engine.ask_question("Is the TV on in the dining room?")
        self.assertIn("dining", r_tv["answer"].lower())
        self.assertTrue("tv" in r_tv["answer"].lower() or "television" in r_tv["answer"].lower() or "screen" in r_tv["answer"].lower())

    def test_anti_hallucination_on_unknown_objects(self):
        """Test strict anti-hallucination refusal when evidence is missing."""
        r_unknown = self.engine.ask_question("Where is the purple bicycle?")
        self.assertIn("don't have enough camera evidence", r_unknown["answer"].lower())
        self.assertTrue(r_unknown["hallucination_guarantee_passed"])

    def test_developer_debug_diagnostic_payload(self):
        """Test internal developer diagnostic debug block."""
        r = self.engine.ask_question("Where is the white car?")
        self.assertIn("debug", r)
        dbg = r["debug"]
        self.assertEqual(dbg["detected_intent"], "locate_entity")
        self.assertIn("tools_queried", dbg)
        self.assertIn("reasoning_context_size_chars", dbg)
        self.assertIsInstance(dbg["latency_ms"], float)


if __name__ == "__main__":
    unittest.main()
