"""Tests for Motion-Based Recording Manager and Vegetation Suppression Filter."""

import time
import unittest
from peewee import SqliteDatabase

from frigate.models import EventRecord
from frigate.motion.vegetation_filter import VegetationMotionFilter
from frigate.record.session import MotionRecordingManager


class TestMotionRecordingAndVegetation(unittest.TestCase):
    def setUp(self):
        self.db = SqliteDatabase(":memory:")
        self.db.bind([EventRecord])
        self.db.connect()
        self.db.create_tables([EventRecord])

    def tearDown(self):
        self.db.drop_tables([EventRecord])
        self.db.close()

    def test_vegetation_suppression(self):
        v_filter = VegetationMotionFilter(camera_name="camera_3")
        v_filter.vegetation_suppression_enabled = True

        # Pure raw pixel motion (e.g. blowing leaves / grass) -> should be suppressed
        is_meaningful, reason = v_filter.is_meaningful_activity(
            detections=[],
            raw_motion_boxes=[(10, 10, 50, 50), (100, 100, 150, 150)],
        )
        self.assertFalse(is_meaningful)
        self.assertEqual(reason, "suppressed_vegetation_motion")

        # Person detected -> should be meaningful
        is_meaningful_person, reason_person = v_filter.is_meaningful_activity(
            detections=[{"label": "person", "score": 0.88, "stationary": False}],
            raw_motion_boxes=[(10, 10, 50, 50)],
        )
        self.assertTrue(is_meaningful_person)
        self.assertEqual(reason_person, "classified_person")

        # Vehicle detected -> should be meaningful
        is_meaningful_car, reason_car = v_filter.is_meaningful_activity(
            detections=[{"label": "car", "score": 0.92, "stationary": False}],
        )
        self.assertTrue(is_meaningful_car)
        self.assertEqual(reason_car, "classified_car")

    def test_motion_recording_session_and_grace_period(self):
        command_log = []
        rec_mgr = MotionRecordingManager(
            on_record_command=lambda cam, en: command_log.append((cam, en))
        )
        rec_mgr.grace_period_seconds = 2.0  # short grace period for fast test

        # 1. Meaningful activity triggers recording start
        active = rec_mgr.process_camera_activity(
            camera_name="camera_1",
            detections=[{"label": "person", "score": 0.90, "stationary": False}],
        )
        self.assertTrue(active)
        self.assertTrue(rec_mgr.is_camera_recording("camera_1"))
        self.assertEqual(command_log[-1], ("camera_1", True))

        # 2. Activity stops, but within grace period -> remains recording
        active_grace = rec_mgr.process_camera_activity(
            camera_name="camera_1",
            detections=[],
        )
        self.assertTrue(active_grace)
        self.assertTrue(rec_mgr.is_camera_recording("camera_1"))

        # 3. New activity during grace period extends session
        rec_mgr.process_camera_activity(
            camera_name="camera_1",
            detections=[{"label": "person", "score": 0.95, "stationary": False}],
        )
        status = rec_mgr.get_session_status("camera_1")
        self.assertTrue(status["is_recording"])
        self.assertEqual(status["activity_count"], 2)


if __name__ == "__main__":
    unittest.main()
