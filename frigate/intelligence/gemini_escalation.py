"""Level 2 Gemini Vision & Reasoning Escalation Module for On-Demand Deep Camera Understanding."""

import logging
import os
from pathlib import Path
from typing import Any, Optional
from PIL import Image

logger = logging.getLogger(__name__)

# Primary and fallback Gemini models
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-2.5-pro",
    "gemini-flash-latest",
]


def _load_env_if_needed():
    """Load environment variables from .env file if available."""
    env_path = Path(".env")
    if env_path.exists() and not os.environ.get("GEMINI_API_KEY"):
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            pass


def get_gemini_client():
    """Instantiate and return official Google GenAI client."""
    _load_env_if_needed()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as e:

        logger.debug("Failed to initialize Google GenAI client: %s", e)
        return None


def resolve_camera_snapshot_path(camera_id: str) -> Optional[str]:
    """Find the latest snapshot file for a camera in config/camera_snapshots/ or root."""
    if not camera_id:
        return None

    clean_id = camera_id.lower().replace("camera_", "kamera_").replace("cam_", "kamera_")
    if not clean_id.startswith("kamera_"):
        clean_id = f"kamera_{clean_id}"

    candidates = [
        Path(f"config/camera_snapshots/{clean_id}.jpg"),
        Path(f"config/camera_snapshots/{clean_id}.webp"),
        Path(f"config/camera_snapshots/{camera_id}.jpg"),
        Path(f"config/camera_snapshots/{camera_id}.webp"),
        Path(f"test_{camera_id}.jpg"),
        Path(f"test_{clean_id}.jpg"),
        Path("test_cam1.jpg"),
    ]
    if camera_id and camera_id[-1].isdigit():
        num = camera_id[-1]
        candidates.extend([
            Path(f"config/camera_snapshots/kamera_{num}.jpg"),
            Path(f"test_cam{num}.jpg"),
        ])

    for p in candidates:
        if p and p.exists() and p.stat().st_size > 0:
            return str(p)
    return None


def analyze_with_gemini_vision(
    camera_id: str,
    question: str,
    image_path: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    On-demand Level 2 Deep Visual Reasoning escalation.
    Used ONLY when visual inspection of camera frames is required (e.g., clothesline, TV screen,
    unidentified objects, obscure scene details) or on explicit user request.

    Never runs continuously or streams raw video feeds.
    """
    client = get_gemini_client()
    if not client:
        return {
            "success": False,
            "escalated": False,
            "error": "gemini_unconfigured",
            "message": "Deep visual analysis is unavailable. Answering using local camera telemetry and tracking.",
            "answer": "Deep visual analysis is unavailable. Answering using local camera telemetry and tracking.",
            "source": "level1_fallback",
        }

    # Resolve snapshot image
    resolved_img_path = image_path or resolve_camera_snapshot_path(camera_id)
    pil_image = None
    if resolved_img_path and Path(resolved_img_path).exists():
        try:
            pil_image = Image.open(resolved_img_path)
        except Exception as e:
            logger.debug("Could not load snapshot image for Gemini vision: %s", e)

    # Construct structured prompt
    ctx_str = f"\nCamera Location & Semantic Scope: {context}\n" if context else ""
    prompt_text = (
        f"You are the visual inspection subsystem of the ANDRO-Vision NVR Security Intelligence System.\n"
        f"Target Camera: {camera_id}\n"
        f"{ctx_str}"
        f"User Question: {question}\n\n"
        f"Strict Guidelines:\n"
        f"1. Carefully inspect the camera frame.\n"
        f"2. Answer the question accurately, naturally, and concisely in 1-2 clear sentences.\n"
        f"3. Do NOT make up objects or people not present in the frame.\n"
        f"4. If something is not clearly visible or uncertain, state that honestly."
    )

    contents: list[Any] = [prompt_text]
    if pil_image:
        contents.insert(0, pil_image)

    last_error = None
    for model_name in GEMINI_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
            )
            if response and hasattr(response, "text") and response.text:
                answer = response.text.strip()
                return {
                    "success": True,
                    "escalated": True,
                    "model": f"Gemini Vision ({model_name})",
                    "camera_id": camera_id,
                    "snapshot_used": resolved_img_path,
                    "question": question,
                    "answer": answer,
                    "source": "gemini_level2_vision",
                }
        except Exception as e:
            last_error = str(e)
            logger.debug("Gemini vision model %s failed: %s, trying next", model_name, e)

    logger.debug("All Gemini vision models failed or unavailable: %s", last_error)
    return {
        "success": False,
        "escalated": False,
        "error": last_error or "vision_api_error",
        "message": "Visual analysis could not be completed at this time.",
        "answer": "Visual analysis could not be completed at this time.",
        "source": "level1_fallback",
    }


def reason_with_gemini(
    system_prompt: str,
    user_prompt: str,
    context: Optional[dict[str, Any]] = None,
    conversation_history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """
    On-demand Level 2 Deep Language Reasoning for complex multi-event, multi-camera, and conversational synthesis.
    """
    client = get_gemini_client()
    if not client:
        return {
            "success": False,
            "escalated": False,
            "error": "gemini_unconfigured",
            "answer": None,
        }

    history_str = ""
    if conversation_history:
        history_lines = [f"User: {turn.get('user', '')}\nAssistant: {turn.get('assistant', '')}" for turn in conversation_history[-4:]]
        history_str = f"\nRecent Conversation Context:\n" + "\n".join(history_lines) + "\n"

    full_prompt = (
        f"{system_prompt}\n"
        f"{history_str}\n"
        f"STRUCTURED CAMERA EVIDENCE & TELEMETRY:\n{context or {}}\n\n"
        f"USER QUESTION: {user_prompt}\n\n"
        f"Provide a natural, fluent, concise, and 100% grounded response based STRICTLY on the camera evidence above. "
        f"Do not invent facts, and acknowledge uncertainty if evidence is absent."
    )

    for model_name in GEMINI_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
            )
            if response and hasattr(response, "text") and response.text:
                return {
                    "success": True,
                    "escalated": True,
                    "model": f"Gemini Reasoning ({model_name})",
                    "answer": response.text.strip(),
                }
        except Exception as e:
            logger.debug("Gemini reasoning with model %s failed: %s", model_name, e)

    return {
        "success": False,
        "escalated": False,
        "error": "reasoning_api_error",
        "answer": None,
    }
