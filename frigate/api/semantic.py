"""FastAPI Router for Camera Semantic Map Management."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from frigate.semantic.map import get_semantic_map_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/semantic", tags=["Camera Semantic Map"])


@router.get("/cameras")
async def get_all_camera_semantics(request: Request):
    """Retrieve all camera semantic maps."""
    mgr = get_semantic_map_manager()
    semantics = mgr.get_all_camera_semantics()
    return JSONResponse(content={"cameras": semantics, "count": len(semantics)})


@router.get("/cameras/{camera_name}")
async def get_camera_semantic(camera_name: str, request: Request):
    """Retrieve semantic metadata for a single camera."""
    mgr = get_semantic_map_manager()
    semantic = mgr.get_camera_semantic(camera_name)
    return JSONResponse(content=semantic)


@router.put("/cameras/{camera_name}")
async def update_camera_semantic(camera_name: str, request: Request):
    """Update semantic metadata for a single camera."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    mgr = get_semantic_map_manager()
    updated = mgr.update_camera_semantic(camera_name, body)
    return JSONResponse(content={"success": True, "camera": updated})
