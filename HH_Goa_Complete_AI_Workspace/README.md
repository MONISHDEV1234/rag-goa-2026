# HH Goa 2026 — Voice-Enabled RAG System

> **Hackathon:** HH Goa 2026 — Shortlisting Task 2  
> **Project:** Voice-Enabled Retrieval-Augmented Generation (RAG) System  
> **Deadline:** August 22, 2026 — 11:59 PM IST  
> **Primary Goal:** Build an end-to-end voice-to-answer RAG pipeline with a target latency of **under 200 ms**.

---

## 1. Project Overview

This repository contains our implementation for **HH Goa 2026 Task 2: Build a Voice-Enabled RAG Model**.

The system accepts a spoken question, converts speech to text, retrieves relevant information from the mandatory MSMARCO-XI dataset, generates a grounded answer using an LLM, validates the answer, and returns the final response.

Official pipeline:

```text
Voice Input
    ↓
Speech-to-Text
    ↓
Chunking / Vector Retrieval
    ↓
Answer Generation
    ↓
Grounded Response
```

The official task requires:

- AI4Bharat MSMARCO-XI
- Sarvam or ElevenLabs for STT
- Multiple/non-naive chunking strategies
- Full pipeline latency under 200 ms
- P50/P70/P100 latency analytics
- A structured model harness
- Guardrails for off-topic, unsafe, missing-context and hallucinated answers

---

# 2. IMPORTANT: Instructions for AI Coding Agents

This repository is designed for Claude, Cursor, Codex, Gemini, GitHub Copilot and other AI coding agents.

`README.md` remains the **complete master project specification**. It is authoritative for what the project must build. However, agents must use the token-efficient documentation router in `RULES.md` instead of rereading this entire document for every small task.

## Mandatory agent entry flow

```text
New instruction
      ↓
Read RULES.md
      ↓
Identify role/task
      ↓
Read relevant role README
      ↓
Read relevant progress log
      ↓
Read only the required rules/docs/sections
      ↓
Inspect actual repository
      ↓
Plan → Implement → Test → Verify → Log
```

## When the full README must be read

Read the full `README.md` when:

- the user explicitly asks for a full project review;
- architecture or major technology decisions are changing;
- requirements are unclear or conflicting;
- multiple roles are being integrated;
- final deployment/submission is being prepared;
- a task depends on project-wide requirements not covered by the compact role documentation.

For ordinary role work, use the relevant role README and only the necessary sections of this master file.

## Universal engineering requirements

1. Inspect the actual repository before editing.
2. Preserve working behavior unless a justified change is required.
3. Follow role ownership boundaries.
4. Never hardcode or expose secrets.
5. Never replace the mandatory MSMARCO-XI dataset.
6. Never fabricate benchmark, test, deployment or completion claims.
7. Do not remove latency instrumentation to make results look better.
8. Do not rebuild embeddings/indexes during a normal request unless explicitly required by the measured design.
9. Keep expensive preprocessing offline where the architecture allows it.
10. Use asynchronous I/O for external services.
11. Use Pydantic for shared contracts and structured outputs.
12. Retry only transient failures.
13. Refuse safely when context is insufficient.
14. Benchmark performance changes before claiming improvement.
15. Avoid unnecessary dependencies and unrelated refactors.
16. Update the appropriate progress log after meaningful work.
17. Never rewrite historical progress entries. Append a new entry for changes.

## AI priority

When trade-offs are necessary:

```text
Correctness
    >
Groundedness
    >
Reliability
    >
Safety
    >
Latency
    >
Convenience
```

A fast hallucinated answer is worse than a reliable refusal.

# 3. Official Task Requirements

## Dataset

Mandatory:

https://huggingface.co/datasets/ai4bharat/MSMARCO-XI

## Speech-to-Text

Use one:

- Sarvam
- ElevenLabs

**Current project decision: Sarvam AI**

## Chunking

The task explicitly requires more than one naive fixed-size chunking approach.

We will implement and benchmark:

1. Semantic chunking
2. Sliding-window chunking
3. Metadata-aware chunking where useful

## Latency

Target:

```text
< 200 ms end-to-end
```

## Analytics

Required:

```text
P50
P70
P100
```

These must be calculated from a reasonable test suite, not a single best-case request.

## Model Harness

The LLM must run inside structured orchestration containing:

- Input/output validation
- Retrieval/tool orchestration
- Retry handling
- Error recovery
- Structured outputs

## Guardrails

The system must handle:

- Off-topic queries
- Unsafe/inappropriate inputs
- Missing context
- Hallucinations
- Ungrounded answers

---

# 4. Architecture

```text
                         USER
                           │
                           ▼
                    ┌─────────────┐
                    │ Microphone  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Vanilla JS  │
                    │  Frontend   │
                    └──────┬──────┘
                           │ Audio
                           ▼
                    ┌─────────────┐
                    │   FastAPI   │
                    │ API Gateway │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Sarvam STT  │
                    └──────┬──────┘
                           │
                       Transcript
                           │
                           ▼
                    ┌─────────────┐
                    │ Input Guard │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ FastEmbed   │
                    │ Embeddings  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    FAISS    │
                    │     RAM     │
                    └──────┬──────┘
                           │
                         Top-K
                        Context
                           │
                           ▼
                    ┌─────────────┐
                    │ RAG Harness │
                    │ Retry/Tools │
                    │ Validation  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Groq LLM  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Grounding   │
                    │   Checker   │
                    └──────┬──────┘
                           │
                    ┌──────┴───────┐
                    │              │
                 Grounded      Ungrounded
                    │              │
                    ▼              ▼
                 Answer         Refusal
```

---

# 5. Offline vs Online Processing

This distinction is critical for latency.

## Offline

```text
MSMARCO-XI
    ↓
Preprocessing
    ↓
Chunking
    ↓
Embedding generation
    ↓
FAISS index construction
    ↓
Persist index
```

This happens before deployment.

## Application Startup

```text
Load FAISS index
      +
Load metadata
      +
Load embedding model
      ↓
Application ready
```

## Online

```text
Voice
 ↓
STT
 ↓
Input guard
 ↓
Query embedding
 ↓
FAISS retrieval
 ↓
RAG harness
 ↓
LLM
 ↓
Grounding check
 ↓
Answer
```

Never download the dataset, rebuild FAISS or embed the complete corpus during a user request.

---

# 6. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5 + CSS + Vanilla JavaScript |
| Audio | Browser MediaRecorder API |
| Backend | FastAPI |
| Runtime | Python 3.11+ |
| STT | Sarvam AI |
| Dataset | AI4Bharat MSMARCO-XI |
| Dataset Loader | Hugging Face `datasets` |
| Embeddings | FastEmbed |
| Vector Search | FAISS |
| LLM | Groq |
| Validation | Pydantic |
| Retries | Tenacity |
| HTTP | httpx |
| Async | asyncio |
| Benchmarking | Python / NumPy / Pandas |
| Deployment | Hugging Face Spaces or Render |
| Version Control | Git + GitHub |

---

# 7. Repository Structure

```text
rag-goa-2026/
│
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── health.py
│   │
│   ├── stt/
│   │   ├── __init__.py
│   │   ├── sarvam_client.py
│   │   └── audio.py
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── dataset_loader.py
│   │   ├── preprocessing.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── vector_store.py
│   │   └── retriever.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── groq_client.py
│   │   ├── harness.py
│   │   └── prompts.py
│   │
│   └── guardrails/
│       ├── __init__.py
│       ├── input_guard.py
│       ├── safety.py
│       └── grounding.py
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── index/
│
├── scripts/
│   ├── download_dataset.py
│   ├── preprocess.py
│   ├── build_index.py
│   └── benchmark.py
│
├── benchmarks/
│   ├── queries.json
│   ├── results.json
│   └── benchmark_latency.py
│
└── tests/
    ├── test_retrieval.py
    ├── test_stt.py
    ├── test_guardrails.py
    ├── test_harness.py
    └── test_api.py
```

---

# 8. Three-Person Ownership

## Person 1 — Dataset & Retrieval

Owns:

```text
app/retrieval/
data/
scripts/download_dataset.py
scripts/preprocess.py
scripts/build_index.py
```

Responsibilities:

- Dataset ingestion
- Dataset inspection
- Preprocessing
- Semantic chunking
- Sliding-window chunking
- Metadata-aware chunking
- Embeddings
- FAISS
- Retrieval API
- Retrieval benchmarking

Primary function:

```python
async def retrieve_context(
    query: str,
    top_k: int = 3
) -> list[DocumentChunk]:
    ...
```

---

## Person 2 — STT, Frontend & Benchmarking

Owns:

```text
app/stt/
frontend/
benchmarks/
scripts/benchmark.py
```

Responsibilities:

- Sarvam integration
- Microphone recording
- Audio handling
- Streaming where supported
- Frontend
- Latency instrumentation
- P50/P70/P100
- Benchmark suite

---

## Person 3 — Backend, LLM & Guardrails

Owns:

```text
app/main.py
app/api/
app/llm/
app/guardrails/
app/config.py
```

Responsibilities:

- FastAPI
- API routes
- Groq integration
- RAG orchestration
- Structured LLM output
- Tenacity retries
- Guardrails
- Grounding
- Error handling
- Integration
- Deployment

---

# 9. Shared Data Contracts

Do not casually modify these schemas.

## DocumentChunk

```python
from pydantic import BaseModel


class DocumentChunk(BaseModel):
    text: str
    doc_id: str
    chunk_strategy: str
    similarity_score: float
```

## RAGResponse

```python
from pydantic import BaseModel
from typing import List


class RAGResponse(BaseModel):
    transcript: str
    answer: str
    is_grounded: bool
    retrieved_sources: List[DocumentChunk]
    latency_breakdown: dict
```

Example:

```json
{
  "transcript": "What is machine learning?",
  "answer": "Machine learning is ...",
  "is_grounded": true,
  "retrieved_sources": [],
  "latency_breakdown": {
    "stt": 52,
    "retrieval": 7,
    "generation": 76,
    "total": 140
  }
}
```

---

# 10. Recommended Additional Schemas

```python
class QueryRequest(BaseModel):
    query: str
    top_k: int = 3
```

```python
class LLMAnswer(BaseModel):
    answer: str
    confidence: float
    citations: list[str]
    grounded: bool
```

```python
class BenchmarkResult(BaseModel):
    query_id: str
    stt_ms: float
    retrieval_ms: float
    generation_ms: float
    grounding_ms: float
    total_ms: float
```

---

# 11. Dataset Processing

Download:

```bash
python scripts/download_dataset.py
```

Preprocess:

```bash
python scripts/preprocess.py
```

Build index:

```bash
python scripts/build_index.py
```

The generated index should be stored under:

```text
data/index/
```

Large generated data should not automatically be committed to GitHub.

---

# 12. Chunking

We must implement multiple strategies.

## A. Semantic Chunking

```text
Document
 ↓
Sentences
 ↓
Sentence embeddings
 ↓
Adjacent semantic similarity
 ↓
Boundary detection
 ↓
Semantic chunks
```

Goal: keep semantically related content together.

## B. Sliding Window

Example:

```text
Chunk 1:
S1 S2 S3 S4

Chunk 2:
   S3 S4 S5 S6

Chunk 3:
      S5 S6 S7 S8
```

## C. Metadata-Aware

Preserve useful metadata:

```json
{
  "chunk_id": "doc_123_04",
  "doc_id": "doc_123",
  "strategy": "semantic",
  "position": 4,
  "text": "..."
}
```

Chunking strategies must be benchmarked rather than assumed to be optimal.

---

# 13. Embedding Strategy

Initial model:

```text
BAAI/bge-small-en-v1.5
```

using FastEmbed.

Because MSMARCO-XI contains Indic-language content, embedding quality must be tested.

Benchmark candidate models on:

```text
Retrieval quality
+
Embedding latency
+
Memory usage
```

Do not choose a model solely by speed.

---

# 14. FAISS

FAISS must be loaded into memory.

Startup:

```text
Application starts
 ↓
Load FAISS
 ↓
Load metadata
 ↓
Load embedding model
 ↓
Ready
```

Request:

```text
Query
 ↓
Embedding
 ↓
FAISS search
 ↓
Top-K results
```

Do not load/rebuild FAISS per request.

---

# 15. Retrieval Threshold

Top-K retrieval alone is not enough.

Use similarity scores:

```text
Query
 ↓
FAISS
 ↓
Similarity scores
 ↓
Threshold
```

If no result is sufficiently relevant:

```text
Do not call the LLM.
Return a grounded refusal.
```

The threshold must be experimentally tuned.

---

# 16. STT

Current provider:

```text
Sarvam AI
```

Interface:

```python
async def transcribe(audio_bytes: bytes) -> str:
    ...
```

Requirements:

- Async/non-blocking API calls
- Connection reuse
- Timeout handling
- Provider error handling
- Minimal audio conversion
- Streaming where practical
- Precise latency measurement

---

# 17. RAG Harness

The harness should execute:

```text
User Query
 ↓
Input Validation
 ↓
Retrieve Context
 ↓
Context Sufficiency Check
 ↓
Build Prompt
 ↓
Structured LLM Call
 ↓
Pydantic Validation
 ↓
Grounding Check
 ↓
Final Response
```

Recommended interface:

```python
async def run_rag(query: str) -> RAGResponse:
    ...
```

The LLM should never be the only component responsible for deciding whether the answer is supported.

---

# 18. Retry Policy

Use:

```text
tenacity
```

Retry transient failures:

- Network errors
- Temporary provider failures
- Rate limiting where appropriate

Do not retry indefinitely.

Validation failures and guardrail refusals should not be blindly retried.

---

# 19. Guardrails

## Input Guard

Reject clearly unsupported/off-topic requests.

## Missing Context

If retrieval is insufficient:

```text
Do not call the LLM.
```

Return:

```text
I couldn't find enough information in the provided knowledge base
to answer that question.
```

## Grounding

```text
Retrieved Context
+
Generated Answer
 ↓
Grounding Checker
```

Output:

```text
SUPPORTED
```

or:

```text
UNSUPPORTED
```

Unsupported answers must not be presented as factual answers.

## Safety

Handle unsafe/inappropriate queries safely.

Guardrails must not be removed for performance.

---

# 20. Prompt Rules

The LLM should:

1. Answer only using retrieved context.
2. Never invent facts.
3. Be concise.
4. State uncertainty when appropriate.
5. Follow structured output.
6. Include source identifiers when applicable.
7. Refuse when context is insufficient.

Keep output concise because generation latency matters.

---

# 21. Latency Instrumentation

Measure at minimum:

```text
STT
Embedding
Retrieval
Harness
Generation
Grounding
Total
```

Use a monotonic clock for duration measurements.

Example:

```json
{
  "stt": 52,
  "embedding": 7,
  "retrieval": 4,
  "generation": 73,
  "grounding": 5,
  "total": 141
}
```

All durations are milliseconds.

---

# 22. Initial Latency Budget

Engineering target:

| Stage | Target |
|---|---:|
| STT | ~60 ms |
| Query embedding | ~10 ms |
| FAISS | ~5 ms |
| Harness/guardrails | ~10 ms |
| LLM | ~80 ms |
| Final processing | ~10 ms |
| **Total** | **~175 ms** |

These are targets, not claimed results.

Actual performance must come from benchmarks.

---

# 23. Benchmarking

Initial benchmark:

```text
100 queries
```

Each query should record:

```json
{
  "query_id": 1,
  "stt_ms": 53,
  "embedding_ms": 7,
  "retrieval_ms": 4,
  "generation_ms": 75,
  "grounding_ms": 5,
  "total_ms": 144
}
```

Calculate:

```text
P50
P70
P100
```

Never hardcode results.

---

# 24. Benchmark Categories

Test:

1. Normal answerable queries
2. Complex queries
3. Missing-context queries
4. Off-topic queries
5. Long/noisy queries
6. Repeated queries
7. Provider/network failure cases

This provides a more meaningful performance picture.

---

# 25. Frontend

Keep the frontend lightweight:

```text
HTML5
CSS
Vanilla JavaScript
```

The UI should show:

```text
Voice recording
Transcript
Answer
Grounded status
Latency breakdown
```

Example:

```text
┌──────────────────────────────────────┐
│          VOICE RAG — HH GOA          │
│                                      │
│          🎙 [ Record ]               │
│                                      │
│ Transcript:                          │
│ "What is ...?"                       │
│                                      │
│ Answer:                              │
│ "..."                                │
│                                      │
│ STT          54 ms                   │
│ Retrieval     7 ms                   │
│ Generation   76 ms                   │
│ Total       137 ms                   │
│                                      │
│ ✓ Grounded                           │
└──────────────────────────────────────┘
```

---

# 26. API Endpoints

## Health

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

## Text RAG

```http
POST /api/query
```

Request:

```json
{
  "query": "What is ...?",
  "top_k": 3
}
```

## Voice RAG

```http
POST /api/voice
```

Input:

```text
multipart/form-data
audio=<audio file>
```

Response:

```json
{
  "transcript": "...",
  "answer": "...",
  "is_grounded": true,
  "retrieved_sources": [],
  "latency_breakdown": {
    "stt": 52,
    "retrieval": 6,
    "generation": 76,
    "total": 140
  }
}
```

---

# 27. Environment Variables

`.env`

```env
SARVAM_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
```

`.env.example`

```env
SARVAM_API_KEY=
GROQ_API_KEY=
```

Never commit `.env`.

---

# 28. Installation

Create environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install:

```bash
pip install -r requirements.txt
```

---

# 29. Running the Backend

Development:

```bash
uvicorn app.main:app --reload
```

Production-style:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

# 30. Testing

Run all tests:

```bash
pytest
```

Individual:

```bash
pytest tests/test_retrieval.py
pytest tests/test_stt.py
pytest tests/test_guardrails.py
pytest tests/test_harness.py
pytest tests/test_api.py
```

---

# 31. Benchmark Command

```bash
python benchmarks/benchmark_latency.py
```

Expected format:

```text
================================================
          HH GOA RAG LATENCY BENCHMARK
================================================

Queries tested: 100

Stage             P50       P70       P100
------------------------------------------------
STT               XX ms     XX ms     XX ms
Embedding         XX ms     XX ms     XX ms
Retrieval         XX ms     XX ms     XX ms
Generation        XX ms     XX ms     XX ms
Grounding         XX ms     XX ms     XX ms
------------------------------------------------
TOTAL             XX ms     XX ms     XX ms

Target: <200 ms
================================================
```

---

# 32. Error Handling

### STT Failure

```text
Unable to transcribe audio. Please try again.
```

### Empty Transcript

```text
No speech detected.
```

### Retrieval Failure

```text
Unable to search the knowledge base.
```

### No Context

```text
I couldn't find enough information in the provided
knowledge base to answer that question.
```

### LLM Failure

```text
The answer service is temporarily unavailable.
```

### Grounding Failure

```text
I couldn't verify the generated answer against the
available context.
```

Never expose stack traces, API keys or internal secrets.

---

# 33. Performance Rules

## DO

- Keep FAISS in RAM.
- Precompute document embeddings.
- Reuse HTTP connections.
- Use async I/O.
- Keep prompts short.
- Retrieve only a small top-K.
- Limit answer length.
- Measure every stage.
- Warm models where practical.
- Benchmark every optimization.

## DON'T

- Rebuild FAISS per request.
- Download data per request.
- Embed the whole corpus per request.
- Send the entire dataset to the LLM.
- Add unnecessary network calls.
- Use unnecessarily large prompts.
- Remove guardrails for speed.
- Fake latency numbers.

---

# 34. LLM Performance

The LLM may be one of the largest latency contributors.

Optimize:

- Model choice
- Prompt length
- Retrieved context size
- Output token limit
- HTTP connection reuse
- Number of LLM calls
- TTFT
- Total generation time

Do not perform multiple LLM calls unless they provide meaningful value.

---

# 35. TTFT vs Total Generation

Where practical, measure:

```text
TTFT
```

and:

```text
Total generation time
```

TTFT = time until the first useful generated token.

Total generation = time until the complete answer is generated.

The benchmark must clearly document what is included in the official end-to-end latency metric.

---

# 36. Cold vs Warm Start

Measure separately when possible.

### Cold

```text
Server startup
 ↓
Model/index loading
 ↓
First query
```

### Warm

```text
Running server
 ↓
Query
```

Do not mix these numbers without documentation.

---

# 37. Quality Evaluation

Track:

```text
Retrieval relevance
Answer correctness
Groundedness
Refusal correctness
Latency
```

The goal is:

```text
Fast
+
Accurate
+
Grounded
```

---

# 38. Demo Queries

Prepare known queries before recording.

### Valid query

Expected:

```text
Correct answer
+
Grounded = true
```

### Missing context

Expected:

```text
Refusal
```

### Off-topic

Expected:

```text
Guardrail/refusal
```

### Noisy/long voice input

Expected:

```text
Graceful processing or graceful failure
```

---

# 39. Git Workflow

Branches:

```text
main
│
├── feature/retrieval
├── feature/stt-benchmark
└── feature/backend-harness
```

Person 1:

```bash
git checkout -b feature/retrieval
```

Person 2:

```bash
git checkout -b feature/stt-benchmark
```

Person 3:

```bash
git checkout -b feature/backend-harness
```

Avoid modifying another teammate's module without coordination.

---

# 40. Commit Convention

Use:

```text
feat: add semantic chunking
feat: implement FAISS retrieval
feat: add Sarvam STT client
feat: add latency benchmark
feat: implement grounding guardrail
fix: handle empty retrieval results
perf: optimize FAISS query path
```

Avoid meaningless commits such as:

```text
update
final
changes
test
```

---

# 41. Development Roadmap

## Phase 1 — Foundation

### Person 1

```text
[ ] Download dataset
[ ] Inspect dataset
[ ] Preprocess
[ ] Implement first chunking strategy
[ ] Test embeddings
```

### Person 2

```text
[ ] Connect Sarvam
[ ] Record audio
[ ] Transcribe audio
[ ] Create benchmark skeleton
```

### Person 3

```text
[ ] Create FastAPI
[ ] Create schemas
[ ] Connect Groq
[ ] Create harness
[ ] Create guardrail architecture
```

---

# 42. Phase 2 — Core Components

### Person 1

```text
[ ] Semantic chunking
[ ] Sliding-window chunking
[ ] Metadata-aware chunking
[ ] Embedding pipeline
[ ] FAISS
[ ] Retrieval API
```

### Person 2

```text
[ ] Streaming/low-latency STT
[ ] Frontend microphone
[ ] Latency instrumentation
[ ] 100-query benchmark
```

### Person 3

```text
[ ] RAG orchestration
[ ] Structured output
[ ] Tenacity retries
[ ] Input guardrail
[ ] Missing-context guard
[ ] Grounding checker
```

---

# 43. Phase 3 — Integration

Integrate:

```text
Frontend
 ↓
FastAPI
 ↓
Sarvam
 ↓
Retriever
 ↓
Groq
 ↓
Grounding
 ↓
Response
```

First priority:

> Get the complete pipeline working before optimizing.

It is acceptable if the first integrated version is slower than 200 ms.

---

# 44. Phase 4 — Optimization

Run:

```text
100+ queries
```

Identify the bottleneck:

```text
STT = ?
Embedding = ?
Retrieval = ?
LLM = ?
Grounding = ?
```

Optimize the actual bottleneck.

Do not spend significant time reducing a 5 ms component to 2 ms if another component takes 200 ms.

---

# 45. Phase 5 — Final Validation

```text
[ ] Normal queries
[ ] Complex queries
[ ] Missing context
[ ] Off-topic
[ ] Unsafe input
[ ] Bad audio
[ ] STT failure
[ ] LLM failure
[ ] Retrieval failure
[ ] Grounding failure
[ ] 100+ query benchmark
[ ] P50
[ ] P70
[ ] P100
```

---

# 46. Deployment Checklist

```text
[ ] Environment variables configured
[ ] Dataset/index available
[ ] FastAPI starts
[ ] Frontend works
[ ] Sarvam works
[ ] Groq works
[ ] HTTPS works
[ ] CORS configured
[ ] /health works
[ ] Voice endpoint works
[ ] Text endpoint works
[ ] Guardrails work
[ ] Final benchmark completed
```

---

# 47. Submission

Official submission requires:

- GitHub repository
- Live working link
- Process video
- Demo video
- Submission form

Form:

https://forms.gle/MNvCjcv23Hn2Eeu58

Deadline:

**August 22, 2026 — 11:59 PM**

No resubmissions are allowed according to the task document, so perform a final verification before submitting.

---

# 48. Videos

## Video 1 — Process

Duration:

**90 seconds**

Show:

- Team collaboration
- Architecture planning
- Chunking strategies
- Development process
- Technical decisions

This should be a process video, not the product demo.

## Video 2 — Demo

Show:

```text
Microphone
 ↓
Speech
 ↓
Transcript
 ↓
Retrieval
 ↓
Answer
 ↓
Latency
 ↓
Grounding
```

---

# 49. Social Media

Every team member must upload both videos to:

```text
Instagram
X / Twitter
```

At least one Instagram account must be public.

Every post must contain:

```text
#RAGInGoa
```

---

# 50. Definition of Done

```text
[ ] Mandatory MSMARCO-XI dataset used
[ ] Voice input works
[ ] Sarvam STT works
[ ] Multiple chunking strategies implemented
[ ] Local embeddings work
[ ] FAISS retrieval works
[ ] RAG generation works
[ ] Structured LLM output works
[ ] Harness exists
[ ] Retry system exists
[ ] Off-topic guard exists
[ ] Safety guard exists
[ ] Missing-context handling exists
[ ] Grounding validation exists
[ ] FastAPI works
[ ] Frontend works
[ ] Latency instrumentation works
[ ] P50 calculated
[ ] P70 calculated
[ ] P100 calculated
[ ] Benchmark completed
[ ] Deployment works
[ ] GitHub ready
[ ] README updated
[ ] Process video complete
[ ] Demo video complete
[ ] Social media requirements complete
[ ] Submission form completed
```

---

# 51. Golden Rules

### 1. Never fake benchmark numbers.

### 2. Never remove guardrails to achieve a better latency score.

### 3. Never rebuild FAISS during inference.

### 4. Never embed the complete dataset during a request.

### 5. Never send the complete dataset to the LLM.

### 6. Never answer when context is clearly insufficient.

### 7. Never commit API keys.

### 8. Measure before optimizing.

### 9. Keep components modular.

### 10. Coordinate changes to shared schemas.

### 11. Prefer a fast, grounded answer over a long answer.

### 12. A fast wrong answer is worse than a reliable refusal.

---

# 52. Project Success Criteria

The final system should demonstrate:

```text
                    VOICE
                      ↓
                   SARVAM
                      ↓
               LOCAL EMBEDDING
                      ↓
                    FAISS
                      ↓
                 RAG HARNESS
                      ↓
                  GROQ LLM
                      ↓
             GROUNDING CHECK
                      ↓
                   ANSWER
```

with:

```text
Correct Retrieval
        +
Grounded Generation
        +
Robust Guardrails
        +
Measured Low Latency
```

The final benchmark should report actual:

```text
P50
P70
P100
```

rather than a single favorable run.

---

# 53. Current Project Status

```text
Project: HH Goa 2026 — Voice-Enabled RAG
Task: Task 2
Dataset: AI4Bharat MSMARCO-XI
STT: Sarvam AI
Backend: FastAPI
Frontend: Vanilla JavaScript
Embeddings: FastEmbed
Vector DB: FAISS
LLM: Groq
Deadline: August 22, 2026 — 11:59 PM
Latency Target: <200 ms
Analytics: P50 / P70 / P100
Status: Active Development
```

---

# 54. For Future AI Agents

When asked to implement a feature:

1. Identify which module owns the feature.
2. Read the relevant existing files.
3. Check the shared schemas.
4. Implement the smallest clean change.
5. Preserve async behavior.
6. Add/update tests.
7. Run the relevant tests.
8. Run a benchmark if the change affects latency.
9. Do not modify unrelated modules.
10. Explain any architectural change.
11. Update this README if the change affects project-wide usage.

When asked to optimize:

```text
Measure
 ↓
Identify bottleneck
 ↓
Change
 ↓
Measure again
 ↓
Keep only if improvement is real
```

When asked to add a dependency:

- Verify that it is necessary.
- Check whether an existing dependency already provides the functionality.
- Consider its effect on deployment size and startup time.
- Add it to `requirements.txt`.
- Document why it exists.

When asked to modify an API:

- Preserve backwards compatibility where possible.
- Update Pydantic schemas.
- Update tests.
- Update frontend callers.
- Update this README.

---

# 55. Final Principle

This is not just an LLM chatbot.

It is a:

> **Latency-constrained, voice-enabled, grounded RAG system with structured orchestration, retrieval intelligence, guardrails and measurable performance.**

Every major engineering decision should answer:

```text
Does this improve:

✓ Accuracy?
✓ Groundedness?
✓ Reliability?
✓ Latency?
✓ Safety?
```

If it improves none of these, it probably does not belong in the critical inference path.
