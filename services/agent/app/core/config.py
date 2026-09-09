"""Mimesis Agent Service - Core Configuration."""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_env: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # --- Google Cloud ---
    google_cloud_project: str = Field(default="", description="GCP project ID")
    google_cloud_location: str = Field(default="us-central1")

    # --- Gemini / Vertex AI ---
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = Field(default="gemini-3.1-flash")
    gemini_thinking_model: str = Field(default="gemini-2.5-pro")

    # --- Parallel Search MCP ---
    parallel_mcp_server_url: str = Field(default="https://search.parallel.ai/mcp")
    parallel_api_key: str | None = Field(default=None)

    # --- Firestore ---
    firestore_database: str = Field(default="(default)")

    # --- Google Cloud Storage ---
    gcs_media_bucket: str = Field(default="mimesis-media-assets")

    # --- Media Models ---
    imagen_model: str = Field(default="imagen-4-ultra")
    tts_model: str = Field(default="gemini-2.5-flash-preview-tts")
    lyria_model: str = Field(default="lyria-realtime")

    # --- Secret Manager ---
    secret_manager_project: str | None = Field(default=None)

    # --- Cost & Generation Controls ---
    max_parallel_queries_per_turn: int = Field(default=1)
    max_evidence_sources_per_query: int = Field(default=2)
    initial_podcast_duration: str = Field(default="a contiguous segment of 6-8 back-and-forth conversational turns")

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings singleton."""
    return Settings()
