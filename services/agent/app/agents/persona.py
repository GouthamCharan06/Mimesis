"""Agent for drafting the Expert Conversation Response."""

from app.domain.models import PodcastSession, ExpertResponse, ConversationTurn
from app.providers.gemini import GeminiProvider
from app.prompts.templates import EXPERT_PERSONA_PROMPT
import json

def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return raw.strip()

class ExpertPersonaAgent:
    def __init__(self):
        self.gemini = GeminiProvider()

    async def generate_response(self, session: PodcastSession) -> PodcastSession:
        if not session.expert_profile or not session.current_question or not session.active_research_plan or not session.active_research_plan.assessment:
             return session # Cannot generate without complete grounding and context!

        recent_context = " ".join([turn.text_content for turn in session.turns[-3:]])
        prompt = EXPERT_PERSONA_PROMPT.format(
            name=session.expert_profile.name,
            communication_style=session.expert_profile.communication_style,
            perspective=session.expert_profile.perspective,
            recent_context=recent_context,
            user_question=session.current_question.text_content,
            synthesis_summary=session.active_research_plan.assessment.synthesis_summary,
            is_uncertain=session.active_research_plan.assessment.is_uncertain,
            turn_index=session.current_question.turn_index,
            time_seconds=session.current_question.time_seconds
        )
        
        try:
            res = await self.gemini.generate_text(prompt=prompt)
            data = json.loads(_clean_json(res))
            
            resp = ExpertResponse(
                draft_text=data.get("draft_text", ""),
                final_text=data.get("final_text", ""),
                based_on_evidence_ids=[e.evidence_id for e in session.active_research_plan.evidence]
            )
            session.active_expert_response = resp
            
            # Append interaction to turns history
            session.turns.append(ConversationTurn(
                speaker="User",
                text_content=session.current_question.text_content,
                is_interruption=True
            ))
            
            session.turns.append(ConversationTurn(
                speaker=session.expert_profile.name,
                text_content=resp.final_text,
                research_evidence_ids=resp.based_on_evidence_ids,
                is_interruption=True
            ))
            
        except Exception as e:
            session.error_message = f"Persona drafted failed: {e}"
            
        return session
