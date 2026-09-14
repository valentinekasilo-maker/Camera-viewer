"""Comprehensive Scenario Test Suite for ANDRO-Vision Camera Intelligence Engine."""

import datetime
import unittest
from peewee import SqliteDatabase

from frigate.identity.manager import get_identity_manager
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


class TestCameraIntelligenceScenarios(unittest.TestCase):
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

        now = datetime.datetime.now()

        # Seed vehicles
        CustomIdentity.create(
            id="veh_toyota",
            name="White Toyota",
            category="vehicle",
            object_class="car",
            color="white",
            is_person=False,
            status="present",
            last_seen_camera="camera_7",
            last_seen_location="Gate / Parking",
            last_seen_time=now - datetime.timedelta(minutes=4),
            first_seen_time=now - datetime.timedelta(hours=3),
            created_at=now,
            updated_at=now,
        )
        CustomIdentity.create(
            id="veh_honda",
            name="Silver Honda",
            category="vehicle",
            object_class="car",
            color="silver",
            is_person=False,
            status="present",
            last_seen_camera="camera_7",
            last_seen_location="Gate / Parking",
            last_seen_time=now - datetime.timedelta(minutes=2),
            first_seen_time=now - datetime.timedelta(hours=3),
            created_at=now,
            updated_at=now,
        )

        # Seed person (John)
        CustomIdentity.create(
            id="person_john",
            name="John",
            category="person",
            object_class="person",
            is_person=True,
            status="present",
            last_seen_camera="camera_5",
            last_seen_location="Dining / Kitchen Island",
            last_seen_time=now - datetime.timedelta(minutes=12),
            first_seen_time=now - datetime.timedelta(hours=2),
            created_at=now,
            updated_at=now,
        )

        # Seed event records
        EventRecord.create(
            id="ev_001",
            camera="camera_7",
            location="Gate / Parking",
            event_type="vehicle_detected",
            identity_name="White Toyota",
            confidence=0.94,
            timestamp=now - datetime.timedelta(minutes=6),
        )
        EventRecord.create(
            id="ev_002",
            camera="camera_7",
            location="Gate / Parking",
            event_type="person_detected",
            identity_name="John",
            confidence=0.96,
            timestamp=now - datetime.timedelta(minutes=5),
        )
        EventRecord.create(
            id="ev_003",
            camera="camera_6",
            location="Entrance",
            event_type="entry_door",
            identity_name="John",
            confidence=0.95,
            timestamp=now - datetime.timedelta(minutes=4),
        )

        # Initialize gate & vehicle states
        self.gate_mgr = get_gate_intelligence()
        self.veh_mgr = get_vehicle_presence()
        self.gate_mgr.set_gate_state("OPEN", confidence=0.95, associated_person="John")
        self.veh_mgr.record_vehicle_arrival("White Toyota", "CAR_01")
        self.veh_mgr.record_vehicle_arrival("Silver Honda", "CAR_02")

        self.engine = get_intelligence_engine()

    def tearDown(self):
        self.db.drop_tables(self.models)
        self.db.close()

    def test_scenario_01_where_is_white_car(self):
        """'Where is the white car?' -> Camera 7 parking."""
        res = self.engine.ask_question("Where is the white car?")
        self.assertIn("camera 7", res["answer"].lower())
        self.assertTrue("white toyota" in res["answer"].lower() or "white car" in res["answer"].lower() or "parking" in res["answer"].lower())

    def test_scenario_02_which_camera_saw_white_car(self):
        """'Which camera saw the white car last?' -> Camera 7."""
        res = self.engine.ask_question("Which camera saw the white car last?")
        self.assertIn("camera 7", res["answer"].lower())

    def test_scenario_03_did_anyone_enter_house(self):
        """'Did anyone enter the house?' -> Entrance Camera 6 reasoning."""
        res = self.engine.ask_question("Did anyone enter the house?")
        self.assertTrue("entrance" in res["answer"].lower() or "camera 6" in res["answer"].lower())

    def test_scenario_04_who_came_through_gate(self):
        """'Who came through the gate?' -> John."""
        res = self.engine.ask_question("Who came through the gate?")
        self.assertIn("john", res["answer"].lower())

    def test_scenario_05_was_gate_opened_today(self):
        """'Was the gate opened today?' -> Yes, open/opened on Camera 7."""
        res = self.engine.ask_question("Was the gate opened today?")
        self.assertTrue("opened" in res["answer"].lower() or "open" in res["answer"].lower())
        self.assertIn("camera 7", res["answer"].lower())

    def test_scenario_06_is_anyone_in_backyard(self):
        """'Is there anyone in the backyard?' -> Camera 3 foliage filtering."""
        res = self.engine.ask_question("Is there anyone in the backyard?")
        self.assertIn("camera 3", res["answer"].lower())
        self.assertIn("backyard", res["answer"].lower())

    def test_scenario_07_are_both_cars_still_there(self):
        """'Are both cars still there?' -> Yes, Camera 7."""
        res = self.engine.ask_question("Are both cars still there?")
        self.assertIn("camera 7", res["answer"].lower())
        self.assertTrue("both" in res["answer"].lower() or "expected vehicles" in res["answer"].lower())

    def test_scenario_08_which_car_left(self):
        """'Which car left?' -> Neither has left."""
        res = self.engine.ask_question("Which car left?")
        self.assertTrue("neither" in res["answer"].lower() or "both" in res["answer"].lower() or "camera 7" in res["answer"].lower())

    def test_scenario_09_small_kitchen_check(self):
        """'Did someone go into the small kitchen?' -> Camera 8."""
        res = self.engine.ask_question("Did someone go into the small kitchen?")
        self.assertTrue("kitchen" in res["answer"].lower() or "camera 8" in res["answer"].lower())

    def test_scenario_10_veranda_check(self):
        """'Has anyone been in the veranda recently?' -> Camera 4."""
        res = self.engine.ask_question("Has anyone been in the veranda recently?")
        self.assertIn("veranda", res["answer"].lower())

    def test_scenario_11_activity_in_last_10_minutes(self):
        """'What happened in the last 10 minutes?' -> Event summary."""
        res = self.engine.ask_question("What happened in the last 10 minutes?")
        self.assertIn("activity", res["answer"].lower())

    def test_scenario_12_show_what_happened_around_gate(self):
        """'Show me what happened around the gate.' -> Gate event sequence."""
        res = self.engine.ask_question("Show me what happened around the gate.")
        self.assertIn("camera 7", res["answer"].lower())

    def test_scenario_13_was_tv_on_or_watching(self):
        """'Was the TV on?' / 'Is anyone watching TV?' -> Camera 2 Dining TV rule."""
        res1 = self.engine.ask_question("Was the TV on?")
        self.assertTrue("camera 2" in res1["answer"].lower() or "tv" in res1["answer"].lower() or "dining" in res1["answer"].lower())

        res2 = self.engine.ask_question("Is anyone watching TV?")
        self.assertTrue("camera 2" in res2["answer"].lower() or "tv" in res2["answer"].lower() or "dining" in res2["answer"].lower())

    def test_scenario_14_last_person_detected(self):
        """'Who was the last person detected?' -> John on Camera 5/6."""
        res = self.engine.ask_question("Who was the last person detected?")
        self.assertIn("john", res["answer"].lower())

    def test_scenario_15_where_was_john_last_seen(self):
        """'Where was John last seen?' -> Camera 5 Dining / Kitchen."""
        res = self.engine.ask_question("Where was John last seen?")
        self.assertIn("john", res["answer"].lower())
        self.assertTrue("camera 5" in res["answer"].lower() or "dining" in res["answer"].lower() or "kitchen" in res["answer"].lower())

    def test_scenario_16_did_john_leave_missing_info_handling(self):
        """'Did John leave?' -> Cannot confirm departure without exit event."""
        res = self.engine.ask_question("Did John leave?")
        self.assertTrue("can't confirm" in res["answer"].lower() or "last" in res["answer"].lower())
        self.assertIn("john", res["answer"].lower())

    def test_scenario_17_what_happened_before_gate_opened(self):
        """'What happened before the gate opened?' -> Preceding detection sequence."""
        res = self.engine.ask_question("What happened before the gate opened?")
        self.assertTrue("before" in res["answer"].lower() or "gate" in res["answer"].lower())

    def test_scenario_18_conversational_pronoun_chain(self):
        """Test multi-step conversation: 'Where is the white car?' -> 'When was it last seen?' -> 'Did it leave?'"""
        sess = "chain_sess_01"
        r1 = self.engine.ask_question("Where is the white car?", session_id=sess)
        self.assertIn("white toyota", r1["answer"].lower())

        r2 = self.engine.ask_question("When was it last seen?", session_id=sess)
        self.assertIn("white toyota", r2["answer"].lower())
        self.assertEqual(r2["debug"]["entities"]["resolved_pronoun"], "it")

        r3 = self.engine.ask_question("Did it leave?", session_id=sess)
        self.assertTrue("parking" in r3["answer"].lower() or "not left" in r3["answer"].lower() or "present" in r3["answer"].lower())


if __name__ == "__main__":
    unittest.main()
