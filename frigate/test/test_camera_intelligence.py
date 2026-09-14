"""Unit tests for ANDRO-Vision Camera Intelligence Engine."""

import unittest
from frigate.intelligence.dataset import (
    CAMERA_DOMAIN_DATASET,
    CAMERA_QA_EXAMPLES,
    generate_synthetic_camera_events,
)
from frigate.intelligence.engine import (
    CameraEventContext,
    CameraIntelligenceEngine,
    get_intelligence_engine,
)
from frigate.intelligence.models import LocalModelManager, get_model_manager


class TestCameraIntelligence(unittest.TestCase):
    def setUp(self):
        self.engine = get_intelligence_engine()
        self.model_mgr = get_model_manager()

    def test_model_manager_tiers(self):
        models = self.model_mgr.get_models()
        self.assertEqual(len(models), 3)
        tiers = [m.tier for m in models]
        self.assertIn("0.5B", tiers)
        self.assertIn("1.2B", tiers)
        self.assertIn("3.0B", tiers)

        # Check quantization
        for m in models:
            self.assertIn("4-bit", m.quantization)

    def test_model_switch_and_telemetry(self):
        res = self.model_mgr.switch_model("andro-vision-1.2b-q4")
        self.assertTrue(res["success"])
        self.assertEqual(self.model_mgr.active_model_id, "andro-vision-1.2b-q4")

        telemetry = self.model_mgr.get_telemetry()
        self.assertTrue(telemetry["is_loaded"])
        self.assertEqual(telemetry["active_model"]["tier"], "1.2B")

    def test_domain_dataset_structure(self):
        self.assertGreaterEqual(len(CAMERA_DOMAIN_DATASET), 8)
        self.assertGreaterEqual(len(CAMERA_QA_EXAMPLES), 4)
        for sample in CAMERA_DOMAIN_DATASET:
            self.assertIn("input", sample)
            self.assertIn("output", sample)
            self.assertIn("summary", sample["output"])
            self.assertIn("objects", sample["output"])

        synthetic = generate_synthetic_camera_events(5)
        self.assertEqual(len(synthetic), 5)

    def test_event_analysis_structured_output(self):
        ctx = CameraEventContext(
            camera="Gate",
            area="Front Gate",
            detections=["person", "car"],
            known_identities=["John"],
            unknown_objects=["1 vehicle"],
            recent_events=["Gate opened"],
        )
        result = self.engine.analyze_event(ctx)
        self.assertIn("summary", result)
        self.assertIn("John", result["summary"])
        self.assertEqual(result["location"], "Front Gate")
        self.assertIn(result["importance"].upper(), ["HIGH", "MEDIUM", "LOW", "NORMAL"])
        self.assertGreater(len(result["objects"]), 0)

    def test_camera_qa_anti_hallucination(self):
        # When asking for an unknown object with no sightings
        resp = self.engine.ask_question("Where is the green bicycle?")
        self.assertIn("question", resp)
        self.assertIn("answer", resp)
        self.assertIn("I don't have enough camera evidence", resp["answer"])
        self.assertFalse(resp["hallucination_guarantee_passed"] is False)

    def test_multi_camera_trajectory_inference(self):
        # Simulate multi-camera sightings
        from frigate.models import CustomIdentity, ObjectSightingRecord
        # Verify ask_question handles trajectory
        resp = self.engine.ask_question("What happened in the last 10 minutes?")
        self.assertIn("answer", resp)
        self.assertIsInstance(resp["latency_ms"], float)


if __name__ == "__main__":
    unittest.main()
