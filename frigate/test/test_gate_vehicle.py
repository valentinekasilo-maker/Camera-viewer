"""Tests for Gate Intelligence and Vehicle Presence Models."""

import unittest
from peewee import SqliteDatabase

from frigate.intelligence.gate_vehicle import (
    GateIntelligenceManager,
    GateState,
    VehiclePresenceModel,
)
from frigate.models import EventRecord, ObjectTrackRecord


class TestGateAndVehicleIntelligence(unittest.TestCase):
    def setUp(self):
        self.db = SqliteDatabase(":memory:")
        self.db.bind([EventRecord, ObjectTrackRecord])
        self.db.connect()
        self.db.create_tables([EventRecord, ObjectTrackRecord])

    def tearDown(self):
        self.db.drop_tables([EventRecord, ObjectTrackRecord])
        self.db.close()

    def test_gate_state_machine_and_transitions(self):
        gate_mgr = GateIntelligenceManager(camera_name="camera_7")
        status = gate_mgr.get_gate_status()
        self.assertEqual(status["state"], "CLOSED")
        self.assertEqual(status["certainty_level"], "CONFIRMED")

        # Open gate with identified person
        res = gate_mgr.set_gate_state(
            new_state=GateState.OPEN,
            confidence=0.94,
            associated_person="John",
        )
        self.assertEqual(res["state"], "OPEN")
        self.assertGreaterEqual(len(res["recent_transitions"]), 1)
        self.assertEqual(res["recent_transitions"][0]["person"], "John")

        # Verify event recorded in DB
        events = list(EventRecord.select().where(EventRecord.event_type == "gate_opened"))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].identity_name, "John")

        # Close gate
        res2 = gate_mgr.set_gate_state(
            new_state=GateState.CLOSED,
            confidence=0.90,
            associated_person="John",
        )
        self.assertEqual(res2["state"], "CLOSED")
        self.assertEqual(len(res2["recent_transitions"]), 2)

    def test_vehicle_presence_baseline(self):
        veh_mgr = VehiclePresenceModel(camera_name="camera_7", expected_baseline=2)
        status = veh_mgr.get_vehicle_status()
        self.assertEqual(status["expected_baseline"], 2)

        # Record arrival of vehicle 1
        arr1 = veh_mgr.record_vehicle_arrival(
            vehicle_name="White Toyota",
            track_id="CAR_01",
            confidence=0.95,
        )
        self.assertEqual(arr1["vehicle"], "White Toyota")

        # Record arrival of vehicle 2
        arr2 = veh_mgr.record_vehicle_arrival(
            vehicle_name="Silver Honda",
            track_id="CAR_02",
            confidence=0.92,
        )
        self.assertEqual(arr2["vehicle"], "Silver Honda")

        status2 = veh_mgr.get_vehicle_status()
        self.assertEqual(status2["current_count"], 2)
        self.assertTrue(status2["both_cars_present"])
        self.assertEqual(status2["missing_expected_vehicles"], 0)

        # Record departure
        veh_mgr.record_vehicle_departure("White Toyota", "CAR_01")
        status3 = veh_mgr.get_vehicle_status()
        self.assertEqual(status3["current_count"], 1)
        self.assertFalse(status3["both_cars_present"])
        self.assertEqual(status3["missing_expected_vehicles"], 1)


if __name__ == "__main__":
    unittest.main()
