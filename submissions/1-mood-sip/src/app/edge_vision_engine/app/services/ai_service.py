import base64
import io
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from PIL import Image
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

try:
    import ollama
    OLLAMA_CLIENT = ollama.AsyncClient()
except Exception as e:  # pragma: no cover - optional at import time
    OLLAMA_CLIENT = None
    logger.warning(f"Ollama client not available: {e}")


_model_names_cache: list[str] | None = None


@asynccontextmanager
async def lifespan_context(app):
    logger.info("=" * 60)
    logger.info("🌊 MoodSip Backend Server (Controller/Service)")
    logger.info("=" * 60)
    logger.info(f"🤖 Default Model: {settings.default_model}")
    logger.info("🚀 Server starting up...")
    global _model_names_cache
    try:
        if OLLAMA_CLIENT is not None:
            models_response = await OLLAMA_CLIENT.list()
            _model_names_cache = [m.model for m in models_response.models]
            logger.info("✅ Connected to Ollama")
            if settings.default_model not in (_model_names_cache or []):
                logger.warning(
                    f"⚠️ Default model '{settings.default_model}' not found in Ollama"
                )
        else:
            logger.warning("⚠️ Ollama client not initialized.")
    except Exception as e:
        logger.error("❌ Cannot connect to Ollama! Ensure the Ollama server is running.")
        logger.error(f"   Error: {e}")
    yield
    logger.info("=" * 60)
    logger.info("🌙 Server shutting down.")
    logger.info("=" * 60)


async def list_all_models() -> list[str]:
    global _model_names_cache
    if OLLAMA_CLIENT is None:
        return _model_names_cache or []
    try:
        models_response = await OLLAMA_CLIENT.list()
        return [m.model for m in models_response.models]
    except Exception:
        return _model_names_cache or []


async def analyze_mood_with_ai(image_base64: str, model: str):
    """Core analysis logic that can use Ollama or Google GenAI depending on model."""
    system_prompt = """
You are a specialized AI assistant for facial expression analysis, focusing on detecting visible signs that may indicate dehydration or fatigue. Your role is to provide objective observations based on facial features visible in the image.

ANALYSIS CRITERIA:
Evaluate the following indicators:
1. Dry or Chapped Lips - visible cracking, peeling, or lack of moisture
2. Sunken Eyes - hollowed appearance around the eye sockets
3. Dark Circles - pronounced discoloration under the eyes
4. Tiredness - drooping eyelids, unfocused gaze, or general facial fatigue
5. Pale or Dull Skin - lack of healthy color or vitality in facial complexion

ASSESSMENT GUIDELINES:
- Be conservative and evidence-based in your analysis
- Only flag signs that are clearly visible and pronounced
- Consider that lighting, makeup, or natural features may affect appearance
- Require at least 2 distinct signs before recommending hydration
- Assign confidence based on clarity and number of indicators present

CONFIDENCE SCORING:
- 0.8-1.0: Multiple clear, pronounced signs present
- 0.6-0.79: 2-3 moderate signs visible
- 0.4-0.59: 1-2 mild signs detected
- 0.0-0.39: No significant signs or unclear image

OUTPUT REQUIREMENTS:
Respond ONLY with valid JSON in this exact format and in the following order (no additional text):
{
    "detected_signs": ["sign1", "sign2"],
    "recommendation": "string",
    "confidence": float,
    "needs_hydration": boolean

}

RULES:
- Set "needs_hydration" to true only if 2+ signs are detected OR 1 severe sign
- List only the signs you actually observe in "detected_signs"
- Keep "recommendation" brief (1-2 sentences max)
- Use natural, supportive language in recommendations
- If no signs detected: "You look well-hydrated! Keep up the good habits."
- If signs detected: Suggest hydration and rest without being alarmist

IMPORTANT: This is an assistive tool, not medical advice. Recommendations should be framed as general wellness suggestions.
"""

    user_prompt = (
        "Analyze this person's facial expression for signs of dehydration, tiredness, or sadness. Respond with JSON only."
    )

    try:
        image_bytes = base64.b64decode(image_base64)

        # If using a Google Gemini model
        if model.startswith("gemini"):
            if not settings.google_api_key:
                raise HTTPException(
                    status_code=503,
                    detail="Google GenAI not available. Set GOOGLE_API_KEY in env.",
                )
            try:
                # Lazy import to keep dependency optional
                from google import genai  # type: ignore
                from google.genai import types  # type: ignore
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"Google GenAI import failed: {e}")

            client = genai.Client(api_key=settings.google_api_key)
            json_prompt = f"""{system_prompt}

{user_prompt}

IMPORTANT: You must respond with ONLY valid JSON. No explanations, no markdown, no additional text. Just the JSON object."""

            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    types.Part.from_text(text=json_prompt),
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                ],
            )

            response_content: str = response.text or "{}"
            if not response_content.strip().startswith("{"):
                # Try to salvage JSON from the response
                import re

                m = re.search(r"\{.*\}", response_content, re.DOTALL)
                response_content = m.group() if m else '{"needs_hydration": true, "detected_signs": ["Unable to analyze"], "confidence": 0.5, "recommendation": "Please try again"}'

        else:
            if OLLAMA_CLIENT is None:
                raise HTTPException(status_code=503, detail="Ollama client not available")
            response = await OLLAMA_CLIENT.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt, "images": [image_bytes]},
                ],
                format="json",
                options={"temperature": 0.2},
            )
            response_content = response["message"]["content"]

        # Common JSON parse
        data = json.loads(response_content)
        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(e))


async def validate_image_base64(image_b64_or_data_url: str) -> tuple[bytes, tuple[int, int], str]:
    """Validate base64 image (data URL or pure base64). Returns (raw_bytes, size, format)."""
    img_b64 = image_b64_or_data_url
    if img_b64.startswith("data:image"):
        img_b64 = img_b64.split(",", 1)[1]
    img_data = base64.b64decode(img_b64)
    img = Image.open(io.BytesIO(img_data))
    img.verify()
    # Reopen to read size/format (verify() leaves file closed)
    img2 = Image.open(io.BytesIO(img_data))
    return img_data, img2.size, img2.format or ""
