"""Unit tests for Camera Light / Spotlight / Flash Control."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from frigate.camera.light import CameraLightManager, get_camera_light_manager


class TestCameraLight(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mgr = CameraLightManager()

    def test_default_state_is_off_and_manual_only(self):
        status = self.mgr.get_light_status("front_cam")
        self.assertEqual(status["camera"], "front_cam")
        self.assertTrue(status["supported"])
        self.assertEqual(status["state"], "off")

    async def test_turn_on_and_off(self):
        res_on = await self.mgr.turn_on("front_cam")
        self.assertTrue(res_on["success"])
        self.assertEqual(res_on["state"], "on")
        self.assertEqual(self.mgr.get_light_status("front_cam")["state"], "on")

        res_off = await self.mgr.turn_off("front_cam")
        self.assertTrue(res_off["success"])
        self.assertEqual(res_off["state"], "off")
        self.assertEqual(self.mgr.get_light_status("front_cam")["state"], "off")

    async def test_toggle_light(self):
        self.mgr.set_manual_state("driveway", "off")
        res1 = await self.mgr.toggle("driveway")
        self.assertEqual(res1["state"], "on")

        res2 = await self.mgr.toggle("driveway")
        self.assertEqual(res2["state"], "off")

    def test_set_unsupported_camera(self):
        self.mgr.set_supported("unsupported_cam", False)
        status = self.mgr.get_light_status("unsupported_cam")
        self.assertFalse(status["supported"])
        self.assertEqual(status["state"], "unavailable")

    def test_singleton_getter(self):
        mgr1 = get_camera_light_manager()
        mgr2 = get_camera_light_manager()
        self.assertIs(mgr1, mgr2)


if __name__ == "__main__":
    unittest.main()
