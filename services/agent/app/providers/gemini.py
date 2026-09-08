"""Gemini reasoning provider using Google GenAI SDK with structured output."""

from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.retry import with_provider_retry
from app.providers.interfaces import GeminiReasoningService

logger = get_logger(__name__)


import os

class GeminiProvider(GeminiReasoningService):
    """Production Gemini reasoning provider using google-genai SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        # Enforce Vertex AI routing. Ignore standalone Developer API key because it throws API_KEY_SERVICE_BLOCKED
        use_vertex = bool(settings.google_cloud_project)
        self._client = genai.Client(
            vertexai=use_vertex,
            project=settings.google_cloud_project if use_vertex else None,
            location=settings.google_cloud_location if use_vertex else None,
            api_key=settings.gemini_api_key if not use_vertex else None,
        )
        self._default_model = settings.gemini_model
        self._thinking_model = settings.gemini_thinking_model
        logger.info(
            "gemini_provider_initialized",
            model=self._default_model,
            project=settings.google_cloud_project,
        )

    @with_provider_retry()
    async def generate_structured(
        self,
        prompt: str,
        response_schema: type,
        *,
        model: str | None = None,
        temperature: float = 1.0,
    ) -> Any:
        """Generate a structured Gemini response enforcing a Pydantic schema."""
        model_id = model or self._default_model
        logger.info("gemini_structured_request", model=model_id, schema=response_schema.__name__)

        response = await self._client.aio.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=temperature,
            ),
        )

        if not response.text:
            raise ValueError("Gemini returned empty response")

        parsed = json.loads(response.text)
        logger.info("gemini_structured_response", model=model_id, keys=list(parsed.keys()) if isinstance(parsed, dict) else len(parsed))
        return parsed

    @with_provider_retry()
    async def generate_text(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 1.0,
        system_instruction: str | None = None,
    ) -> str:
        """Generate a free-form text response from Gemini."""
        model_id = model or self._default_model
        logger.info("gemini_text_request", model=model_id)

        config = types.GenerateContentConfig(temperature=temperature)
        if system_instruction:
            config.system_instruction = system_instruction

        response = await self._client.aio.models.generate_content(
            model=model_id,
            contents=prompt,
            config=config,
        )

        result = response.text or ""
        logger.info("gemini_text_response", model=model_id, length=len(result))
        return result
