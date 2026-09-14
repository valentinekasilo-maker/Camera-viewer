"""FastAPI endpoints for Camera Light / Spotlight / Flash Control."""

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import JSONResponse

from frigate.api.auth import allow_any_authenticated
from frigate.api.defs.tags import Tags
from frigate.camera.light import get_camera_light_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=[Tags.camera])


@router.get("/cameras/{camera_name}/light", dependencies=[Depends(allow_any_authenticated())])
async def get_camera_light(camera_name: str = Path(...)):
    """Get current spotlight / light hardware status for a camera."""
    mgr = get_camera_light_manager()
    status = mgr.get_light_status(camera_name)
    return JSONResponse(content={"success": True, **status})


@router.post("/cameras/{camera_name}/light/on", dependencies=[Depends(allow_any_authenticated())])
async def turn_on_camera_light(camera_name: str = Path(...)):
    """Turn ON camera spotlight / white LED manually."""
    mgr = get_camera_light_manager()
    result = await mgr.turn_on(camera_name)
    return JSONResponse(content=result)


@router.post("/cameras/{camera_name}/light/off", dependencies=[Depends(allow_any_authenticated())])
async def turn_off_camera_light(camera_name: str = Path(...)):
    """Turn OFF camera spotlight / white LED manually."""
    mgr = get_camera_light_manager()
    result = await mgr.turn_off(camera_name)
    return JSONResponse(content=result)


@router.post("/cameras/{camera_name}/light/toggle", dependencies=[Depends(allow_any_authenticated())])
async def toggle_camera_light(camera_name: str = Path(...)):
    """Toggle camera spotlight / white LED state."""
    mgr = get_camera_light_manager()
    result = await mgr.toggle(camera_name)
    return JSONResponse(content=result)
