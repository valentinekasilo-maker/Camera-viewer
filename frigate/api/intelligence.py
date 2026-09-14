"""FastAPI endpoints for ANDRO-Vision Camera Intelligence Engine."""

import logging
import os
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from frigate.api.auth import allow_any_authenticated
from frigate.api.defs.tags import Tags
from frigate.intelligence.dataset import CAMERA_DOMAIN_DATASET, CAMERA_QA_EXAMPLES
from frigate.intelligence.engine import get_intelligence_engine
from frigate.intelligence.gemini_escalation import analyze_with_gemini_vision, resolve_camera_snapshot_path
from frigate.intelligence.models import get_model_manager
from frigate.semantic.map import get_semantic_map_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=[Tags.camera])


class ModelActionRequest(BaseModel):
    model_id: str


class EventAnalysisRequest(BaseModel):
    camera: str
    area: Optional[str] = None
    detections: list[str] = []
    known_identities: list[str] = []
    unknown_objects: list[str] = []
    raw_track_id: Optional[str] = None
    priority: Optional[str] = "NORMAL"


class AskQuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default"
    escalate_gemini: Optional[bool] = False


class InspectCameraRequest(BaseModel):
    camera: str
    question: Optional[str] = "Describe what is happening in this camera frame in detail."


@router.get("/intelligence/models", dependencies=[Depends(allow_any_authenticated())])
async def list_intelligence_models():
    """List available local camera specialist models, quantization specs, and active loaded status."""
    mgr = get_model_manager()
    models = mgr.get_available_models()
    telemetry = mgr.get_active_model_info()
    return JSONResponse(content={"success": True, "models": models, "telemetry": telemetry})


@router.post("/intelligence/models/load", dependencies=[Depends(allow_any_authenticated())])
async def load_intelligence_model(body: ModelActionRequest):
    """Load a specific camera specialist model tier into memory."""
    mgr = get_model_manager()
    try:
        telemetry = mgr.load_model(body.model_id)
        return JSONResponse(content={"success": True, "telemetry": telemetry})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/intelligence/models/unload", dependencies=[Depends(allow_any_authenticated())])
async def unload_intelligence_model():
    """Unload the active camera specialist model from memory."""
    mgr = get_model_manager()
    telemetry = mgr.unload_model()
    return JSONResponse(content={"success": True, "telemetry": telemetry})


@router.post("/intelligence/models/switch", dependencies=[Depends(allow_any_authenticated())])
async def switch_intelligence_model(body: ModelActionRequest):
    """Switch active model tier."""
    mgr = get_model_manager()
    try:
        telemetry = mgr.switch_model(body.model_id)
        return JSONResponse(content={"success": True, "telemetry": telemetry})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/intelligence/analyze-event", dependencies=[Depends(allow_any_authenticated())])
async def analyze_camera_event(body: EventAnalysisRequest):
    """Run structured camera scene and event understanding."""
    engine = get_intelligence_engine()
    result = engine.analyze_event_direct(body.model_dump())
    return JSONResponse(content={"success": True, "understanding": result})


@router.post("/intelligence/ask", dependencies=[Depends(allow_any_authenticated())])
async def ask_camera_question(body: AskQuestionRequest):
    """Ask natural language questions about camera telemetry, sightings, and identities."""
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    engine = get_intelligence_engine()
    result = engine.ask_question(
        question=body.question.strip(),
        session_id=body.session_id or "default",
        escalate_gemini=bool(body.escalate_gemini),
    )
    return JSONResponse(content={"success": True, "response": result})


@router.post("/intelligence/inspect-camera", dependencies=[Depends(allow_any_authenticated())])
async def inspect_camera_with_gemini(body: InspectCameraRequest):
    """Directly inspect camera frame snapshot with Gemini Multimodal Vision."""
    sem_mgr = get_semantic_map_manager()
    sem_meta = sem_mgr.get_camera_semantic(body.camera)
    loc_name = sem_meta.get("location") or body.camera

    result = analyze_with_gemini_vision(
        camera_id=body.camera,
        question=body.question or "Describe what you see in this camera frame.",
        context={"location": loc_name, "visible_areas": sem_meta.get("visible_areas")},
    )
    return JSONResponse(content={"success": True, "result": result})


@router.get("/intelligence/cameras/{camera_id}/snapshot", dependencies=[Depends(allow_any_authenticated())])
async def get_camera_snapshot_image(camera_id: str):
    """Serve the latest snapshot image for a camera."""
    path = resolve_camera_snapshot_path(camera_id)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No snapshot found for camera {camera_id}")

    media_type = "image/webp" if path.endswith(".webp") else "image/jpeg"
    return FileResponse(path, media_type=media_type)


@router.get("/intelligence/semantic-feed", dependencies=[Depends(allow_any_authenticated())])
async def get_semantic_feed(limit: int = Query(30, ge=1, le=100)):
    """Retrieve real-time semantic event understandings feed."""
    engine = get_intelligence_engine()
    feed = engine.get_semantic_feed(limit=limit)
    return JSONResponse(content={"success": True, "feed": feed, "count": len(feed)})


@router.get("/intelligence/dataset-sample", dependencies=[Depends(allow_any_authenticated())])
async def get_dataset_sample():
    """View curated camera domain training dataset scenarios and Q&A benchmarks."""
    return JSONResponse(content={
        "success": True,
        "scenarios": CAMERA_DOMAIN_DATASET,
        "qa_benchmarks": CAMERA_QA_EXAMPLES,
    })
