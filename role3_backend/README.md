# Role 3 Backend — HH Goa 2026

FastAPI backend for the Voice-Enabled RAG system.

## What this is

This is Role 3's implementation — the central orchestration layer. It connects:
- **Role 1** (FAISS retrieval) via `retrieve_context()` 
- **Role 2** (Sarvam STT + Frontend) via `/api/voice` and `/api/query`

## Quick start

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — add GROQ_API_KEY, SARVAM_API_KEY

# 4. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| POST | `/api/query` | Text query → RAGResponse |
| POST | `/api/voice` | Base64 audio → STT → RAGResponse |

## Run tests

```bash
pytest tests/ -v
```

All tests use mocks — no live API keys required.

## Integration stubs

Until Role 1 and Role 2 land their code, the backend uses:
- `app/retrieval/mock_retriever.py` → fake `retrieve_context()`
- `app/stt/mock_stt.py` → fake `transcribe()`

**To integrate Role 1:** in `app/rag/orchestrator.py`, replace:
```python
from app.retrieval.mock_retriever import retrieve_context
# with:
from app.retrieval.retriever import retrieve_context
```

**To integrate Role 2 STT:** in `app/rag/orchestrator.py`, replace:
```python
from app.stt.mock_stt import transcribe
# with:
from app.stt.sarvam import transcribe
```

## File structure

```
role3_backend/
├── app/
│   ├── main.py             # FastAPI app
│   ├── config.py           # Settings from env
│   ├── schemas.py          # Shared Pydantic contracts (all roles)
│   ├── api/
│   │   ├── health.py       # GET /health
│   │   └── routes.py       # POST /api/query, /api/voice
│   ├── rag/
│   │   ├── orchestrator.py # Full RAG pipeline + latency instrumentation
│   │   └── prompt.py       # Prompt builder
│   ├── llm/
│   │   └── groq_client.py  # Groq client + Tenacity retries
│   ├── guardrails/
│   │   ├── input_guard.py  # Validation + NSFW filter
│   │   ├── context_guard.py# Context sufficiency check
│   │   └── grounding.py    # Deterministic grounding check
│   ├── retrieval/
│   │   └── mock_retriever.py # → Replace with Role 1
│   └── stt/
│       └── mock_stt.py       # → Replace with Role 2
└── tests/
    ├── test_api.py
    ├── test_guardrails.py
    └── test_orchestrator.py
```

## Latency budget

Target: **< 200 ms end-to-end**. Every stage is measured in `latency_breakdown`.

| Stage | Target |
|-------|--------|
| STT (Sarvam) | ~50 ms |
| Retrieval (Role 1 FAISS) | ~15 ms |
| Guardrails | < 1 ms |
| LLM Generation (Groq) | ~100 ms |
| Grounding check | < 1 ms |
| **Total** | **< 200 ms** |
