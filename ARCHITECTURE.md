# Mimesis Architecture

Mimesis is an agentic interactive podcast platform. The podcast is not a static audio file, but an ongoing audio conversation between an AI host and a fictional AI expert persona. The listener can actively enter the conversation, ask questions, challenge claims, and explore the topic further.

## Core Architectural Principle: Mandatory External Grounding

Every user-originated question is a **mandatory research event**. The system is built around a "Three-Layer Architecture":
1. **Factual Grounding (Parallel Search MCP)**: The system invokes Parallel MCP to retrieve real-time, external facts. Gemini never answers factual questions purely from its pre-trained weights.
2. **Reasoning Synthesis**: Gemini processes the retrieved evidence against the ongoing `PodcastContext`. If evidence is sparse or contradictory, it maintains structural uncertainty.
3. **Persona/Perspective**: The generated response is styled strictly within the constraints of the `ExpertProfile`.

---

## Technical Stack

### Backend (`services/agent/app`)
- **Language**: Python 3.11+
- **Agent Framework**: Google ADK / LangGraph
- **API Framework**: FastAPI, Pydantic v2
- **Reasoning**: Gemini via `google-genai` SDK
- **Data Persistence**: Firestore (Session State) & Google Cloud Storage (Media Assets)
- **Audio Processing**: FFmpeg
- **External Tools**: Parallel Search MCP (via Google ADK MCP client)
- **TTS Generation**: Gemini TTS — live-verified using `google-genai` SDK with `vertexai=True`, model `gemini-2.5-flash-preview-tts`, voice `Kore`, via Application Default Credentials. No mocks or third-party fallbacks.

### Frontend (`apps/web`)
- **Framework**: Next.js 14+ (App Router)
- **Styling**: Tailwind CSS, shadcn/ui, Framer Motion
- **Communication**: REST API + Server-Sent Events (SSE) (for real-time pipeline status)

---

## The LangGraph State Machine
Defined in `app/graph/workflow.py`, enforcing research on every iteration:
```
PODCAST_INITIALIZATION -> EXPERT_READY -> PODCAST_GENERATION -> CONVERSATION_ACTIVE
  -> [User Question Received] -> QUESTION_RECEIVED
  -> RESEARCH_PLANNING
  -> PARALLEL_RESEARCH
  -> EVIDENCE_SYNTHESIS
  -> EXPERT_RESPONSE_GENERATION
  -> TTS_GENERATION
  -> RESPONSE_PLAYBACK
  -> CONVERSATION_ACTIVE
```
*Note that there is deliberately no graph edge bypassing the research nodes when transitioning from `QUESTION_RECEIVED` to `EXPERT_RESPONSE_GENERATION`.*

---

## Directory Map

```text
mimesis/
├── apps/web/                    # Next.js Podcast Studio UI
├── services/agent/
│   ├── app/
│   │   ├── api/                 # FastAPI routes (Start Session, Ask Question, SSE)
│   │   ├── core/                # Config, logging, budget safeguards
│   │   ├── domain/              # Pydantic models (PodcastSession, ResearchEvidence)
│   │   ├── agents/              # Logical transcreation agents (ResearchPlanner, etc)
│   │   ├── graph/               # LangGraph workflow
│   │   ├── prompts/             # Expert styling and context synthesis Prompts
│   │   ├── providers/           # API interfaces (Gemini TTS, Firestore, FFmpeg)
│   │   └── tools/               # Parallel MCP integration
│   └── tests/                   # Pytest suite
├── .agents/mcp_config.json      # Workspace MCP configuration
└── .env.example                 # Environment variable template
```
