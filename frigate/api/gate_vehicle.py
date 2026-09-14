"""FastAPI Router for Gate Intelligence, Vehicle Presence, Timeline Events, and Environment Snapshots."""

import datetime
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from frigate.intelligence.environment import get_environment_snapshot_scheduler
from frigate.intelligence.gate_vehicle import get_gate_intelligence, get_vehicle_presence
from frigate.intelligence.gemini_escalation import analyze_with_gemini_vision
from frigate.models import EventRecord
from frigate.record.session import get_motion_recording_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Gate, Vehicles & Timeline"])


@router.get("/gate")
async def get_gate_status(request: Request):
    """Retrieve Camera 7 gate status and recent transition history."""
    gate_mgr = get_gate_intelligence()
    return JSONResponse(content=gate_mgr.get_gate_status())


@router.post("/gate/set")
async def set_gate_state(request: Request):
    """Update Camera 7 gate state (e.g. OPEN / CLOSED) and log transition event."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    state = body.get("state", "UNKNOWN")
    confidence = float(body.get("confidence", 0.90))
    person = body.get("person")
    vehicle = body.get("vehicle")
    snapshot = body.get("snapshot_path")

    gate_mgr = get_gate_intelligence()
    updated = gate_mgr.set_gate_state(
        new_state=state,
        confidence=confidence,
        associated_person=person,
        associated_vehicle=vehicle,
        snapshot_path=snapshot,
    )
    return JSONResponse(content={"success": True, "gate": updated})


@router.get("/vehicles")
async def get_vehicle_status(request: Request):
    """Retrieve Camera 7 vehicle status vs expected baseline (2 vehicles)."""
    veh_mgr = get_vehicle_presence()
    return JSONResponse(content=veh_mgr.get_vehicle_status())


@router.post("/vehicles/arrival")
async def record_vehicle_arrival(request: Request):
    """Record vehicle arrival on Camera 7."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    vehicle_name = body.get("vehicle_name", "Unknown Vehicle")
    track_id = body.get("track_id", f"CAR_{int(datetime.datetime.now().timestamp())}")
    confidence = float(body.get("confidence", 0.90))
    is_unknown = bool(body.get("is_unknown", False))
    snapshot_path = body.get("snapshot_path")

    veh_mgr = get_vehicle_presence()
    event = veh_mgr.record_vehicle_arrival(
        vehicle_name=vehicle_name,
        track_id=track_id,
        confidence=confidence,
        is_unknown=is_unknown,
        snapshot_path=snapshot_path,
    )
    return JSONResponse(content={"success": True, "event": event})


@router.post("/vehicles/departure")
async def record_vehicle_departure(request: Request):
    """Record vehicle departure from Camera 7."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    vehicle_name = body.get("vehicle_name", "Unknown Vehicle")
    track_id = body.get("track_id", "")
    confidence = float(body.get("confidence", 0.90))

    veh_mgr = get_vehicle_presence()
    event = veh_mgr.record_vehicle_departure(
        vehicle_name=vehicle_name,
        track_id=track_id,
        confidence=confidence,
    )
    return JSONResponse(content={"success": True, "event": event})


@router.get("/timeline")
async def get_event_timeline(
    request: Request,
    camera: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    """Retrieve unified event timeline memory from SQLite."""
    try:
        query = EventRecord.select().order_by(EventRecord.timestamp.desc())
        if camera:
            query = query.where(EventRecord.camera == camera)
        if event_type:
            query = query.where(EventRecord.event_type == event_type)

        records = list(query.limit(limit))
        events = [
            {
                "id": r.id,
                "camera": r.camera,
                "location": r.location,
                "event_type": r.event_type,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "tracking_id": r.tracking_id,
                "identity_name": r.identity_name,
                "confidence": r.confidence,
                "evidence_snapshot": r.evidence_snapshot,
                "metadata": r.metadata,
            }
            for r in records
        ]
        return JSONResponse(content={"events": events, "count": len(events)})
    except Exception as e:
        logger.debug("Timeline query error: %s", e)
        return JSONResponse(content={"events": [], "count": 0})


@router.get("/snapshots/environment")
async def get_environment_snapshots(
    request: Request,
    camera: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
):
    """Retrieve recent 30-minute representative environmental scene snapshots."""
    scheduler = get_environment_snapshot_scheduler()
    snapshots = scheduler.get_recent_snapshots(camera=camera, limit=limit)
    return JSONResponse(content={"snapshots": snapshots, "count": len(snapshots)})


@router.get("/recordings/sessions/{camera_name}")
async def get_recording_session_status(camera_name: str, request: Request):
    """Retrieve active motion recording session status with remaining grace period."""
    mgr = get_motion_recording_manager()
    status = mgr.get_session_status(camera_name)
    return JSONResponse(content=status)


@router.post("/gemini/analyze")
async def escalate_gemini_vision(request: Request):
    """Request on-demand Level 2 Gemini Deep Visual Reasoning for selected evidence."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    camera_id = body.get("camera_id", "all")
    question = body.get("question", "Analyze the camera scene.")
    event_ids = body.get("event_ids")
    images = body.get("images")
    context = body.get("context")

    result = analyze_with_gemini_vision(
        camera_id=camera_id,
        question=question,
        event_ids=event_ids,
        images=images,
        context=context,
    )
    return JSONResponse(content=result)
