# HH Goa 2026 — ROLES (COMPACT ROUTER)

## Role 1 — Dataset, Chunking & Retrieval

**Command:** `Work as Role 1`

Read:

```text
roles/ROLE1_README.md
progress/ROLE1_PROGRESS.md
```

Owns:
- MSMARCO-XI ingestion/normalization
- semantic chunking
- sliding-window chunking
- embeddings
- FAISS/in-memory retrieval
- retrieval tests/benchmarks

Do not casually own frontend, STT, LLM orchestration or final guardrails.

## Role 2 — Voice, STT, Frontend & Benchmarking

**Command:** `Work as Role 2`

Read:

```text
roles/ROLE2_README.md
progress/ROLE2_PROGRESS.md
```

Owns:
- vanilla JS UI
- microphone/audio capture
- Sarvam/approved STT integration
- transcript flow
- latency instrumentation
- P50/P70/P100 benchmark suite

Do not casually own dataset/chunking internals, FAISS design, LLM harness or final guardrails.

## Role 3 — Backend, RAG Harness, Guardrails & Integration

**Command:** `Work as Role 3`

Read:

```text
roles/ROLE3_README.md
progress/ROLE3_PROGRESS.md
```

Owns:
- FastAPI
- orchestration
- shared Pydantic contracts
- Groq/LLM integration
- structured outputs
- retries
- input/context/grounding guardrails
- missing-context refusal
- integration

## Shared rule

Roles are ownership boundaries, not isolated silos. Shared interfaces must be coordinated. Integration requires all three progress logs plus `ARCHITECTURE.md` and `rules/INTEGRATION.md`.

## Full historical role specification

Preserved at:

```text
roles/COMPLETE_ROLE_SPEC_REFERENCE.md
```
