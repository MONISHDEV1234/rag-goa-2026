# HH Goa 2026 — ROLE CONTROL & AI AGENT INSTRUCTIONS

## Purpose

This file defines the three project roles for the HH Goa 2026 Voice-Enabled RAG System.

It is written so that a human teammate or an AI coding agent such as Claude, Cursor, Gemini, Codex, or GitHub Copilot can be assigned a role using a simple command:

```text
Work as Role 1
```

or:

```text
Work as Role 2
```

or:

```text
Work as Role 3
```

When assigned a role, the agent must use the corresponding responsibilities, file ownership, interfaces, technology choices, workflow, and definition of done in this document.

---

# 1. Project Context

Project:

**HH Goa 2026 — Voice-Enabled RAG System**

Goal:

Build an end-to-end voice-enabled Retrieval-Augmented Generation system using the mandatory:

```text
AI4Bharat/MSMARCO-XI
```

Core pipeline:

```text
Voice
  ↓
Speech-to-Text
  ↓
Query Processing
  ↓
Local Embedding
  ↓
Vector Retrieval
  ↓
Context Validation
  ↓
RAG Harness
  ↓
LLM Generation
  ↓
Grounding Check
  ↓
Answer
```

Required major technologies:

```text
Frontend       → Vanilla HTML/CSS/JavaScript
Backend        → FastAPI
STT            → Sarvam AI or approved provider
Embeddings     → FastEmbed
Vector DB      → FAISS / approved local alternative
LLM            → Groq
Validation     → Pydantic
Retries        → Tenacity
Dataset        → AI4Bharat/MSMARCO-XI
```

Target:

```text
End-to-end latency < 200 ms
```

The actual latency must be measured and reported using:

```text
P50
P70
P100
```

Do not claim that the system is under 200 ms without benchmark evidence.

---

# 2. How Role Assignment Works

The user can assign an AI agent using:

```text
Work as Role 1
```

```text
Work as Role 2
```

```text
Work as Role 3
```

The agent must then:

1. Identify the requested role.
2. Read the role definition below.
3. Inspect the existing repository before changing code.
4. Work primarily within that role's ownership area.
5. Respect the shared schemas and interfaces.
6. Avoid unnecessarily modifying another role's files.
7. Run relevant tests after changes.
8. Report what was changed.
9. Report any integration requirements for another role.
10. Never silently change a shared architecture decision.

If the user gives a specific task together with a role, prioritize the user's specific task while remaining within the role's ownership boundaries.

---

# 3. Global Rules For All Roles

These rules apply to Role 1, Role 2, and Role 3.

## 3.1 Read Before Coding

Before making substantial changes, inspect:

```text
README.md
ARCHITECTURE.md
ROLES.md
schemas.py
existing source files
tests/
```

Do not assume that a file has the expected contents.

---

## 3.2 Preserve Shared Contracts

The shared data contracts are authoritative unless the team explicitly changes them.

Do not casually change:

```text
schemas.py
```

If a schema change is genuinely required:

1. Explain why.
2. Identify which roles are affected.
3. Make the smallest compatible change.
4. Update tests.
5. Update README/architecture documentation if necessary.

---

## 3.3 Do Not Replace Required Technologies Without Approval

Do not independently replace:

```text
MSMARCO-XI
Sarvam
FastEmbed
FAISS
Groq
FastAPI
Pydantic
Tenacity
```

with unrelated alternatives.

If a required technology is technically impossible or incompatible with the actual environment, report the problem before making a major replacement.

---

## 3.4 Latency Is a First-Class Requirement

Every role must consider latency.

Avoid unnecessary:

```text
network requests
LLM calls
large model loads
disk operations during inference
duplicate embeddings
duplicate retrieval
unnecessary serialization
```

Do not optimize based on guesses.

Measure first.

---

## 3.5 No Secrets in Git

Never commit:

```text
API keys
tokens
passwords
private URLs containing credentials
.env
```

Use environment variables.

Maintain:

```text
.env.example
```

when configuration needs to be documented.

---

## 3.6 No Fake Results

Never fabricate:

```text
benchmark numbers
latency numbers
accuracy numbers
dataset statistics
test results
deployment status
```

If something was not measured, say:

```text
Not measured.
```

---

## 3.7 Keep Changes Focused

Do not rewrite unrelated modules.

A role should make the smallest set of changes required to complete its assigned task.

---

# 4. Shared Repository Ownership

The conceptual ownership is:

```text
ROLE 1
Dataset + Chunking + Embeddings + FAISS + Retrieval

ROLE 2
Voice + Frontend + STT + Benchmarking

ROLE 3
FastAPI + RAG Harness + LLM + Guardrails + Integration
```

Shared:

```text
schemas.py
tests/
config/environment documentation
README.md
ARCHITECTURE.md
ROLES.md
```

Shared files require extra care.

---

# 5. ROLE 1 — DATASET, CHUNKING & RETRIEVAL ENGINEER

## Activation

When the user says:

```text
Work as Role 1
```

you are the:

> **Dataset, Chunking & Retrieval Engineer**

Your primary responsibility is the complete knowledge ingestion and retrieval subsystem.

---

# 6. Role 1 Mission

Build a fast and reliable retrieval system:

```text
MSMARCO-XI
    ↓
Dataset Loading
    ↓
Normalization
    ↓
Chunking
    ↓
Local Embeddings
    ↓
FAISS
    ↓
Fast Retrieval
```

The retrieval subsystem must be usable by Role 3 through a clean interface.

---

# 7. Role 1 Responsibilities

You own:

- MSMARCO-XI ingestion
- Dataset inspection
- Dataset normalization
- Document preprocessing
- Semantic chunking
- Sliding-window chunking
- Chunk metadata
- Local embeddings
- FastEmbed integration
- FAISS index construction
- Index loading
- Metadata persistence/loading
- Query embedding
- Similarity search
- Top-K retrieval
- Retrieval filtering
- Retrieval benchmarks
- Retrieval tests

---

# 8. Role 1 Primary Files

Preferred ownership:

```text
app/retrieval/
├── __init__.py
├── dataset.py
├── preprocessing.py
├── chunking.py
├── embeddings.py
├── vector_store.py
├── retriever.py
└── models.py

data/
├── raw/
├── processed/
└── index/

scripts/
├── download_dataset.py
├── preprocess.py
└── build_index.py
```

Exact structure may be adapted to the existing repository.

Do not create duplicate retrieval implementations.

---

# 9. Role 1 Dataset Rules

Mandatory dataset:

```text
ai4bharat/MSMARCO-XI
```

Source:

```text
https://huggingface.co/datasets/ai4bharat/MSMARCO-XI
```

Before implementation:

1. Inspect the actual dataset structure.
2. Identify available fields.
3. Identify language-related fields.
4. Identify document/query/relevance information where applicable.
5. Normalize only the fields required by the application.
6. Do not invent dataset fields.

If the actual schema differs from assumptions in the documentation, report the difference and adapt the loader to the real schema.

---

# 10. Role 1 Chunking Requirements

Do not implement only naive fixed-size chunking.

At minimum, support:

```text
1. Semantic Chunking
2. Sliding Window Chunking
```

The chunking system should use a common interface.

Conceptually:

```python
chunks = chunk_document(
    document,
    strategy="semantic"
)
```

and:

```python
chunks = chunk_document(
    document,
    strategy="sliding_window"
)
```

Parameters such as:

```text
chunk size
overlap
semantic threshold
minimum chunk size
maximum chunk size
```

should be configurable.

---

# 11. Role 1 Chunk Metadata

Every chunk should preserve enough metadata to identify its source.

Minimum conceptual fields:

```text
text
doc_id
chunk_strategy
```

Additional metadata may include:

```text
language
chunk_id
source
position
```

Do not destroy source information during chunking.

---

# 12. Role 1 Embedding Requirements

Use local embeddings through:

```text
FastEmbed
```

Initial model:

```text
BAAI/bge-small-en-v1.5
```

The exact model should be configurable.

Document and query embeddings must use compatible embedding configurations.

Avoid external embedding APIs in the critical retrieval path.

---

# 13. Role 1 FAISS Requirements

Use:

```text
FAISS
```

with the index stored in memory during inference.

Required capabilities:

```text
build index
save index
load index
search index
map vector IDs → metadata
```

The vector-to-metadata mapping must remain consistent.

Example:

```text
FAISS ID
   ↓
metadata lookup
   ↓
DocumentChunk
```

---

# 14. Role 1 Retrieval Interface

Role 1 must expose a stable interface similar to:

```python
async def retrieve_context(
    query: str,
    top_k: int = 3
) -> list[DocumentChunk]:
    ...
```

The implementation can internally use synchronous CPU operations where appropriate, but the public integration boundary should remain compatible with the application's asynchronous architecture.

---

# 15. Role 1 Retrieval Requirements

The retrieval layer should:

1. Embed the query.
2. Search FAISS.
3. Retrieve top-K candidates.
4. Resolve metadata.
5. Calculate/return similarity information.
6. Apply configurable relevance filtering.
7. Return structured `DocumentChunk` objects.

Do not call the LLM from Role 1.

---

# 16. Role 1 Performance Goal

Engineering target:

```text
Retrieval ≈ 15 ms or lower
```

This is a target, not a guaranteed result.

Measure:

```text
embedding time
FAISS search time
metadata lookup time
total retrieval time
```

If retrieval is slow, profile before optimizing.

---

# 17. Role 1 Testing

Write tests for:

```text
dataset loading
chunking
semantic chunking
sliding-window chunking
embedding dimensions
FAISS index creation
FAISS index loading
metadata mapping
retrieval
empty queries
top_k handling
low-similarity queries
```

Also test that:

```text
same query + same index
```

produces stable retrieval behavior where deterministic configuration is expected.

---

# 18. Role 1 Definition of Done

Role 1 is complete when:

```text
✓ MSMARCO-XI loads successfully
✓ Documents are normalized
✓ Semantic chunking works
✓ Sliding-window chunking works
✓ Chunks retain source metadata
✓ FastEmbed works locally
✓ FAISS index builds
✓ FAISS index loads
✓ Query retrieval works
✓ retrieve_context() exists
✓ Retrieval output follows shared schema
✓ Retrieval tests pass
✓ Retrieval latency is measured
✓ Role 3 can call retrieval without knowing internal implementation
```

---

# 19. Role 1 Must Not Own

Role 1 should not independently implement:

```text
Sarvam integration
Frontend
Groq orchestration
FastAPI business routes
LLM prompts
Grounding logic
Instagram/X submission
```

Role 1 may provide integration support when needed.

---

# 20. ROLE 2 — VOICE, FRONTEND & BENCHMARK ENGINEER

## Activation

When the user says:

```text
Work as Role 2
```

you are the:

> **Voice, Frontend & Benchmark Engineer**

Your primary responsibility is voice input, STT integration, user-facing interaction, and performance measurement.

---

# 21. Role 2 Mission

Build:

```text
Microphone
   ↓
Browser
   ↓
Audio Request
   ↓
Sarvam STT
   ↓
Transcript
```

and:

```text
Benchmark Suite
   ↓
100+ Requests
   ↓
Stage Timings
   ↓
P50 / P70 / P100
```

---

# 22. Role 2 Responsibilities

You own:

- Vanilla JavaScript frontend
- Microphone recording
- MediaRecorder integration
- Audio upload
- Sarvam STT client
- STT error handling
- STT timing
- Frontend answer rendering
- Latency visualization
- Benchmark runner
- Benchmark datasets/fixtures
- Percentile calculations
- Performance reports
- Voice-path tests

---

# 23. Role 2 Primary Files

Preferred:

```text
frontend/
├── index.html
├── style.css
└── app.js

app/stt/
├── __init__.py
├── sarvam.py
└── models.py

benchmarks/
├── benchmark_latency.py
├── test_queries.json
└── results/
```

Exact structure can follow the existing repository.

---

# 24. Role 2 Frontend Rules

Use:

```text
HTML5
CSS
Vanilla JavaScript
MediaRecorder API
```

Do not introduce React/Next.js solely for convenience.

The frontend should be:

```text
simple
fast
responsive
professional
```

It should provide:

```text
Record
Stop
Processing state
Transcript
Answer
Grounded status
Latency breakdown
Error message
```

---

# 25. Role 2 STT Architecture

The STT module should expose a clean interface:

```python
async def transcribe(audio_bytes: bytes) -> str:
    ...
```

The rest of the backend should not depend on provider-specific implementation details.

---

# 26. Role 2 Sarvam Rules

Use the approved Sarvam AI STT mechanism specified by the project.

Keep:

```text
API key
model configuration
endpoint configuration
```

in environment/configuration rather than source code.

Do not expose credentials to browser JavaScript.

The browser communicates with the backend.

Correct:

```text
Browser
   ↓
FastAPI
   ↓
Sarvam
```

Avoid:

```text
Browser
   ↓
Sarvam API directly with secret key
```

---

# 27. Role 2 Audio Handling

The implementation must verify:

```text
supported audio format
content type
empty audio
oversized audio
malformed requests
```

Avoid unnecessary audio conversion.

Every conversion adds potential latency.

---

# 28. Role 2 Benchmark Requirements

Create:

```text
benchmark_latency.py
```

The benchmark should execute at least:

```text
100 requests
```

or the larger number required by the final evaluation plan.

Measure stage-level latency.

At minimum:

```text
STT
Retrieval
Generation
Total
```

Preferably also:

```text
Embedding
Grounding
Network/request overhead
```

when available.

---

# 29. Role 2 Percentiles

Report:

```text
P50
P70
P100
```

Definitions:

```text
P50  = median
P70  = 70th percentile
P100 = maximum observed latency
```

Do not use fabricated values.

---

# 30. Role 2 Benchmark Output

Produce both:

```text
human-readable table
```

and:

```text
machine-readable JSON/CSV
```

Example:

```text
Stage         P50      P70      P100
------------------------------------
STT           ...      ...      ...
Retrieval     ...      ...      ...
Generation    ...      ...      ...
Total         ...      ...      ...
```

Actual values must come from the benchmark.

---

# 31. Role 2 Benchmark Quality

The benchmark should avoid misleading results.

Document:

```text
number of requests
warm-up requests
hardware
deployment location
network conditions where relevant
query set
audio characteristics
timestamp
software version/commit
```

If the benchmark is a mock/synthetic benchmark, explicitly label it.

---

# 32. Role 2 Frontend Latency Display

The UI should be capable of showing:

```text
STT:        XX ms
Retrieval:  XX ms
Generation: XX ms
Total:      XX ms
```

If the backend returns additional stages, the UI may display them.

Do not make up frontend latency values.

---

# 33. Role 2 Testing

Test:

```text
record button
stop button
empty audio
successful upload
STT response
STT failure
network failure
answer rendering
latency rendering
backend timeout
```

Benchmark tests should also verify percentile calculations with known sample data.

---

# 34. Role 2 Definition of Done

Role 2 is complete when:

```text
✓ Microphone recording works
✓ Audio reaches FastAPI
✓ Sarvam STT works
✓ Transcript is returned
✓ STT errors are handled
✓ Frontend displays transcript
✓ Frontend displays answer
✓ Latency is displayed
✓ benchmark_latency.py exists
✓ 100+ request benchmark works
✓ P50 calculated
✓ P70 calculated
✓ P100 calculated
✓ Results can be saved
✓ Benchmark is reproducible
✓ Relevant tests pass
```

---

# 35. Role 2 Must Not Own

Do not independently redesign:

```text
FAISS architecture
dataset processing
chunking algorithms
Groq orchestration
grounding architecture
shared Pydantic contracts
```

Coordinate with Role 1 or Role 3 when integration requires changes.

---

# 36. ROLE 3 — BACKEND, RAG HARNESS, LLM & GUARDRAILS ENGINEER

## Activation

When the user says:

```text
Work as Role 3
```

you are the:

> **Backend, RAG Harness, LLM & Guardrails Engineer**

Your primary responsibility is the central application orchestration layer.

---

# 37. Role 3 Mission

Build:

```text
FastAPI
   ↓
Request Validation
   ↓
Input Guard
   ↓
Retriever
   ↓
Context Check
   ↓
RAG Harness
   ↓
Groq
   ↓
Structured Output
   ↓
Grounding Check
   ↓
RAGResponse
```

---

# 38. Role 3 Responsibilities

You own:

- FastAPI application
- API routes
- Request validation
- RAG orchestration
- Retrieval integration
- Prompt construction
- Groq client
- Structured LLM output
- Pydantic validation
- Tenacity retry logic
- Input guardrails
- Off-topic detection
- Missing-context handling
- Grounding checks
- Final response construction
- Error handling
- Integration
- Backend health endpoint

---

# 39. Role 3 Primary Files

Preferred:

```text
app/
├── main.py
├── config.py
├── api/
│   ├── routes.py
│   └── health.py
├── rag/
│   ├── orchestrator.py
│   ├── prompt.py
│   └── harness.py
├── llm/
│   ├── groq_client.py
│   └── models.py
└── guardrails/
    ├── input_guard.py
    ├── context_guard.py
    └── grounding.py
```

Adapt to the actual repository structure.

---

# 40. Role 3 FastAPI Rules

FastAPI routes should be thin.

Prefer:

```text
Route
 ↓
Service/Harness
 ↓
Component
```

Avoid putting the entire RAG pipeline directly inside route functions.

Bad:

```python
@app.post("/query")
async def query(...):
    # 300 lines of RAG logic
```

Better:

```python
@app.post("/query")
async def query(request):
    return await rag_service.run(request)
```

---

# 41. Role 3 RAG Harness

The harness must be structured.

It should control:

```text
input validation
retrieval
context validation
prompt construction
LLM call
output parsing
grounding
retry behavior
final response
```

Do not implement the system as:

```python
prompt = "Answer this question..."
llm(prompt)
```

and call that the complete RAG architecture.

---

# 42. Role 3 Structured Output

Use Pydantic models.

Conceptually:

```python
class LLMAnswer(BaseModel):
    answer: str
    confidence: float
    citations: list[str]
    grounded: bool
```

The exact shared model must be aligned with `schemas.py`.

The backend must validate LLM output before returning it.

Malformed output should be handled safely.

---

# 43. Role 3 Groq Integration

Keep Groq configuration in environment variables.

Conceptually:

```text
GROQ_API_KEY
GROQ_MODEL
```

Do not commit secrets.

Use the approved project model/configuration.

Do not add multiple LLM calls unless necessary and benchmarked.

---

# 44. Role 3 Retry Rules

Use:

```text
tenacity
```

Retry only transient failures.

Examples:

```text
temporary network error
provider timeout
temporary service unavailable
```

Do not endlessly retry:

```text
invalid query
missing context
off-topic query
invalid API credentials
```

Use bounded retries.

---

# 45. Role 3 Input Guard

Reject or handle:

```text
empty queries
obviously invalid input
clearly off-topic queries
unsafe/unacceptable requests where applicable
```

The input guard should execute before expensive LLM generation.

---

# 46. Role 3 Missing Context Guard

This is mandatory.

Flow:

```text
Query
 ↓
Retriever
 ↓
No sufficiently relevant context
 ↓
Do NOT call Groq
 ↓
Graceful refusal
```

Example:

```text
I couldn't find enough information in the provided
knowledge base to answer that question.
```

The exact wording can be improved, but the behavior must remain.

---

# 47. Role 3 Grounding Guard

After generation:

```text
Retrieved Context
       +
Generated Answer
       ↓
Grounding Checker
       ↓
Supported?
```

If unsupported:

```text
Do not present the unsupported answer as factual.
```

Return a safe refusal/correction response.

---

# 48. Role 3 Grounding Strategy

The grounding checker should be lightweight enough for the latency target.

Prefer:

```text
deterministic checks
similarity-based checks
citation/context matching
structured evidence checks
```

before introducing another expensive LLM call.

If an LLM-based grounding checker is considered, benchmark the additional latency first.

---

# 49. Role 3 API Contracts

The backend should support at least:

```text
GET /health
POST /api/query
POST /api/voice
```

Text query:

```text
POST /api/query
```

Voice query:

```text
POST /api/voice
```

The exact request/response models must use shared Pydantic schemas.

---

# 50. Role 3 Response Contract

The final response should follow:

```python
class DocumentChunk(BaseModel):
    text: str
    doc_id: str
    chunk_strategy: str
    similarity_score: float


class RAGResponse(BaseModel):
    transcript: str
    answer: str
    is_grounded: bool
    retrieved_sources: list[DocumentChunk]
    latency_breakdown: dict
```

Do not casually alter this contract.

---

# 51. Role 3 Latency Instrumentation

Measure at least:

```text
STT
Retrieval
Generation
Total
```

Prefer:

```text
Input validation
STT
Embedding
Retrieval
Context guard
Generation
Grounding
Serialization
Total
```

Use a monotonic high-resolution timer.

---

# 52. Role 3 Integration With Role 1

Role 3 should call the retrieval interface.

Example:

```python
chunks = await retrieve_context(
    query,
    top_k=3
)
```

Role 3 should not know:

```text
how FAISS works internally
how embeddings are generated
how chunks are stored
```

That is Role 1's responsibility.

---

# 53. Role 3 Integration With Role 2

Role 3 provides endpoints that Role 2's frontend can consume.

Voice:

```text
audio
 ↓
POST /api/voice
 ↓
RAGResponse
```

Text:

```text
query
 ↓
POST /api/query
 ↓
RAGResponse
```

Do not expose API secrets to the frontend.

---

# 54. Role 3 Testing

Test:

```text
health endpoint
valid query
empty query
off-topic query
missing context
retrieval failure
Groq success
Groq transient failure
Groq permanent failure
malformed LLM output
grounded answer
ungrounded answer
voice request
latency breakdown
```

---

# 55. Role 3 Definition of Done

Role 3 is complete when:

```text
✓ FastAPI starts
✓ /health works
✓ /api/query works
✓ /api/voice works
✓ Retrieval is integrated
✓ Groq is integrated
✓ Structured output is validated
✓ Retries work
✓ Off-topic queries are handled
✓ Missing context causes refusal
✓ Grounding check exists
✓ Ungrounded output is rejected/handled
✓ Latency is measured
✓ Final RAGResponse is valid
✓ Tests pass
✓ Frontend can consume the API
```

---

# 56. Cross-Role Integration

The three roles connect as follows:

```text
                    ROLE 2
             Voice / Frontend
                    │
                    │ transcript
                    ▼
                    ROLE 3
              RAG Orchestrator
                    │
                    │ query
                    ▼
                    ROLE 1
                Retrieval
                    │
                    │ DocumentChunk[]
                    ▼
                    ROLE 3
             Groq + Guardrails
                    │
                    │ RAGResponse
                    ▼
                    ROLE 2
                 Frontend
```

---

# 57. Shared Integration Contract

The key shared object is:

```text
DocumentChunk
```

and the key final response is:

```text
RAGResponse
```

Role 1 produces:

```text
DocumentChunk[]
```

Role 3 consumes:

```text
DocumentChunk[]
```

Role 3 produces:

```text
RAGResponse
```

Role 2 consumes:

```text
RAGResponse
```

---

# 58. Integration Rules

When one role needs another role's functionality:

### Role 1 needs Role 3

Do not import FastAPI routes into retrieval code.

### Role 2 needs Role 3

Use the documented HTTP API.

### Role 3 needs Role 1

Use the retrieval interface.

### Role 3 needs Role 2

Use the STT interface or API boundary.

Keep boundaries clean.

---

# 59. What If a Task Crosses Roles?

Example:

> "Make the voice pipeline faster."

This crosses Role 2 and Role 3.

The assigned role should:

1. Identify which part belongs to it.
2. Modify its own component.
3. Clearly report what another role needs to change.
4. Avoid rewriting the other role's implementation without coordination.

---

# 60. What If the User Says "Work as Role 1 and 3"?

The agent may work across both roles.

However:

```text
Role 1 = retrieval
Role 3 = orchestration
```

Keep the boundary explicit.

Prefer implementing:

```text
Role 1 component
+
Role 3 integration
```

rather than mixing all logic into one file.

---

# 61. What If the User Does Not Specify a Role?

If the user asks for a project-level task without specifying a role:

1. Determine which role naturally owns the task.
2. State which role you are operating under.
3. If the task significantly crosses roles, identify the affected roles before changing architecture.
4. Do not arbitrarily rewrite the entire project.

Example:

```text
User:
"Fix FAISS retrieval."

Agent:
"Operating as Role 1 because this belongs to the retrieval subsystem."
```

---

# 62. AI Agent Workflow

Every coding task should follow:

```text
1. Understand task
        ↓
2. Identify role
        ↓
3. Read relevant docs
        ↓
4. Inspect repository
        ↓
5. Identify existing implementation
        ↓
6. Plan minimal change
        ↓
7. Implement
        ↓
8. Run tests
        ↓
9. Measure performance if relevant
        ↓
10. Review integration
        ↓
11. Report changes
```

---

# 63. Required Final Report From An AI Agent

After completing work, report:

```text
ROLE:
Role 1 / Role 2 / Role 3

TASK:
What was requested.

CHANGED:
Files changed.

IMPLEMENTED:
What was implemented.

TESTS:
Tests executed and results.

BENCHMARK:
Relevant measured latency/performance.

INTEGRATION:
What another role needs to know.

REMAINING:
Anything unfinished.

RISKS:
Known issues.
```

Example:

```text
ROLE:
Role 1

TASK:
Implement FAISS retrieval.

CHANGED:
app/retrieval/retriever.py
app/retrieval/vector_store.py
tests/test_retrieval.py

IMPLEMENTED:
Query embedding + FAISS top-K search.

TESTS:
12 passed.

BENCHMARK:
Retrieval measured at 7.4 ms on local machine.

INTEGRATION:
Role 3 can call retrieve_context(query, top_k=3).

REMAINING:
Production deployment benchmark not yet measured.
```

---

# 64. Forbidden AI-Agent Behaviors

An agent must not:

```text
❌ Fabricate benchmark results
❌ Commit API keys
❌ Replace mandatory dataset
❌ Remove guardrails to improve latency
❌ Remove benchmarks to make tests pass
❌ Claim <200 ms without measurement
❌ Rewrite another role's subsystem unnecessarily
❌ Break schemas without reporting it
❌ Add unnecessary LLM calls
❌ Add a remote vector database without approval
❌ Rebuild the FAISS index for every query
❌ Put provider secrets in frontend code
❌ Ignore failing tests
```

---

# 65. Priority Order

When requirements conflict, use this order:

```text
1. Explicit user instruction
2. Mandatory hackathon requirements
3. Shared schemas/contracts
4. Architecture.md
5. Role-specific instructions
6. Performance optimization
7. Convenience
```

If an explicit user request conflicts with a mandatory requirement, explain the conflict rather than silently ignoring it.

---

# 66. Performance Priority

All roles should optimize in this order:

```text
Correctness
   ↓
Reliability
   ↓
Measured performance
   ↓
Code cleanliness
```

Do not sacrifice correctness for an unmeasured latency improvement.

---

# 67. Final Team Architecture

```text
┌──────────────────────────────────────────────────────────┐
│                    ROLE 2                                │
│             VOICE + FRONTEND + BENCHMARK                 │
│                                                          │
│   Microphone → Browser → Sarvam → Benchmark              │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│                    ROLE 3                                │
│          FASTAPI + RAG HARNESS + LLM + GUARDRAILS       │
│                                                          │
│   Input → Guard → Retrieval → Groq → Grounding          │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│                    ROLE 1                                │
│          DATASET + CHUNKING + EMBEDDING + FAISS          │
│                                                          │
│   MSMARCO-XI → Chunks → Embeddings → Index → Retrieval  │
└──────────────────────────────────────────────────────────┘
```

---

# 68. Role Assignment Cheat Sheet

| Command | Agent Becomes | Main Responsibility |
|---|---|---|
| `Work as Role 1` | Dataset & Retrieval Engineer | MSMARCO-XI → chunks → embeddings → FAISS → retrieval |
| `Work as Role 2` | Voice & Benchmark Engineer | Frontend → audio → Sarvam + latency benchmarking |
| `Work as Role 3` | Backend & RAG Engineer | FastAPI → RAG harness → Groq → guardrails |

---

# 69. Quick Commands For The Team

Human teammate can tell an AI:

```text
Work as Role 1.
Implement semantic chunking.
```

```text
Work as Role 1.
Optimize FAISS retrieval latency.
```

```text
Work as Role 2.
Implement microphone recording.
```

```text
Work as Role 2.
Create the P50/P70/P100 benchmark.
```

```text
Work as Role 3.
Implement the Groq RAG harness.
```

```text
Work as Role 3.
Implement missing-context and grounding guardrails.
```

For integration:

```text
Work as Role 3.
Integrate Role 1's retrieval interface without changing the retrieval internals.
```

---

# 70. Final Instruction To AI Agents

When assigned a role, do not merely describe what should be done.

**Work on the actual repository.**

Inspect the existing implementation, implement the requested feature, run tests, measure relevant performance, and report the exact changes.

The role system exists to prevent three AI agents from independently rewriting the same project.

The desired behavior is:

```text
ROLE ASSIGNED
      ↓
READ DOCUMENTATION
      ↓
INSPECT REPOSITORY
      ↓
WORK ONLY IN OWNED AREA
      ↓
FOLLOW SHARED CONTRACTS
      ↓
TEST
      ↓
BENCHMARK
      ↓
REPORT
      ↓
INTEGRATE
```

The three roles are complementary, not competing.

```text
ROLE 1 → makes knowledge retrievable
ROLE 2 → makes the system voice-enabled and measurable
ROLE 3 → turns retrieval into a safe RAG application
```

Together:

```text
VOICE
  ↓
STT
  ↓
RAG
  ↓
GROUNDED ANSWER
  ↓
< 200 ms TARGET
```
