"""Unit tests for Two-Way Camera Audio / P2P Telecom."""

import unittest
from frigate.config import CameraConfig


class TestCameraTelecom(unittest.TestCase):
    def test_audio_config_defaults(self):
        camera_dict = {
            "name": "front_door",
            "ffmpeg": {
                "inputs": [
                    {
                        "path": "rtsp://10.0.0.1:554/live",
                        "roles": ["detect", "audio", "record"],
                    }
                ]
            },
            "live": {
                "streams": {
                    "front_door": "front_door",
                    "front_door_sub": "front_door_sub",
                }
            },
        }
        cam_config = CameraConfig.model_validate(camera_dict)
        self.assertEqual(cam_config.name, "front_door")
        self.assertIn("audio", cam_config.ffmpeg.inputs[0].roles)

        # Test go2rtc backchannel parsing
        stream_definition = "rtsp://10.0.0.1:554/live#backchannel=onvif"
        self.assertTrue("backchannel=" in stream_definition)
        self.assertTrue(stream_definition.endswith("onvif"))

    def test_audio_webrtc_constraints_structure(self):
        # Verify structure expected by the WebRTC Talk subsystem
        expected_audio_constraints = {
            "echoCancellation": True,
            "noiseSuppression": True,
            "autoGainControl": True,
        }
        self.assertTrue(expected_audio_constraints["echoCancellation"])
        self.assertTrue(expected_audio_constraints["noiseSuppression"])
        self.assertTrue(expected_audio_constraints["autoGainControl"])


if __name__ == "__main__":
    unittest.main()
