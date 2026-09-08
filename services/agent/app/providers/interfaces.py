"""Provider interfaces for external service integrations.

These are production-grade interfaces — not mocks. Each defines the contract
that a real provider implementation must satisfy. Implementations use actual
Google Cloud SDKs and APIs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.models import (
    MediaAsset,
    MediaType,
    PodcastSession,
)


class GeminiReasoningService(ABC):
    """Interface for Gemini LLM reasoning with structured output."""

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: type,
        *,
        model: str | None = None,
        temperature: float = 1.0,
    ) -> Any:
        """Generate a structured response matching the given Pydantic schema."""
        ...

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 1.0,
        system_instruction: str | None = None,
    ) -> str:
        """Generate a free-form text response."""
        ...


class ImageGenerationService(ABC):
    """Interface for storyboard/visual asset generation (Imagen 3/4)."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "9:16",
        style: str | None = None,
    ) -> MediaAsset:
        """Generate an image from a text prompt and return a MediaAsset."""
        ...


class TextToSpeechService(ABC):
    """Interface for voiceover generation (Gemini TTS)."""

    @abstractmethod
    async def generate_speech(
        self,
        text: str,
        *,
        voice: str | None = None,
        speaking_rate: float = 1.0,
    ) -> MediaAsset:
        """Generate speech audio from text and return a MediaAsset."""
        ...


class MusicGenerationService(ABC):
    """Interface for background music generation (Lyria)."""

    @abstractmethod
    async def generate_music(
        self,
        prompt: str,
        *,
        duration_seconds: int = 30,
        mood: str | None = None,
    ) -> MediaAsset:
        """Generate music from a text prompt and return a MediaAsset."""
        ...


class StorageService(ABC):
    """Interface for blob/media asset storage (Google Cloud Storage)."""

    @abstractmethod
    async def upload_asset(
        self,
        data: bytes,
        filename: str,
        media_type: MediaType,
        *,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload a media asset and return its storage URL."""
        ...

    @abstractmethod
    async def get_asset_url(self, storage_path: str) -> str:
        """Get a signed or public URL for a stored asset."""
        ...

    @abstractmethod
    async def download_asset(self, storage_path: str) -> bytes:
        """Download an asset by its storage path."""
        ...


class SessionRepository(ABC):
    """Interface for session state persistence (Firestore)."""

    @abstractmethod
    async def create_session(self, session: PodcastSession) -> str:
        """Persist a new session state and return the session ID."""
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> PodcastSession | None:
        """Retrieve session state by ID."""
        ...

    @abstractmethod
    async def update_session(self, session: PodcastSession) -> None:
        """Update an existing session's state."""
        ...

    @abstractmethod
    async def list_sessions(self, *, limit: int = 50) -> list[PodcastSession]:
        """List recent sessions."""
        ...
