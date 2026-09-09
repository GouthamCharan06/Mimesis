"""Pydantic v2 domain models for Mimesis Interactive Podcast System."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowState(str, Enum):
    """Explicit states for the durable LangGraph state machine."""
    PODCAST_INITIALIZATION = "PODCAST_INITIALIZATION"
    EXPERT_READY = "EXPERT_READY"
    PODCAST_GENERATION = "PODCAST_GENERATION"
    CONVERSATION_ACTIVE = "CONVERSATION_ACTIVE"
    QUESTION_RECEIVED = "QUESTION_RECEIVED"
    GAP_EVALUATION = "GAP_EVALUATION"
    ADAPTATION_PROPOSED = "ADAPTATION_PROPOSED"
    RESEARCH_PLANNING = "RESEARCH_PLANNING"
    PARALLEL_RESEARCH = "PARALLEL_RESEARCH"
    EVIDENCE_SYNTHESIS = "EVIDENCE_SYNTHESIS"
    EXPERT_RESPONSE_GENERATION = "EXPERT_RESPONSE_GENERATION"
    TTS_GENERATION = "TTS_GENERATION"
    RESPONSE_PLAYBACK = "RESPONSE_PLAYBACK"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Core Domain Models
# ---------------------------------------------------------------------------

class ExpertProfile(BaseModel):
    expert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    domain: str
    background: str
    experience: str
    communication_style: str
    conversational_personality: str
    perspective: str
    expertise_boundaries: list[str] = Field(default_factory=list)


class ConversationTurn(BaseModel):
    turn_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    speaker: str = Field(description="'Host', 'Expert', or 'User'")
    timestamp: datetime = Field(default_factory=utc_now)
    text_content: str
    audio_path: str | None = None
    research_evidence_ids: list[str] = Field(default_factory=list)
    is_interruption: bool = False


class UserQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=utc_now)
    text_content: str
    turn_index: int = -1
    time_seconds: float = 0.0


class PodcastContext(BaseModel):
    context_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    core_topic: str
    summary_of_previous_turns: str = ""
    active_expert_id: str
    recent_turns: list[ConversationTurn] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Mandatory Research Layer
# ---------------------------------------------------------------------------

class ResearchQuery(BaseModel):
    query_string: str
    intent: str


class EvidenceSource(BaseModel):
    source_url: str
    title: str
    retrieved_content: str
    relevance_score: float = 0.0


class ResearchEvidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    sources: list[EvidenceSource] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class EvidenceAssessment(BaseModel):
    synthesis_summary: str
    contradictions_found: bool = False
    is_uncertain: bool = False
    uncertainty_reason: str | None = None


class ResearchPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_question_id: str
    queries: list[ResearchQuery] = Field(default_factory=list)
    evidence: list[ResearchEvidence] = Field(default_factory=list)
    assessment: EvidenceAssessment | None = None


# ---------------------------------------------------------------------------
# Output & Assembly
# ---------------------------------------------------------------------------

class MediaType(str, Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MUSIC = "music"
    SUBTITLE = "subtitle"


class MediaAsset(BaseModel):
    asset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    media_type: MediaType
    filename: str
    description: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)
    raw_bytes: bytes | None = Field(default=None, exclude=True)


class ExpertResponse(BaseModel):
    response_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    draft_text: str
    based_on_evidence_ids: list[str] = Field(default_factory=list)
    final_text: str


class AudioResponse(BaseModel):
    audio_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    response_id: str
    duration_seconds: float = 0.0
    storage_path: str


class SessionRecording(BaseModel):
    recording_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total_duration_seconds: float = 0.0
    storage_path: str
    compiled_at: datetime = Field(default_factory=utc_now)


class PublishingJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recording_id: str
    platform: str
    status: str = "pending"
    published_url: str | None = None


# ---------------------------------------------------------------------------
# Graph State & Events
# ---------------------------------------------------------------------------

class PodcastSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_state: WorkflowState = WorkflowState.PODCAST_INITIALIZATION
    expert_profile: ExpertProfile | None = None
    podcast_context: PodcastContext | None = None
    turns: list[ConversationTurn] = Field(default_factory=list)
    
    current_question: UserQuestion | None = None
    active_research_plan: ResearchPlan | None = None
    active_expert_response: ExpertResponse | None = None
    
    background_music_path: str | None = None
    final_recording: SessionRecording | None = None
    publishing_job: PublishingJob | None = None
    
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def transition_to(self, new_state: WorkflowState) -> None:
        self.workflow_state = new_state
        self.updated_at = utc_now()


class AgentEventType(str, Enum):
    INITIALIZING_PODCAST = "initializing_podcast"
    EXPERT_READY = "expert_ready"
    GENERATING_PODCAST = "generating_podcast"
    QUESTION_RECEIVED = "question_received"
    PLANNING_RESEARCH = "planning_research"
    EXECUTING_SEARCH = "executing_search"
    SYNTHESIZING_EVIDENCE = "synthesizing_evidence"
    GENERATING_RESPONSE = "generating_response"
    GENERATING_TTS = "generating_tts"
    CONVERSATION_ACTIVE = "conversation_active"
    WORKFLOW_STATE_CHANGED = "workflow_state_changed"
    ERROR = "error"
    COMPLETED = "completed"
    
    # New Progress Events
    PREPARING_TOPIC = "preparing_topic"
    STRUCTURING_CONVERSATION = "structuring_conversation"
    WRITING_DIALOGUE = "writing_dialogue"
    GENERATING_VOICES = "generating_voices"
    PODCAST_READY = "podcast_ready"
    CAPTURING_CONTEXT = "capturing_context"
    EVALUATING_GAPS = "evaluating_gaps"
    ADAPTATION_PROPOSED = "adaptation_proposed"
    COMPARING_EVIDENCE = "comparing_evidence"
    REASONING_WITH_GEMINI = "reasoning_with_gemini"
    GENERATING_EXPERT_VOICE = "generating_expert_voice"
    RETURNING_TO_STORY = "returning_to_story"


class AgentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AgentEventType
    agent_name: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
