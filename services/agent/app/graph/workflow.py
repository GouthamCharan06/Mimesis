"""LangGraph state machine for Mimesis Interactive Podcast.

Two separate compiled graphs:
  - init_workflow: PODCAST_INITIALIZATION → EXPERT_READY → PODCAST_GENERATION → END
  - question_workflow: QUESTION_RECEIVED → RESEARCH_PLANNING → PARALLEL_RESEARCH
      → EVIDENCE_SYNTHESIS → EXPERT_RESPONSE_GENERATION → TTS_GENERATION
      → RESPONSE_PLAYBACK → END

Session state (PodcastSession) carries all context between invocations.
The mandatory Parallel research path is enforced: there is NO edge from
QUESTION_RECEIVED to EXPERT_RESPONSE_GENERATION that bypasses research.
"""

from __future__ import annotations
from typing import Any, TypedDict
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.core.logging import get_logger
from app.domain.models import AgentEvent, AgentEventType, PodcastSession, WorkflowState

logger = get_logger(__name__)


class MimesisPodcastState(TypedDict):
    """LangGraph state schema wrapping the durable PodcastSession."""
    session: PodcastSession
    events: list[AgentEvent]
    current_input: dict[str, Any]


# ---------------------------------------------------------------------------
# Agent Nodes
# ---------------------------------------------------------------------------

async def podcast_initialization_node(state: MimesisPodcastState) -> dict:
    from app.agents.orchestrator import OrchestratorAgent
    state["events"].append(AgentEvent(
        event_type=AgentEventType.INITIALIZING_PODCAST,
        message="Initializing Expert Profile and starting podcast session"
    ))
    agent = OrchestratorAgent()
    session = await agent.initialize_session(state["session"], state["current_input"])
    session.transition_to(WorkflowState.EXPERT_READY)
    return {"session": session, "events": state["events"], "current_input": {}}


async def podcast_generation_node(state: MimesisPodcastState) -> dict:
    """Uses Gemini to start the baseline podcast."""
    from app.agents.orchestrator import OrchestratorAgent
    state["events"].append(AgentEvent(
        event_type=AgentEventType.GENERATING_PODCAST,
        message="Generating initial podcast script with Gemini"
    ))
    agent = OrchestratorAgent()
    session = await agent.generate_initial_podcast(state["session"])
    session.transition_to(WorkflowState.CONVERSATION_ACTIVE)
    return {"session": session, "events": state["events"]}


async def question_received_node(state: MimesisPodcastState) -> dict:
    from app.domain.models import UserQuestion

    question_text = state["current_input"].get("new_question", "")
    turn_index = state["current_input"].get("turn_index", -1)
    time_seconds = state["current_input"].get("time_seconds", 0.0)
    
    state["session"].current_question = UserQuestion(
        text_content=question_text, 
        turn_index=turn_index, 
        time_seconds=time_seconds
    )
    state["session"].transition_to(WorkflowState.QUESTION_RECEIVED)

    state["events"].append(AgentEvent(
        event_type=AgentEventType.QUESTION_RECEIVED,
        message=f"Received: {question_text}",
        data={"text": question_text}
    ))

    return {"session": state["session"], "events": state["events"], "current_input": state["current_input"]}


async def gap_evaluation_node(state: MimesisPodcastState) -> dict:
    from app.agents.evaluator import GapEvaluatorAgent
    state["events"].append(AgentEvent(event_type=AgentEventType.EVALUATING_GAPS, message="Evaluating question for fundamental comprehension gaps..."))
    
    agent = GapEvaluatorAgent()
    eval_result = await agent.evaluate_question(state["session"])
    
    if eval_result.get("is_fundamental_gap", False):
        state["events"].append(AgentEvent(
            event_type=AgentEventType.ADAPTATION_PROPOSED,
            message="Knowledge gap detected. Requesting pivot consent.",
            data=eval_result
        ))
        
        # We explicitly halt transition here and flag the session payload with the adaptation block
        state["session"].transition_to(WorkflowState.ADAPTATION_PROPOSED)
        state["current_input"]["adaptation_payload"] = eval_result
        return {"session": state["session"], "events": state["events"]}
        
    from app.domain.models import ResearchPlan, ResearchQuery
    from app.core.config import get_settings
    settings = get_settings()
    
    queries = [ResearchQuery(query_string=q["query_string"], intent=q["intent"]) for q in eval_result.get("queries", [])][:settings.max_parallel_queries_per_turn]
    
    current_q = state["session"].current_question
    fallback_text = current_q.text_content if current_q else "General inquiry"
    q_id = current_q.question_id if current_q else "guest_q"
    
    if not queries:
        queries = [ResearchQuery(query_string=fallback_text, intent="fallback")]
        
    state["session"].active_research_plan = ResearchPlan(
        original_question_id=q_id,
        queries=queries
    )
    state["events"].append(AgentEvent(event_type=AgentEventType.PLANNING_RESEARCH, message="Planning research strategy..."))
    state["session"].transition_to(WorkflowState.RESEARCH_PLANNING)
    return {"session": state["session"], "events": state["events"]}


async def parallel_research_node(state: MimesisPodcastState) -> dict:
    from app.agents.research import ResearchAgent
    state["events"].append(AgentEvent(event_type=AgentEventType.EXECUTING_SEARCH, message="Executing Parallel MCP Search queries..."))
    agent = ResearchAgent()
    session = await agent.execute_searches(state["session"])
    session.transition_to(WorkflowState.PARALLEL_RESEARCH)
    return {"session": session, "events": state["events"]}


async def evidence_synthesis_node(state: MimesisPodcastState) -> dict:
    from app.agents.research import ResearchAgent
    state["events"].append(AgentEvent(event_type=AgentEventType.SYNTHESIZING_EVIDENCE, message="Synthesizing context and retrieved evidence..."))
    agent = ResearchAgent()
    session = await agent.synthesize_evidence(state["session"])
    session.transition_to(WorkflowState.EVIDENCE_SYNTHESIS)
    return {"session": session, "events": state["events"]}


async def expert_response_generation_node(state: MimesisPodcastState) -> dict:
    from app.agents.persona import ExpertPersonaAgent
    state["events"].append(AgentEvent(event_type=AgentEventType.GENERATING_RESPONSE, message="Generating expert response..."))
    agent = ExpertPersonaAgent()
    session = await agent.generate_response(state["session"])
    session.transition_to(WorkflowState.EXPERT_RESPONSE_GENERATION)
    return {"session": session, "events": state["events"]}


async def tts_generation_node(state: MimesisPodcastState) -> dict:
    from app.agents.audio import AudioAgent
    state["events"].append(AgentEvent(event_type=AgentEventType.GENERATING_TTS, message="Synthesizing Expert Audio..."))
    agent = AudioAgent()
    session = await agent.generate_tts(state["session"])
    session.transition_to(WorkflowState.TTS_GENERATION)
    return {"session": session, "events": state["events"]}


async def response_playback_node(state: MimesisPodcastState) -> dict:
    state["events"].append(AgentEvent(
        event_type=AgentEventType.CONVERSATION_ACTIVE,
        message="Response delivered. Ready for next question."
    ))
    state["session"].transition_to(WorkflowState.RESPONSE_PLAYBACK)
    return {"session": state["session"], "events": state["events"]}


# ---------------------------------------------------------------------------
# Graph Builders
# ---------------------------------------------------------------------------

def build_init_graph() -> StateGraph:
    """Graph for session initialization + initial podcast generation."""
    graph = StateGraph(MimesisPodcastState)

    graph.add_node("podcast_initialization", podcast_initialization_node)
    graph.add_node("podcast_generation", podcast_generation_node)
    graph.add_node("tts_generation", tts_generation_node)

    graph.set_entry_point("podcast_initialization")
    graph.add_edge("podcast_initialization", "podcast_generation")
    graph.add_edge("podcast_generation", "tts_generation")
    graph.add_edge("tts_generation", END)

    return graph


def build_question_graph() -> StateGraph:
    """Graph for handling a user question with mandatory Parallel research.
    
    CRITICAL: There is NO edge that bypasses research_planning → parallel_research.
    Every question MUST go through the full grounding pipeline.
    """
    graph = StateGraph(MimesisPodcastState)

    graph.add_node("question_received", question_received_node)
    graph.add_node("gap_evaluation", gap_evaluation_node)
    # graph.add_node("research_planning", research_planning_node)
    graph.add_node("parallel_research", parallel_research_node)
    graph.add_node("evidence_synthesis", evidence_synthesis_node)
    graph.add_node("expert_response_generation", expert_response_generation_node)
    graph.add_node("tts_generation", tts_generation_node)
    graph.add_node("response_playback", response_playback_node)

    def route_adaptation(state: MimesisPodcastState):
        if state["session"].workflow_state == WorkflowState.ADAPTATION_PROPOSED:
            return "end"
        return "continue"

    graph.set_entry_point("question_received")
    graph.add_edge("question_received", "gap_evaluation")
    graph.add_conditional_edges(
        "gap_evaluation",
        route_adaptation,
        {
            "end": END,
            "continue": "parallel_research"
        }
    )
    graph.add_edge("parallel_research", "evidence_synthesis")
    graph.add_edge("evidence_synthesis", "expert_response_generation")
    graph.add_edge("expert_response_generation", "tts_generation")
    graph.add_edge("tts_generation", "response_playback")
    graph.add_edge("response_playback", END)

    return graph


def create_init_workflow():
    """Create the compiled init workflow."""
    return build_init_graph().compile()


def create_question_workflow():
    """Create the compiled question-handling workflow."""
    return build_question_graph().compile()


# Legacy compatibility
def create_workflow():
    """Legacy: returns the init workflow. Use create_init_workflow/create_question_workflow instead."""
    return create_init_workflow()
