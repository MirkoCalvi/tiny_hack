from pydantic import BaseModel, Field, conlist


class AnalyzeRequest(BaseModel):
    image: str = Field(..., description="Base64-encoded image string.")
    model: str = Field(..., description="The vision model to use.")


class MoodResponse(BaseModel):
    detected_signs: conlist(str, min_length=0)
    recommendation: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    needs_hydration: bool


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    available_models: list[str] | None = None
    default_model: str
    error: str | None = None


class ModelsResponse(BaseModel):
    vision_models: list[str]
    all_models: list[str]
