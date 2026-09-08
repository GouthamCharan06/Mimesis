"""FastAPI routing for Interactive Podcast System."""

from __future__ import annotations
import asyncio
import json
import os
from typing import Any
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.core.logging import get_logger, project_id_var
from app.domain.models import AgentEvent, AgentEventType, PodcastSession, WorkflowState, ConversationTurn
from app.graph.workflow import MimesisPodcastState, create_init_workflow, create_question_workflow

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["mimesis-podcast"])

# In-memory session store for hackathon
_sessions: dict[str, PodcastSession] = {}
_session_events: dict[str, list[AgentEvent]] = {}

# Media directory for audio artifacts
MEDIA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "media"))


class SessionInitRequest(BaseModel):
    expert_id: str = "mimesis"
    topic: str = "The future of interactive podcasts"
    background_score: bool = False


class QuestionRequest(BaseModel):
    text_content: str
    turn_index: int = -1
    time_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Session Lifecycle
# ---------------------------------------------------------------------------

@router.post("/sessions")
async def init_session(req: SessionInitRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Initialize a new podcast session in the background and stream progress."""
    import uuid
    session_id = str(uuid.uuid4())
    session = PodcastSession(session_id=session_id)
    _sessions[session_id] = session
    
    background_tasks.add_task(run_podcast_generation, session_id, req)
    return {"session_id": session_id}

async def run_podcast_generation(session_id: str, req: SessionInitRequest):
    project_id_var.set(session_id)
    events_list = _session_events.setdefault(session_id, [])
    
    def emit(et: AgentEventType, details: dict | None = None):
        events_list.append(AgentEvent(event_type=et, data=details or {}))

    emit(AgentEventType.PREPARING_TOPIC)
    session = _sessions[session_id]
    
    state: MimesisPodcastState = {
        "session": session,
        "events": events_list,
        "current_input": {"expert_id": "mimesis", "topic": req.topic},
    }

    init_wf = create_init_workflow()
    emit(AgentEventType.STRUCTURING_CONVERSATION)

    if req.background_score:
        from app.agents.audio import AudioAgent
        asyncio.create_task(AudioAgent().generate_background_score(_sessions[session_id], req.topic))

    try:
        async for output in init_wf.astream(state):
            for node_name, node_state in output.items():
                if node_name == "podcast_generation":
                    emit(AgentEventType.WRITING_DIALOGUE)
                    emit(AgentEventType.GENERATING_VOICES)
                elif node_name == "tts_generation":
                    _sessions[session_id] = node_state["session"]
                    turns = [t.model_dump(mode="json") for t in node_state["session"].turns]
                    emit(AgentEventType.PODCAST_READY, {"turns": turns})
    except Exception as e:
        logger.error(f"Gen error: {e}")
        emit(AgentEventType.ERROR, {"error": str(e)})


@router.post("/sessions/{session_id}/ask")
async def ask_question(session_id: str, req: QuestionRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Submit a factual question mapped to a Narrative Checkpoint running in the background."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    background_tasks.add_task(run_ask_workflow, session_id, req)
    return {"status": "started"}

async def run_ask_workflow(session_id: str, req: QuestionRequest):
    session = _sessions.get(session_id)
    if not session: return
    project_id_var.set(session_id)
    
    events_list = _session_events.setdefault(session_id, [])
    def emit(et: AgentEventType, details: dict | None = None):
        events_list.append(AgentEvent(event_type=et, data=details or {}))
        
    emit(AgentEventType.CAPTURING_CONTEXT)
    
    state: MimesisPodcastState = {
        "session": session,
        "events": events_list,
        "current_input": {"new_question": req.text_content, "turn_index": req.turn_index, "time_seconds": req.time_seconds},
    }
    
    question_wf = create_question_workflow()
    
    try:
        async for output in question_wf.astream(state):
            for node_name, node_state in output.items():
                if node_name == "gap_evaluation":
                    emit(AgentEventType.EXECUTING_SEARCH)
                elif node_name == "parallel_research":
                    evidence = [e.model_dump(mode="json") for e in node_state["session"].active_research_plan.evidence] if node_state["session"].active_research_plan else []
                    emit(AgentEventType.COMPARING_EVIDENCE, {"evidence": evidence})
                    emit(AgentEventType.REASONING_WITH_GEMINI)
                elif node_name == "evidence_synthesis":
                    emit(AgentEventType.GENERATING_EXPERT_VOICE)
                elif node_name == "tts_generation":
                    emit(AgentEventType.RETURNING_TO_STORY)
                elif node_name == "response_playback":
                    _sessions[session_id] = node_state["session"]
                    latest_turn = None
                    for turn in reversed(node_state["session"].turns):
                        if turn.speaker != "User":
                            latest_turn = turn
                            break
                    emit(AgentEventType.COMPLETED, {"new_turn": latest_turn.model_dump(mode="json") if latest_turn else None})
    except Exception as e:
        logger.error(f"Ask error: {e}")
        emit(AgentEventType.ERROR, {"error": str(e)})


@router.post("/sessions/{session_id}/adapt")
async def adapt_episode(session_id: str, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Slice the episode exactly at the knowledge gap and rebuild the script based on AI pivot."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    background_tasks.add_task(run_adaptation, session_id)
    return {"status": "started"}

async def run_adaptation(session_id: str):
    """The Background runner that pivots the entire episode based on the consent modal payload."""
    session = _sessions.get(session_id)
    if not session or not session.active_research_plan: return
    project_id_var.set(session_id)
    
    events_list = _session_events.setdefault(session_id, [])
    def emit(et: AgentEventType, details: dict | None = None):
        events_list.append(AgentEvent(event_type=et, data=details or {}))

    # Re-use init UI states so the Frontend loading checklist renders cleanly
    emit(AgentEventType.PREPARING_TOPIC)
    
    # 1. Prune the future turns using the playhead turn_index grabbed prior to the question
    if session.current_question and session.current_question.turn_index >= 0:
         session.turns = session.turns[:session.current_question.turn_index + 1]

    # Append listener's question
    question_text = session.current_question.text_content if session.current_question else "Can you explain that deeper?"
    session.turns.append(ConversationTurn(
        speaker="User",
        text_content=question_text
    ))
    
    # 2. Modify Context
    adaptation_direction = ""
    topic_str = "The future of interactive podcasts"
    if session.podcast_context:
        payload = session.podcast_context.summary_of_previous_turns # Just a dummy to grab the dict
        # The prompt payload was stored in current_input during the eval phase in graph node
        session.podcast_context.core_topic += f" [PIVOT: Focus on fundamentals as requested by user]"
        topic_str = session.podcast_context.core_topic
    
    emit(AgentEventType.STRUCTURING_CONVERSATION)
    
    # Run the same init generation graph loop (using Gemini without parallel for now to just rebuild the episode from here)
    state: MimesisPodcastState = {
        "session": session,
        "events": events_list,
        "current_input": {"expert_id": "mimesis", "topic": topic_str},
    }

    init_wf = create_init_workflow()
    
    try:
        async for output in init_wf.astream(state):
            for node_name, node_state in output.items():
                if node_name == "podcast_generation":
                    emit(AgentEventType.WRITING_DIALOGUE)
                    emit(AgentEventType.GENERATING_VOICES)
                elif node_name == "tts_generation":
                    _sessions[session_id] = node_state["session"]
                    turns = [t.model_dump(mode="json") for t in node_state["session"].turns]
                    emit(AgentEventType.PODCAST_READY, {"turns": turns})
    except Exception as e:
        logger.error(f"Adapt error: {e}")
        emit(AgentEventType.ERROR, {"error": str(e)})


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    """Get full session state for reload safety."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump(mode="json")


@router.get("/sessions/{session_id}/events")
async def stream_events(session_id: str, request: Request) -> StreamingResponse:
    """SSE endpoint for real-time progress events."""
    events_list = _session_events.setdefault(session_id, [])

    async def event_generator():
        last_idx = 0
        while not await request.is_disconnected():
            if last_idx < len(events_list):
                for ev in events_list[last_idx:]:
                    yield f"event: {ev.event_type.value}\ndata: {json.dumps(ev.model_dump(mode='json'))}\n\n"
                last_idx = len(events_list)
            await asyncio.sleep(1)
            yield f"event: heartbeat\ndata: {json.dumps({'type': 'heartbeat'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ---------------------------------------------------------------------------
# Media Serving
# ---------------------------------------------------------------------------

@router.get("/media/{filename}")
async def serve_media(filename: str):
    """Serve generated audio files from the local media directory."""
    filepath = os.path.join(MEDIA_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Media file not found")
    return FileResponse(filepath, media_type="audio/wav")
