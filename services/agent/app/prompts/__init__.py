"""Prompts module - centralized system instructions and prompt templates."""

from app.prompts.templates import (
    INITIAL_PODCAST_GENERATION,
    COMBINED_ROUTING_PROMPT,
    EVIDENCE_SYNTHESIS_PROMPT,
    EXPERT_PERSONA_PROMPT,
)

__all__ = [
    "INITIAL_PODCAST_GENERATION",
    "COMBINED_ROUTING_PROMPT",
    "EVIDENCE_SYNTHESIS_PROMPT",
    "EXPERT_PERSONA_PROMPT",
]
