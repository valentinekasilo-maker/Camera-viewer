"""API endpoints for Custom Objects & Identity Tracking in ANDRO-Vision."""

import io
import logging
import os
from typing import Any, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from frigate.api.auth import allow_any_authenticated, allow_public
from frigate.api.defs.tags import Tags
from frigate.identity.manager import IdentityManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=[Tags.identities])

_identity_mgr: Optional[IdentityManager] = None


def get_identity_manager() -> IdentityManager:
    global _identity_mgr
    if _identity_mgr is None:
        _identity_mgr = IdentityManager()
    return _identity_mgr


class IdentityCreateRequest(BaseModel):
    name: str
    object_class: str
    category: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    confidence_threshold: Optional[float] = None


class IdentityUpdateRequest(BaseModel):
    name: Optional[str] = None
    object_class: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    confidence_threshold: Optional[float] = None


class CameraAreaUpdateItem(BaseModel):
    camera: str
    area: str
    notes: Optional[str] = ""


class SettingsUpdateRequest(BaseModel):
    matching_threshold_object: Optional[float] = None
    matching_threshold_person: Optional[float] = None
    unknown_object_threshold: Optional[float] = None
    track_timeout_seconds: Optional[int] = None
    presence_timeout_seconds: Optional[int] = None
    away_timeout_seconds: Optional[int] = None
    recognition_cooldown_seconds: Optional[int] = None
    max_reference_images: Optional[int] = None
    cross_camera_window_seconds: Optional[int] = None
    enable_cross_camera_tracking: Optional[bool] = None


class IdentifyTrackRequest(BaseModel):
    action: str  # "create_new" or "link_existing"
    identity_id: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None


# -------------------------------------------------------------------------
# 1. Top-Level List & Creation
# -------------------------------------------------------------------------

@router.get("/identities", dependencies=[Depends(allow_any_authenticated())])
async def list_identities(
    object_class: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    """Retrieve list of registered custom identities and their current status."""
    mgr = get_identity_manager()
    identities = mgr.get_identities(
        object_class=object_class,
        category=category,
        search=search,
    )
    return JSONResponse(content={"success": True, "identities": identities})


@router.post("/identities", dependencies=[Depends(allow_any_authenticated())])
async def create_identity(
    name: str = Form(...),
    object_class: str = Form(...),
    category: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    confidence_threshold: Optional[float] = Form(None),
    photos: list[UploadFile] = File(None),
):
    """Register a new custom object or person identity with optional reference photos."""
    mgr = get_identity_manager()
    identity = mgr.create_identity(
        name=name,
        object_class=object_class,
        category=category,
        color=color,
        description=description,
        notes=notes,
        confidence_threshold=confidence_threshold,
    )

    # Process and attach uploaded reference photos
    if photos:
        for photo in photos:
            if photo.filename:
                contents = await photo.read()
                if len(contents) > 0:
                    mgr.add_reference_image(
                        identity_id=identity["id"],
                        image_bytes=contents,
                        notes=photo.filename,
                    )

    # Re-fetch full details including added references
    detailed = mgr.get_identity(identity["id"])
    return JSONResponse(content={"success": True, "identity": detailed})


# -------------------------------------------------------------------------
# 2. Configuration & Settings (Must precede parameterized /identities/{id})
# -------------------------------------------------------------------------

@router.get("/identities/config", dependencies=[Depends(allow_any_authenticated())])
async def get_identity_settings():
    """Retrieve identity tracking configuration and thresholds."""
    mgr = get_identity_manager()
    settings = mgr.get_settings()
    return JSONResponse(content={"success": True, "config": settings})


@router.put("/identities/config", dependencies=[Depends(allow_any_authenticated())])
async def update_identity_settings(body: SettingsUpdateRequest):
    """Update identity matching and tracking configuration."""
    mgr = get_identity_manager()
    updated = mgr.update_settings(**body.model_dump(exclude_unset=True))
    return JSONResponse(content={"success": True, "config": updated})


# -------------------------------------------------------------------------
# 3. Camera to Area Mappings
# -------------------------------------------------------------------------

@router.get("/identities/camera-areas", dependencies=[Depends(allow_any_authenticated())])
async def get_camera_areas():
    """Get camera to area mapping."""
    mgr = get_identity_manager()
    mappings = mgr.get_camera_area_mappings()
    return JSONResponse(content={"success": True, "camera_areas": mappings})


@router.put("/identities/camera-areas", dependencies=[Depends(allow_any_authenticated())])
async def update_camera_areas(items: list[CameraAreaUpdateItem]):
    """Update camera to area mappings."""
    mgr = get_identity_manager()
    updated = []
    for item in items:
        res = mgr.update_camera_area(
            camera=item.camera,
            area=item.area,
            notes=item.notes or "",
        )
        updated.append(res)
    return JSONResponse(content={"success": True, "camera_areas": updated})


# -------------------------------------------------------------------------
# 4. Active Tracks & Unknown Queue
# -------------------------------------------------------------------------

@router.get("/identities/tracks/active", dependencies=[Depends(allow_any_authenticated())])
async def list_active_tracks():
    """Get real-time tracked objects and people across all cameras."""
    mgr = get_identity_manager()
    tracks = mgr.get_active_tracks()
    return JSONResponse(content={"success": True, "tracks": tracks, "count": len(tracks)})


@router.get("/identities/tracks/unknown", dependencies=[Depends(allow_any_authenticated())])
async def list_unknown_tracks(limit: int = Query(50, ge=1, le=200)):
    """Get unknown objects / unrecognized people queue for user review and enrollment."""
    mgr = get_identity_manager()
    unknowns = mgr.get_unknown_queue(limit=limit)
    return JSONResponse(content={"success": True, "unknowns": unknowns, "count": len(unknowns)})


@router.post("/identities/tracks/{track_id}/identify", dependencies=[Depends(allow_any_authenticated())])
async def identify_track(track_id: str, body: IdentifyTrackRequest):
    """Confirm/enroll an unknown track as a new custom identity or link to existing identity."""
    mgr = get_identity_manager()
    if body.action == "create_new":
        if not body.name:
            raise HTTPException(status_code=400, detail="Name is required for new identity")
        res = mgr.enroll_unknown_as_new(
            track_id=track_id,
            name=body.name,
            category=body.category,
            color=body.color,
            notes=body.notes,
        )
    elif body.action == "link_existing":
        if not body.identity_id:
            raise HTTPException(status_code=400, detail="identity_id is required to link")
        res = mgr.link_unknown_to_existing(
            track_id=track_id,
            identity_id=body.identity_id,
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    if not res:
        raise HTTPException(status_code=404, detail="Track not found or identification failed")

    return JSONResponse(content={"success": True, "result": res})


@router.delete("/identities/tracks/{track_id}", dependencies=[Depends(allow_any_authenticated())])
async def dismiss_unknown_track(track_id: str):
    """Dismiss an unknown track from the review queue."""
    mgr = get_identity_manager()
    success = mgr.dismiss_unknown_track(track_id)
    if not success:
        raise HTTPException(status_code=404, detail="Track not found")
    return JSONResponse(content={"success": True, "message": "Track dismissed"})


# -------------------------------------------------------------------------
# 5. Sightings & Movement History
# -------------------------------------------------------------------------

@router.get("/identities/history", dependencies=[Depends(allow_any_authenticated())])
async def get_sightings_history(
    identity_id: Optional[str] = None,
    camera: Optional[str] = None,
    area: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
):
    """Retrieve object and people sightings and location history log."""
    mgr = get_identity_manager()
    history = mgr.get_sightings_history(
        identity_id=identity_id,
        camera=camera,
        area=area,
        limit=limit,
    )
    return JSONResponse(content={"success": True, "history": history, "count": len(history)})


# -------------------------------------------------------------------------
# 6. Reference Images & Snapshots Serving
# -------------------------------------------------------------------------

@router.get("/identities/reference-image/{ref_id}", dependencies=[Depends(allow_public())])
async def get_reference_image(ref_id: str):
    """Stream stored local reference image for an identity."""
    mgr = get_identity_manager()
    path = mgr.get_reference_image_path(ref_id)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/identities/track-snapshot/{track_id}", dependencies=[Depends(allow_public())])
async def get_track_snapshot(track_id: str):
    """Stream stored local snapshot image for a tracked object/person."""
    mgr = get_identity_manager()
    path = mgr.get_track_snapshot_path(track_id)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return FileResponse(path, media_type="image/jpeg")


@router.delete("/identities/references/{reference_id}", dependencies=[Depends(allow_any_authenticated())])
async def delete_reference(reference_id: str):
    """Delete a single reference image."""
    mgr = get_identity_manager()
    success = mgr.delete_reference_image(reference_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reference not found")
    return JSONResponse(content={"success": True, "message": "Reference deleted"})


# -------------------------------------------------------------------------
# 7. Parameterized Identity Operations (Must be last)
# -------------------------------------------------------------------------

@router.get("/identities/{identity_id}", dependencies=[Depends(allow_any_authenticated())])
async def get_identity_detail(identity_id: str):
    """Get single identity details, reference photos, sighting history, and presence."""
    mgr = get_identity_manager()
    identity = mgr.get_identity(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")
    return JSONResponse(content={"success": True, "identity": identity})


@router.put("/identities/{identity_id}", dependencies=[Depends(allow_any_authenticated())])
async def update_identity(identity_id: str, body: IdentityUpdateRequest):
    """Update identity metadata and matching threshold."""
    mgr = get_identity_manager()
    updated = mgr.update_identity(identity_id, **body.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Identity not found")
    return JSONResponse(content={"success": True, "identity": updated})


@router.delete("/identities/{identity_id}", dependencies=[Depends(allow_any_authenticated())])
async def delete_identity(identity_id: str):
    """Permanently remove a registered identity, reference images, and unbind sightings."""
    mgr = get_identity_manager()
    deleted = mgr.delete_identity(identity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Identity not found")
    return JSONResponse(content={"success": True, "message": "Identity deleted successfully"})


@router.post("/identities/{identity_id}/references", dependencies=[Depends(allow_any_authenticated())])
async def add_references(identity_id: str, photos: list[UploadFile] = File(...)):
    """Upload additional reference images to an existing identity."""
    mgr = get_identity_manager()
    identity = mgr.get_identity(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")

    added = []
    for photo in photos:
        if photo.filename:
            contents = await photo.read()
            if len(contents) > 0:
                ref = mgr.add_reference_image(
                    identity_id=identity_id,
                    image_bytes=contents,
                    notes=photo.filename,
                )
                if ref:
                    added.append(ref)

    return JSONResponse(content={"success": True, "added_count": len(added), "references": added})
