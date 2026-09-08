"""Orchestrator Agent for Podcast Initialization and Context generation."""

from app.domain.models import PodcastSession, ExpertProfile, PodcastContext, ConversationTurn
from app.providers.gemini import GeminiProvider
from app.prompts.templates import INITIAL_PODCAST_GENERATION
from app.core.config import get_settings
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

class OrchestratorAgent:
    def __init__(self):
        self.gemini = GeminiProvider()

    async def initialize_session(self, session: PodcastSession, input_data: dict) -> PodcastSession:
        expert_id = input_data.get("expert_id", "mimesis")
        topic = input_data.get("topic", "The future of interactive podcasts")
        
        # Unbounded Dynamic Persona Generation
        prompt = f"""
        You are configuring the absolute perfect Subject Matter Expert for a podcast about: "{topic}"
        
        Your response must exactly match this strict JSON structure:
        {{
            "name": "Mimesis",
            "domain": "<a short 2-3 word title of their academic or professional domain, e.g. 'Evolutionary Biologist' or 'Tech Historian'>",
            "background": "<a single sentence describing their impressive relevant background>",
            "experience": "<a single short sentence describing their tenure>",
            "communication_style": "<how do they talk? e.g. 'Highly academic but patient with beginners'>",
            "conversational_personality": "<how do they feel? e.g. 'Deeply philosophical'>",
            "perspective": "<their core worldview regarding this topic in 1 sentence>"
        }}
        """
        
        try:
             res = await self.gemini.generate_text(prompt=prompt)
             data = json.loads(_clean_json(res))
             
             session.expert_profile = ExpertProfile(
                 expert_id=expert_id,
                 name="Mimesis",
                 domain=data.get("domain", "General Analyst"),
                 background=data.get("background", "Independent Researcher"),
                 experience=data.get("experience", "Years of study in the field"),
                 communication_style=data.get("communication_style", "Clear and engaging"),
                 conversational_personality=data.get("conversational_personality", "Curious and thoughtful"),
                 perspective=data.get("perspective", "Every topic has multiple layers."),
                 expertise_boundaries=["Medical advice", "Financial investing"]
             )
        except Exception as e:
             # Graceful fallback on network/parsing error
             session.expert_profile = ExpertProfile(
                 expert_id=expert_id,
                 name="Mimesis",
                 domain="Systems Architecture",
                 background="Software and Systems Integrator",
                 experience="10 years building distributed applications",
                 communication_style="Direct and technical",
                 conversational_personality="Enthusiastic about clean architecture",
                 perspective="Good design survives scaling.",
                 expertise_boundaries=["Medical advice", "Financial investing"]
             )
        
        session.podcast_context = PodcastContext(
            active_expert_id=expert_id,
            core_topic=topic
        )
        
        return session

    async def generate_initial_podcast(self, session: PodcastSession) -> PodcastSession:
        settings = get_settings()
        if not session.expert_profile or not session.podcast_context:
            return session
        
        prompt = INITIAL_PODCAST_GENERATION.format(
            domain=session.expert_profile.domain,
            name=session.expert_profile.name,
            background=session.expert_profile.background,
            communication_style=session.expert_profile.communication_style,
            perspective=session.expert_profile.perspective,
            topic=session.podcast_context.core_topic,
            initial_podcast_duration=settings.initial_podcast_duration
        )
        
        try:
            res = await self.gemini.generate_text(prompt=prompt)
            data = json.loads(_clean_json(res))
            
            for turn in data:
                session.turns.append(ConversationTurn(
                    speaker=turn["speaker"],
                    text_content=turn["text_content"]
                ))
        except Exception as e:
            session.error_message = f"Failed to generate initial podcast: {e}"
            
        return session
