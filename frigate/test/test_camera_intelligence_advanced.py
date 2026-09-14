"""Tests for Advanced Camera Intelligence Q&A Engine, Gate/Vehicle Reasoning, and Gemini Escalation."""

import os
import unittest
from peewee import SqliteDatabase

from frigate.identity.manager import IdentityManager
from frigate.intelligence.engine import CameraIntelligenceEngine
from frigate.intelligence.gate_vehicle import get_gate_intelligence, get_vehicle_presence
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


class TestAdvancedCameraIntelligence(unittest.TestCase):
    def setUp(self):
        self.db = SqliteDatabase(":memory:")
        models = [
            CustomIdentity,
            IdentityReference,
            ObjectTrackRecord,
            ObjectSightingRecord,
            CameraAreaMapping,
            IdentitySettings,
            CameraSemanticMeta,
            EventRecord,
        ]
        self.db.bind(models)
        self.db.connect()
        self.db.create_tables(models)

        # Seed semantics
        get_semantic_map_manager()._init_seed_data()

    def tearDown(self):
        models = [
            CustomIdentity,
            IdentityReference,
            ObjectTrackRecord,
            ObjectSightingRecord,
            CameraAreaMapping,
            IdentitySettings,
            CameraSemanticMeta,
            EventRecord,
        ]
        self.db.drop_tables(models)
        self.db.close()

    def test_gate_qa_reasoning(self):
        gate_mgr = get_gate_intelligence()
        gate_mgr.set_gate_state("OPEN", confidence=0.95, associated_person="John")

        engine = CameraIntelligenceEngine()
        res = engine.ask_question("Is the gate open?")
        self.assertIn("OPEN", res["answer"])
        self.assertTrue(res["hallucination_guarantee_passed"])

    def test_vehicle_presence_qa_reasoning(self):
        veh_mgr = get_vehicle_presence()
        veh_mgr.record_vehicle_arrival("White Toyota", "CAR_01")
        veh_mgr.record_vehicle_arrival("Silver Honda", "CAR_02")

        engine = CameraIntelligenceEngine()
        res = engine.ask_question("Are both cars in the parking?")
        self.assertIn("both expected vehicles", res["answer"].lower())
        self.assertTrue(res["hallucination_guarantee_passed"])

    def test_dining_tv_rule_reasoning(self):
        engine = CameraIntelligenceEngine()
        res = engine.ask_question("Is the TV on in the dining room?")
        self.assertTrue(
            "tv" in res["answer"].lower()
            or "television" in res["answer"].lower()
            or "screen" in res["answer"].lower()
        )

    def test_gemini_escalation_integration(self):
        engine = CameraIntelligenceEngine()
        # When Gemini escalation is active, it inspects real camera context
        res = engine.ask_question("Analyze the detailed scene context", escalate_gemini=True)
        self.assertTrue(res["hallucination_guarantee_passed"])
        self.assertIn("answer", res)
        self.assertGreater(len(res["answer"]), 5)


if __name__ == "__main__":
    unittest.main()
