# Role 3 Planned Changes (Backend, Orchestration, Guardrails)

This document summarizes the agreed-upon design updates and implementation plan for **Role 3**, so that all teammates are aligned before implementation begins.

## 1. Key Design Decisions

- **Model Agnostic**: We are keeping the LLM configuration flexible. We'll use an environment variable (e.g., `GROQ_MODEL`) so it can be swapped out easily without changing code.
- **Grounding Latency**: To stay within the 200ms latency budget, our grounding checks will use a **fast, deterministic** approach (e.g., checking if generated citations/facts exist within the retrieved text block). This is significantly faster (<1ms) than doing a secondary LLM call to verify grounding (~100-300ms).
- **Voice Payload Format**: The `/api/voice` endpoint will initially expect a JSON payload where the audio is encoded as a `base64` string. This can be adapted later if necessary.
- **NSFW Guardrail**: Since Groq models don't enforce a native NSFW filter, Role 3 will add an explicitly coded NSFW and safety guardrail within `app/guardrails/input_guard.py` that intercepts the request before hitting the LLM.

## 2. Where to Find the Detailed Plan

The full line-by-line breakdown of the architecture we will implement can be found in the system-generated **Implementation Plan**. 

**Planned File Structure for Role 3:**
- `app/schemas.py`: Shared Pydantic contracts (`DocumentChunk`, `LLMAnswer`, `RAGResponse`).
- `app/main.py` & `app/api/routes.py`: FastAPI setup.
- `app/rag/orchestrator.py`: Request lifecycle and latency instrumentation.
- `app/llm/groq_client.py`: Groq client with Tenacity retries.
- `app/guardrails/`: Containing `input_guard.py` (includes the NSFW filter), `context_guard.py`, and `grounding.py`.

## 3. Implementation Status (Role 1 Integration)

The integration of Role 1's FAISS retrieval system into Role 3's backend is now **Complete and Verified**:
- **Unified Schema:** `app/schemas.py` now serves as the single source of truth for `DocumentChunk` with properties `effective_score` and `effective_strategy` bridging the gap between Role 1 and Role 3 field naming styles.
- **Real Retriever Wire-up:** `app/retrieval/retriever.py` imported from Role 1 is fully active. `init_retrieval` runs on FastAPI startup, and `retrieve_context` handles RAG queries dynamically.
- **Latency & Reliability Constraints Met:** Guardrails updated to use `effective_score`. All 45 pipeline tests pass (including lazy FAISS imports to enable purely mocked backend unit testing).
- **Role 2 Readiness:** The orchestrator and health endpoints are perfectly poised to receive Role 2's STT integration (currently stubbed).

*Status: Role 1 Integration Complete. Awaiting Role 2 STT integration.*
