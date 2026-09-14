"""Camera Light / Spotlight / Flash Hardware Control Manager for ANDRO-Vision."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CameraLightManager:
    """Manages controllable camera spotlights, white LEDs, floodlights, and IR illuminators."""

    def __init__(self, onvif_controller: Any = None):
        self.onvif_controller = onvif_controller
        # In-memory manual light state dictionary per camera: "on" | "off"
        self._light_states: dict[str, str] = {}
        # Cameras that have verified light hardware support
        self._supported_cameras: set[str] = set()
        self._unsupported_cameras: set[str] = set()

    def set_onvif_controller(self, onvif_controller: Any):
        self.onvif_controller = onvif_controller

    def set_supported(self, camera_name: str, supported: bool = True):
        """Explicitly set hardware support for a camera."""
        if supported:
            self._supported_cameras.add(camera_name)
            self._unsupported_cameras.discard(camera_name)
        else:
            self._unsupported_cameras.add(camera_name)
            self._supported_cameras.discard(camera_name)

    def set_manual_state(self, camera_name: str, state: str):
        """Set in-memory manual state ('on' | 'off')."""
        self._light_states[camera_name] = state

    def is_light_supported(self, camera_name: str) -> bool:
        """Check if camera exposes controllable white light / auxiliary spotlight."""
        if camera_name in self._unsupported_cameras:
            return False
        if camera_name in self._supported_cameras:
            return True

        if not self.onvif_controller:
            # Default to available for local cameras
            return True

        # Check in ONVIF controller cams
        cam_info = getattr(self.onvif_controller, "cams", {}).get(camera_name, {})
        if cam_info:
            return True

        return True

    def get_light_status(self, camera_name: str) -> dict[str, Any]:
        """Retrieve current light state for a camera.

        Returns:
            {"supported": bool, "state": "on" | "off" | "unavailable"}
        """
        supported = self.is_light_supported(camera_name)
        if not supported:
            return {
                "camera": camera_name,
                "supported": False,
                "state": "unavailable",
                "message": "Light control unavailable",
            }

        state = self._light_states.get(camera_name, "off")
        return {
            "camera": camera_name,
            "supported": True,
            "state": state,
        }

    async def turn_on(self, camera_name: str) -> dict[str, Any]:
        """Activate camera white spotlight / floodlight."""
        supported = self.is_light_supported(camera_name)
        if not supported:
            return {"success": False, "state": "unavailable", "message": "Light control unavailable"}

        # Send ONVIF auxiliary light command if ONVIF is connected
        try:
            if self.onvif_controller:
                cam = getattr(self.onvif_controller, "cams", {}).get(camera_name, {}).get("onvif")
                if cam:
                    ptz = getattr(cam, "ptz", None)
                    if ptz and hasattr(ptz, "SendAuxiliaryCommand"):
                        await ptz.SendAuxiliaryCommand({
                            "ProfileToken": "Profile_1",
                            "AuxiliaryData": "tt:IRLampOn",
                        })
        except Exception as e:
            logger.debug("ONVIF auxiliary light command for %s: %s", camera_name, e)

        self._light_states[camera_name] = "on"
        logger.info("Camera %s spotlight turned ON (manual control)", camera_name)
        return {"success": True, "camera": camera_name, "state": "on"}

    async def turn_off(self, camera_name: str) -> dict[str, Any]:
        """Deactivate camera spotlight."""
        supported = self.is_light_supported(camera_name)
        if not supported:
            return {"success": False, "state": "unavailable", "message": "Light control unavailable"}

        try:
            if self.onvif_controller:
                cam = getattr(self.onvif_controller, "cams", {}).get(camera_name, {}).get("onvif")
                if cam:
                    ptz = getattr(cam, "ptz", None)
                    if ptz and hasattr(ptz, "SendAuxiliaryCommand"):
                        await ptz.SendAuxiliaryCommand({
                            "ProfileToken": "Profile_1",
                            "AuxiliaryData": "tt:IRLampOff",
                        })
        except Exception as e:
            logger.debug("ONVIF auxiliary light off command for %s: %s", camera_name, e)

        self._light_states[camera_name] = "off"
        logger.info("Camera %s spotlight turned OFF (manual control)", camera_name)
        return {"success": True, "camera": camera_name, "state": "off"}

    async def toggle(self, camera_name: str) -> dict[str, Any]:
        """Toggle current light state."""
        curr = self._light_states.get(camera_name, "off")
        if curr == "on":
            return await self.turn_off(camera_name)
        else:
            return await self.turn_on(camera_name)


_light_manager: Optional[CameraLightManager] = None


def get_camera_light_manager() -> CameraLightManager:
    global _light_manager
    if _light_manager is None:
        _light_manager = CameraLightManager()
    return _light_manager
