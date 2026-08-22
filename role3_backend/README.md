# Role 3 Backend — HH Goa 2026

FastAPI backend for the Voice-Enabled RAG system.

## Status

**Role 1 integration: COMPLETE ✅**  
**Role 2 (STT) integration: PENDING — stub in place**

## What this is

The central orchestration layer connecting all three roles:

- **Role 1** (FAISS retrieval) → `app/retrieval/retriever.py` (real, active)
- **Role 2** (Sarvam STT + Frontend) → `app/stt/mock_stt.py` (stub — swap when ready)

## Quick start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows

# 2. Install dependencies (includes Role 1 retrieval deps)
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — add GROQ_API_KEY, SARVAM_API_KEY, set FAISS_INDEX_DIR

# 4. Ensure the FAISS index exists (built by Role 1)
#    If not built yet, run from the role1/ directory:
#    python embed_index.py --chunks data/chunks/chunks_metadata_aware.jsonl --output-dir data/index

# 5. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness + FAISS subsystem diagnostics |
| POST | `/api/query` | Text query → RAGResponse |
| POST | `/api/voice` | Base64 audio → STT → RAGResponse |

## Run tests

```bash
pytest tests/ -v
```

All 45 tests pass. All external dependencies (Groq, retriever at startup, STT) are mocked in tests — no live API keys required.

## Integration state

### Role 1 (FAISS Retrieval) — COMPLETE

`app/retrieval/retriever.py` — Role 1's full retrieval engine, ported in.

On startup (`app/main.py` lifespan):
```python
from app.retrieval.retriever import init_retrieval
init_retrieval(settings.faiss_index_dir)  # loads FAISS index + model into RAM
```

Per request (orchestrator):
```python
from app.retrieval.retriever import retrieve_context
chunks = await retrieve_context(query, top_k=3)
```

Role 1 files integrated into `app/retrieval/`:
- `retriever.py` — main `retrieve_context()` API + `RetrievalIndex`
- `hybrid_retrieval.py` — BM25 + FAISS hybrid via Reciprocal Rank Fusion
- `security_guardrails.py` — SQL injection / prompt injection / path traversal defense

### Role 2 (STT) — PENDING

**To integrate Role 2 STT:** in `app/rag/orchestrator.py`, replace:
```python
from app.stt.mock_stt import transcribe
# with:
from app.stt.sarvam import transcribe
```

Interface contract:
```python
async def transcribe(audio_bytes: bytes, content_type: str) -> str:
    ...
```

## File structure

```
role3_backend/
├── app/
│   ├── main.py              # FastAPI app + FAISS startup init
│   ├── config.py            # Settings (incl. FAISS_INDEX_DIR)
│   ├── schemas.py           # Unified Pydantic contracts — ALL roles
│   ├── api/
│   │   ├── health.py        # GET /health (+ retrieval subsystem status)
│   │   └── routes.py        # POST /api/query, /api/voice
│   ├── rag/
│   │   ├── orchestrator.py  # Full RAG pipeline + latency instrumentation
│   │   └── prompt.py        # Prompt builder
│   ├── llm/
│   │   └── groq_client.py   # Groq client + Tenacity retries
│   ├── guardrails/
│   │   ├── input_guard.py   # Validation + NSFW filter
│   │   ├── context_guard.py # Context sufficiency check (uses effective_score)
│   │   └── grounding.py     # Deterministic grounding check
│   ├── retrieval/
│   │   ├── retriever.py        # ← Role 1 REAL implementation (active)
│   │   ├── hybrid_retrieval.py # ← Role 1 BM25+FAISS hybrid
│   │   ├── security_guardrails.py # ← Role 1 security layer
│   │   └── mock_retriever.py   # ← Kept for reference; no longer used
│   └── stt/
│       └── mock_stt.py         # → Replace with Role 2's sarvam.py
└── tests/
    ├── test_api.py          # 7 tests — API endpoints
    ├── test_guardrails.py   # 27 tests — all guardrails
    └── test_orchestrator.py # 7 tests — full pipeline (mocked)
    # Total: 45/45 passing
```

## Unified schema

`app/schemas.py` is the single source of truth for all three roles.

`DocumentChunk` accepts both Role 1 field names (`strategy`, `score`) and
Role 3 names (`chunk_strategy`, `similarity_score`) as optional fields.
Use `chunk.effective_score` and `chunk.effective_strategy` in pipeline
code for transparent dual-field access.

## Latency budget

Target: **< 200 ms end-to-end**. Every stage is measured in `latency_breakdown`.

| Stage | Target | Notes |
|-------|--------|-------|
| STT (Sarvam) | ~50 ms | Role 2 — stub active |
| Retrieval (Role 1 FAISS) | ~78 ms P50 | Measured by Role 1 |
| Guardrails | < 1 ms | Deterministic |
| LLM Generation (Groq) | ~100 ms | Groq llama3-8b |
| Grounding check | < 1 ms | Token overlap |
| **Total** | **< 200 ms** | |
