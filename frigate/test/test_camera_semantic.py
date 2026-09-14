"""Tests for Camera Semantic Map."""

import unittest
from peewee import SqliteDatabase

from frigate.models import CameraSemanticMeta
from frigate.semantic.map import CameraSemanticMapManager, INITIAL_CAMERA_SEMANTICS


class TestCameraSemanticMap(unittest.TestCase):
    def setUp(self):
        self.db = SqliteDatabase(":memory:")
        self.db.bind([CameraSemanticMeta])
        self.db.connect()
        self.db.create_tables([CameraSemanticMeta])

    def tearDown(self):
        self.db.drop_tables([CameraSemanticMeta])
        self.db.close()

    def test_initial_seed_and_retrieval(self):
        mgr = CameraSemanticMapManager()
        semantics = mgr.get_all_camera_semantics()
        self.assertGreaterEqual(len(semantics), 8)

        # Check Camera 7 Gate and Parking
        cam7 = mgr.get_camera_semantic("camera_7")
        self.assertEqual(cam7["location"], "Gate / Parking")
        self.assertEqual(cam7["expected_vehicles"], 2)
        self.assertTrue(cam7["special_rules"].get("gate_state_machine"))

        # Check Camera 2 Dining & TV rule
        cam2 = mgr.get_camera_semantic("camera_2")
        self.assertEqual(cam2["location"], "Dining")
        self.assertIn("TV ON", cam2["special_rules"].get("tv_state_rule", ""))

        # Check Camera 3 Backyard & Vegetation rule
        cam3 = mgr.get_camera_semantic("camera_3")
        self.assertEqual(cam3["location"], "Backyard / Garden")
        self.assertTrue(cam3["special_rules"].get("vegetation_suppression"))

    def test_update_camera_semantic(self):
        mgr = CameraSemanticMapManager()
        updated = mgr.update_camera_semantic(
            "camera_7",
            {
                "description": "Updated main driveway and gate view.",
                "expected_vehicles": 3,
            },
        )
        self.assertEqual(updated["expected_vehicles"], 3)
        self.assertEqual(updated["description"], "Updated main driveway and gate view.")


if __name__ == "__main__":
    unittest.main()
