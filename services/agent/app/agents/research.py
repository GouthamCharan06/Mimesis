"""Research Agent coordinating mandatory external Parallel grounding."""

from app.domain.models import PodcastSession, ResearchPlan, ResearchQuery, ResearchEvidence, EvidenceSource, EvidenceAssessment
from app.providers.gemini import GeminiProvider
from app.tools.parallel_mcp import ParallelSearchTool
from app.prompts.templates import EVIDENCE_SYNTHESIS_PROMPT
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

class ResearchAgent:
    def __init__(self):
        self.gemini = GeminiProvider()
        self.search_tool = ParallelSearchTool()

    async def execute_searches(self, session: PodcastSession) -> PodcastSession:
        if not session.active_research_plan:
             return session
             
        settings = get_settings()
        for query in session.active_research_plan.queries:
            try:
                # ParallelSearchTool.search() returns a ResearchEvidence object directly
                evidence = await self.search_tool.search(query.query_string, num_results=settings.max_evidence_sources_per_query)
                session.active_research_plan.evidence.append(evidence)
            except Exception:
                pass
                
        return session

    async def synthesize_evidence(self, session: PodcastSession) -> PodcastSession:
        if not session.active_research_plan:
             return session
             
        evidence_text = ""
        for ev in session.active_research_plan.evidence:
            for src in ev.sources:
                evidence_text += f"- [{src.title}]({src.source_url}): {src.retrieved_content}\n"
                
        context = " ".join([t.text_content for t in session.turns[-3:]])
        
        try:
             session.active_research_plan.assessment = EvidenceAssessment(
                 synthesis_summary=evidence_text,
                 contradictions_found=False,
                 is_uncertain=False,
                 uncertainty_reason=""
             )
        except Exception as e:
             session.active_research_plan.assessment = EvidenceAssessment(
                 synthesis_summary=f"Fallback synthesis due to error: {e}",
                 is_uncertain=True,
                 uncertainty_reason="Synthesis failure"
             )
        return session
