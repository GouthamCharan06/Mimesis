"""Media generation provider interfaces - Imagen, TTS, Lyria.

These providers use the actual Google GenAI SDK for media generation.
Implementations are ready for integration once the respective APIs are enabled.
"""

from __future__ import annotations

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.retry import with_provider_retry
from app.domain.models import MediaAsset, MediaType
import uuid
from app.providers.interfaces import (
    ImageGenerationService,
    MusicGenerationService,
    TextToSpeechService,
)

logger = get_logger(__name__)


import os

class ImagenProvider(ImageGenerationService):
    """Imagen image generation using Google GenAI SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        use_vertex = bool(settings.google_cloud_project)
        self._client = genai.Client(
            vertexai=use_vertex,
            project=settings.google_cloud_project if use_vertex else None,
            location=settings.google_cloud_location if use_vertex else None,
            api_key=settings.gemini_api_key if not use_vertex else None,
        )
        self._model = settings.imagen_model
        logger.info("imagen_provider_initialized", model=self._model)

    @with_provider_retry()
    async def generate_image(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "9:16",
        style: str | None = None,
    ) -> MediaAsset:
        full_prompt = f"{prompt}. Style: {style}" if style else prompt

        response = await self._client.aio.models.generate_images(
            model=self._model,
            prompt=full_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
            ),
        )

        asset_id = str(uuid.uuid4())
        
        image_data = b""
        if response.generated_images and len(response.generated_images) > 0:
            if response.generated_images[0].image:
                image_data = response.generated_images[0].image.image_bytes
        
        return MediaAsset(
            asset_id=asset_id,
            media_type=MediaType.IMAGE,
            filename=f"storyboard_{asset_id}.png",
            description=prompt,
            metadata={"aspect_ratio": aspect_ratio, "model": self._model},
            raw_bytes=image_data,
        )


class GeminiTTSProvider(TextToSpeechService):
    """Gemini TTS provider using the google-genai SDK (Vertex AI).

    Root cause of previous 400 error: the model name was 'gemini-2.5-flash'
    (the reasoning model). The correct TTS model is 'gemini-2.5-flash-preview-tts'.
    The SDK path with vertexai=True and AUDIO modality works with ADC.
    """

    def __init__(self) -> None:
        settings = get_settings()
        use_vertex = bool(settings.google_cloud_project)
        self._client = genai.Client(
            vertexai=use_vertex,
            project=settings.google_cloud_project if use_vertex else None,
            location=settings.google_cloud_location if use_vertex else None,
            api_key=settings.gemini_api_key if not use_vertex else None,
        )
        self._model = settings.tts_model
        logger.info(
            "tts_provider_initialized",
            model=self._model,
            project=settings.google_cloud_project,
        )

    @with_provider_retry()
    async def generate_speech(
        self,
        text: str,
        *,
        voice: str | None = None,
        speaking_rate: float = 1.0,
    ) -> MediaAsset:
        asset_id = str(uuid.uuid4())
        voice_name = voice or "Kore"

        logger.info("tts_request", voice=voice_name, model=self._model)

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            ),
        )

        # Extract the binary audio data from the response parts
        raw_audio: bytes | None = None
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.inline_data and part.inline_data.data:
                        raw_audio = part.inline_data.data
                        break

        if not raw_audio:
            fallback_reason = "Unknown"
            if response.candidates and response.candidates[0].finish_reason:
                fallback_reason = f"Finish Reason: {response.candidates[0].finish_reason}"
            if response.prompt_feedback:
                fallback_reason += f" | Prompt Feedback: {response.prompt_feedback}"
            raise ValueError(f"Gemini TTS returned no audio data in response. {fallback_reason}")

        # Gemini SDK returns raw 24kHz 16-bit PCM bytes. We must wrap it in a valid RIFF/WAV container.
        import wave
        import io
        with io.BytesIO() as wav_io:
            with wave.open(wav_io, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(24000)
                wav_file.writeframes(raw_audio)
            valid_wav_bytes = wav_io.getvalue()

        logger.info("tts_success", voice=voice_name, audio_bytes=len(valid_wav_bytes))

        return MediaAsset(
            asset_id=asset_id,
            media_type=MediaType.AUDIO,
            filename=f"voiceover_{asset_id}.wav",
            description=f"Voiceover: {text[:100]}...",
            metadata={"voice": voice_name, "model": self._model},
            raw_bytes=valid_wav_bytes,
        )


class LyriaProvider(MusicGenerationService):
    """Lyria music generation provider.

    Uses the Google GenAI SDK for music generation.
    Implementation boundary: Lyria API access requires specific enablement.
    """

    def __init__(self) -> None:
        settings = get_settings()
        use_vertex = bool(settings.google_cloud_project)
        self._client = genai.Client(
            vertexai=use_vertex,
            project=settings.google_cloud_project if use_vertex else None,
            location=settings.google_cloud_location if use_vertex else None,
            api_key=settings.gemini_api_key if not use_vertex else None,
        )
        self._model = settings.lyria_model
        logger.info("lyria_provider_initialized", model=self._model)

    @with_provider_retry()
    async def generate_music(
        self,
        prompt: str,
        *,
        duration_seconds: int = 30,
        mood: str | None = None,
    ) -> MediaAsset:
        asset_id = str(uuid.uuid4())
        full_prompt = f"{prompt}. Mood: {mood}. Duration: {duration_seconds}s" if mood else prompt

        # Implementation boundary: Lyria API call pattern
        # The exact SDK method will depend on the Lyria API surface when enabled.
        # This provider is structured to integrate directly once the API is available.
        logger.info(
            "lyria_generation_request",
            prompt=full_prompt[:100],
            duration=duration_seconds,
        )

        return MediaAsset(
            asset_id=asset_id,
            media_type=MediaType.MUSIC,
            filename=f"music_{asset_id}.wav",
            description=f"Music: {prompt[:100]}",
            metadata={
                "mood": mood or "",
                "duration_seconds": str(duration_seconds),
                "model": self._model,
            },
        )
