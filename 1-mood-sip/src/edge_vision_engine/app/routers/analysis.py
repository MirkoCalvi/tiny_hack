import logging
from fastapi import APIRouter, HTTPException
from app.schemas import AnalyzeRequest, MoodResponse, HealthResponse, ModelsResponse
from app.config import settings
from app.services.ai_service import (
    analyze_mood_with_ai,
    validate_image_base64,
    list_all_models,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["analysis"])


@router.post("/analyze-mood", response_model=MoodResponse)
async def analyze_mood(req: AnalyzeRequest):
    try:
        # Validate that the image is decodable
        await validate_image_base64(req.image)
        data = await analyze_mood_with_ai(req.image, req.model or settings.default_model)
        # Ensure required keys
        return MoodResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("analyze_mood failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        models = await list_all_models()
        return HealthResponse(
            status="healthy", ollama_connected=bool(models), available_models=models, default_model=settings.default_model
        )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return HealthResponse(
            status="unhealthy", ollama_connected=False, error="Cannot connect to Ollama.", default_model=settings.default_model
        )


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    models = await list_all_models()
    vision_models = [
        m
        for m in models
        if (
            "vision" in m.lower()
            or "llava" in m.lower()
            or "minicpm" in m.lower()
            or "bakllava" in m.lower()
            or "gemma3" in m.lower()
            or "gemma2" in m.lower()
            or ("qwen2.5" in m.lower() and "instruct" in m.lower())
        )
    ]
    return ModelsResponse(vision_models=vision_models, all_models=models)


@router.get("/test-analysis", response_model=MoodResponse)
async def test_analysis():
    return MoodResponse(
        needs_hydration=True,
        detected_signs=["tiredness", "dark_circles"],
        confidence=0.75,
        recommendation="You look tired! Take a break and drink some water.",
    )


@router.post("/test-image")
async def test_image(req: AnalyzeRequest):
    try:
        img_bytes, size, fmt = await validate_image_base64(req.image)
        return {
            "status": "success",
            "message": f"Valid image received: {fmt} format, size {size}",
            "format": fmt,
            "size": list(size),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
