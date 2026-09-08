"""Agent for evaluating User Questions for fundamental knowledge gaps."""

from app.domain.models import PodcastSession
from app.providers.gemini import GeminiProvider
from app.prompts.templates import COMBINED_ROUTING_PROMPT
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

class GapEvaluatorAgent:
    def __init__(self):
        self.gemini = GeminiProvider()

    async def evaluate_question(self, session: PodcastSession) -> dict:
        """Determines if the question requires a script pivot."""
        if not session.podcast_context or not session.current_question:
             return {"is_fundamental_gap": False}
             
        recent_context = " ".join([turn.text_content for turn in session.turns[-3:]])
        prompt = COMBINED_ROUTING_PROMPT.format(
            topic=session.podcast_context.core_topic,
            recent_context=recent_context,
            user_question=session.current_question.text_content
        )
        
        try:
            res = await self.gemini.generate_text(prompt=prompt)
            data = json.loads(_clean_json(res))
            return data
        except Exception as e:
            # On failure, safely fallback to basic Q&A
            return {"is_fundamental_gap": False}
