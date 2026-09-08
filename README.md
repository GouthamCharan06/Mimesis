# Mimesis

Mimesis is an agentic interactive podcast platform. Listen to an AI-generated conversation between a host and a fictional expert persona. Interrupt at any time to ask questions—Mimesis will aggressively research your question via Parallel MCP, synthesize the facts contextually, and reply seamlessly in the expert's voice using Gemini TTS.

## Features

- **Mandatory External Grounding**: Every user question forces a live internet search via **Parallel Search MCP**. No LLM hallucinated facts.
- **Persistent Conversation Context**: User inquiries like "Why did you say that?" resolve seamlessly using previous turn contexts stored in a durable LangGraph session.
- **Dynamic Three-Layer Answers**: Integrates Factual Gathering (Parallel), Logical Synthesis (Gemini), and Persona Styling (Expert Profile).
- **Deterministic Audio Muxing**: Combines host interactions and real-time TTS synthesized replies into a final, exportable chronological `SessionRecording`.
- **Event-Driven Progress Indicators**: Transparent (but non-intrusive) frontend indicators streaming Research Progress without raw chain-of-thought dumps.

## Quickstart

### Prerequisites

1. **Python 3.11+** (Use `uv` for package management ideally)
2. **Node.js 20+**
3. **Google Cloud SDK** (for default credentials)
4. **FFmpeg** (installed and in system PATH)

### Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Fill in the required environment variables:
   - `GOOGLE_CLOUD_PROJECT`
   - `PARALLEL_API_KEY` (if authenticating Parallel MCP)
   - Firestore and GCS configurations.

3. Authenticate with Google Cloud locally (enabling Gemini SDK via Application Default Credentials):
   ```bash
   gcloud auth application-default login
   ```

### Running Locally

1. **Install backend dependencies:**
   ```bash
   cd services/agent
   uv venv
   pip install -e .[dev]
   ```

2. **Install frontend dependencies:**
   ```bash
   cd apps/web
   npm install
   ```

3. **Start the development servers (from root):**
   ```bash
   npm run dev
   ```
   - API runs at `http://localhost:8000`
   - Frontend runs at `http://localhost:3000`

### Architecture & Workflows

For detailed sub-system design, see [ARCHITECTURE.md](./ARCHITECTURE.md).

### Stage 2 — Live Verification (All Passed ✅)

All four integration points have been independently verified against the live `gemini-agentic-cinema` Google Cloud project using Application Default Credentials:

| Stage | Provider | Model / Endpoint | Status |
|-------|----------|------------------|--------|
| Gemini Reasoning | `google-genai` SDK (Vertex AI) | `gemini-2.5-flash` | ✅ Verified |
| Parallel Search MCP | HTTP MCP client | `search.parallel.ai` | ✅ Verified |
| Grounded Synthesis | `google-genai` SDK (Vertex AI) | `gemini-2.5-flash` | ✅ Verified |
| Gemini TTS | `google-genai` SDK (Vertex AI) | `gemini-2.5-flash-preview-tts` | ✅ Verified |

**No mocks, fallbacks, or fake audio were used.** The TTS stage generates real LINEAR16 WAV audio (~144 KB for a short sentence).

**Verification command:**
```bash
cd services/agent
python scripts/verify_connectivity.py
```

> ⚠️ **Cost Warning:** Each run makes 2 Gemini calls, 1 Parallel search, and 1 TTS generation against live Google Cloud billing.
