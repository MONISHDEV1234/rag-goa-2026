# HH Goa 2026 — Voice-Enabled RAG Architecture

## 1. Purpose

This document defines the technical architecture for the HH Goa 2026 Task 2 Voice-Enabled RAG system.

The architecture is designed around five primary requirements:

1. Use the mandatory **AI4Bharat MSMARCO-XI** dataset.
2. Use **Sarvam AI** for speech-to-text.
3. Perform retrieval using locally generated embeddings and an in-memory FAISS index.
4. Use a structured RAG harness with retries and guardrails.
5. Target an end-to-end latency of **under 200 ms**, while reporting actual P50, P70 and P100 measurements.

This document is intended for:

- The three human team members
- Claude
- Cursor
- Gemini
- Codex
- GitHub Copilot
- Other AI coding agents

---

# 2. High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│                           USER / BROWSER                            │
│                                                                     │
│                 Microphone → Voice Input                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                │ Audio
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       VANILLA JS FRONTEND                           │
│                                                                     │
│  • MediaRecorder API                                                │
│  • Record / Stop                                                     │
│  • Audio upload                                                      │
│  • Transcript display                                                │
│  • Answer display                                                    │
│  • Latency display                                                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                │ HTTP
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                              │
│                         API / ORCHESTRATOR                           │
│                                                                     │
│  /health                                                            │
│  /api/query                                                         │
│  /api/voice                                                         │
└───────────────┬──────────────────────┬──────────────────────────────┘
                │                      │
                │ Voice request       │ Text request
                ▼                      │
┌─────────────────────────┐            │
│       SARVAM AI         │            │
│       SPEECH-TO-TEXT    │            │
└────────────┬────────────┘            │
             │                         │
             │ Transcript              │
             └────────────┬────────────┘
                          ▼
                ┌─────────────────────┐
                │    INPUT GUARD      │
                │                     │
                │ • Validation        │
                │ • Off-topic check   │
                │ • Safety check      │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ LOCAL EMBEDDING     │
                │                     │
                │ FastEmbed           │
                │ BGE-small           │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │       FAISS         │
                │    IN-MEMORY        │
                │                     │
                │ Top-K retrieval     │
                └──────────┬──────────┘
                           │
                           │ Context
                           ▼
                ┌─────────────────────┐
                │    RAG HARNESS      │
                │                     │
                │ • Context check     │
                │ • Prompt builder    │
                │ • Tool orchestration│
                │ • Retry handling    │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │       GROQ          │
                │       LLM           │
                │                     │
                │ Structured output   │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ GROUNDING CHECKER   │
                │                     │
                │ Answer vs Context   │
                └──────────┬──────────┘
                           │
                 ┌─────────┴─────────┐
                 │                   │
             Grounded            Ungrounded
                 │                   │
                 ▼                   ▼
             ANSWER               REFUSAL
                 │                   │
                 └─────────┬─────────┘
                           ▼
                      FASTAPI RESPONSE
                           │
                           ▼
                        FRONTEND
```

---

# 3. Two Different Pipelines

The system has two logical paths.

## 3.1 Offline Knowledge Pipeline

This pipeline prepares the knowledge base.

```text
MSMARCO-XI
    ↓
Dataset Loading
    ↓
Cleaning
    ↓
Document Processing
    ↓
Chunking
    ├── Semantic Chunking
    ├── Sliding Window
    └── Metadata-Aware
    ↓
Local Embeddings
    ↓
FAISS Index
    ↓
Metadata Store
    ↓
Persisted Index
```

This pipeline is **not executed for every user request**.

---

## 3.2 Online Inference Pipeline

This pipeline handles each user request.

```text
Voice
 ↓
Sarvam STT
 ↓
Input Guard
 ↓
Query Embedding
 ↓
FAISS Search
 ↓
Context Validation
 ↓
Groq LLM
 ↓
Grounding Check
 ↓
Response
```

The online path is the path that must be optimized for the sub-200 ms target.

---

# 4. Why Offline/Online Separation Matters

The following operations are expensive and must happen before inference:

```text
Dataset download
Dataset parsing
Chunk creation
Corpus embedding
FAISS index construction
```

If these operations happen during a request, latency will become unacceptable.

Correct architecture:

```text
                    OFFLINE
                       │
              Build Knowledge Base
                       │
                       ▼
                 FAISS + Metadata
                       │
                       │ Load at startup
                       ▼
                    ONLINE
                       │
                 User Query
                       │
                       ▼
                    Retrieval
```

---

# 5. Component Architecture

## 5.1 Frontend

Technology:

```text
HTML5
CSS
Vanilla JavaScript
MediaRecorder API
```

Responsibilities:

- Request microphone permission.
- Start recording.
- Stop recording.
- Send audio to `/api/voice`.
- Display transcript.
- Display answer.
- Display grounded status.
- Display latency breakdown.
- Display errors.

The frontend should remain intentionally lightweight.

---

# 6. API Layer

Technology:

```text
FastAPI
```

Responsibilities:

- Receive requests.
- Validate request structure.
- Route voice requests.
- Route text requests.
- Call the orchestration layer.
- Return Pydantic-validated responses.
- Expose health endpoint.
- Handle API-level errors.

Endpoints:

```text
GET  /health
POST /api/query
POST /api/voice
```

The API layer should not contain dataset-processing logic.

---

# 7. Voice Pipeline

## Request

```text
Browser
  ↓
audio/webm or supported browser format
  ↓
POST /api/voice
```

## Processing

```text
Audio Bytes
    ↓
Audio validation
    ↓
Sarvam API
    ↓
Transcript
```

## Output

```text
{
  "transcript": "...",
  ...
}
```

STT should be implemented asynchronously.

Connection reuse and minimal audio conversion should be preferred to reduce latency.

---

# 8. STT Architecture

```text
┌──────────────┐
│   FastAPI    │
└──────┬───────┘
       │ audio bytes
       ▼
┌──────────────┐
│ Sarvam Client│
│   (async)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Sarvam AI   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Transcript  │
└──────────────┘
```

Interface:

```python
async def transcribe(audio_bytes: bytes) -> str:
    ...
```

The rest of the application should depend on this interface rather than directly calling provider-specific code.

---

# 9. Dataset Architecture

Mandatory dataset:

```text
AI4Bharat/MSMARCO-XI
```

Source:

https://huggingface.co/datasets/ai4bharat/MSMARCO-XI

The dataset processing module should isolate Hugging Face-specific logic.

Recommended flow:

```text
Hugging Face Dataset
        ↓
Dataset Loader
        ↓
Normalized Document Representation
        ↓
Chunker
```

This prevents the retrieval system from being tightly coupled to the raw dataset schema.

---

# 10. Document Representation

Internally, documents should be normalized into a consistent representation.

Conceptually:

```python
{
    "doc_id": "...",
    "text": "...",
    "language": "...",
    "metadata": {...}
}
```

The exact fields should follow the actual dataset structure discovered during implementation.

Do not assume fields that have not been verified from the dataset.

---

# 11. Chunking Architecture

The chunking layer should support multiple strategies through a common interface.

```text
                 Document
                    │
                    ▼
              Chunking Engine
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
      Semantic   Sliding   Metadata
      Chunking   Window    Chunking
          │         │         │
          └─────────┼─────────┘
                    ▼
               Chunk Objects
```

Each chunk should preserve:

```text
doc_id
text
chunk_strategy
metadata
```

---

# 12. Semantic Chunking

Conceptual flow:

```text
Document
 ↓
Sentence splitting
 ↓
Sentence embeddings
 ↓
Similarity calculation
 ↓
Semantic boundary detection
 ↓
Chunk formation
```

Example:

```text
Sentence A ── high similarity ── Sentence B
                                      │
                                      │ same chunk
                                      ▼
                                 Chunk 1

Sentence C ── low similarity ── Sentence D
       │                              │
       └──────── boundary ────────────┘
```

The boundary threshold should be configurable.

---

# 13. Sliding Window Chunking

Conceptual example:

```text
Sentences:

S1 S2 S3 S4 S5 S6 S7 S8

Window = 4
Overlap = 2

Chunk 1:
S1 S2 S3 S4

Chunk 2:
      S3 S4 S5 S6

Chunk 3:
            S5 S6 S7 S8
```

Advantages:

- Simple
- Predictable
- Preserves local context
- Easy to benchmark

Disadvantage:

- May split semantic units.

---

# 14. Embedding Architecture

Initial technology:

```text
FastEmbed
+
BAAI/bge-small-en-v1.5
```

Offline:

```text
Chunks
 ↓
Embedding Model
 ↓
Vectors
 ↓
FAISS
```

Online:

```text
User Query
 ↓
Same Embedding Model
 ↓
Query Vector
 ↓
FAISS
```

The document and query embedding models must be compatible.

---

# 15. Vector Store Architecture

Initial vector database:

```text
FAISS
```

Stored in memory.

Conceptual structure:

```text
FAISS Index
│
├── Vector 0 → Metadata 0
├── Vector 1 → Metadata 1
├── Vector 2 → Metadata 2
└── ...
```

The FAISS index and metadata mapping must remain synchronized.

Example:

```text
FAISS ID 42
      ↓
metadata[42]
      ↓
{
    doc_id: "...",
    text: "...",
    chunk_strategy: "semantic"
}
```

---

# 16. Retrieval Architecture

```text
Query
 ↓
Embedding
 ↓
FAISS similarity search
 ↓
Top-K candidate vectors
 ↓
Metadata lookup
 ↓
Similarity threshold
 ↓
DocumentChunk[]
```

Interface:

```python
async def retrieve_context(
    query: str,
    top_k: int = 3
) -> list[DocumentChunk]:
    ...
```

Target retrieval latency:

```text
~15 ms or lower
```

This is an engineering target and must be validated through measurements.

---

# 17. Retrieval Confidence

Top-K alone is insufficient.

Example:

```text
Query
 ↓
FAISS
 ↓
Top 3

0.91  ← strong
0.88  ← strong
0.86  ← strong
```

Likely sufficient.

Another query:

```text
0.31
0.28
0.24
```

Likely insufficient.

The exact threshold must be experimentally tuned using the actual dataset.

---

# 18. Context Selection

Do not blindly pass every retrieved document to the LLM.

Recommended flow:

```text
Top-K Retrieval
      ↓
Similarity filtering
      ↓
Remove redundant context
      ↓
Context size limit
      ↓
LLM prompt
```

This improves:

- Latency
- Prompt efficiency
- Context quality
- Generation quality

---

# 19. RAG Harness

The harness is the central orchestration layer.

```text
                QUERY
                  │
                  ▼
          ┌───────────────┐
          │ Input Guard   │
          └───────┬───────┘
                  │
                  ▼
          ┌───────────────┐
          │   Retriever   │
          └───────┬───────┘
                  │
                  ▼
        ┌───────────────────┐
        │ Context Sufficiency│
        │      Checker       │
        └─────────┬─────────┘
                  │
                  ▼
          ┌───────────────┐
          │ Prompt Builder │
          └───────┬───────┘
                  │
                  ▼
          ┌───────────────┐
          │   Groq LLM    │
          └───────┬───────┘
                  │
                  ▼
          ┌───────────────┐
          │ Pydantic Parse │
          └───────┬───────┘
                  │
                  ▼
          ┌───────────────┐
          │Grounding Check│
          └───────┬───────┘
                  │
                  ▼
               Response
```

---

# 20. Structured LLM Output

The LLM must not return uncontrolled free-form data to the backend.

Recommended structure:

```python
class LLMAnswer(BaseModel):
    answer: str
    confidence: float
    citations: list[str]
    grounded: bool
```

The actual provider response should be validated before it becomes a public API response.

---

# 21. Guardrail Architecture

Guardrails exist at multiple points.

```text
                    User Query
                        │
                        ▼
                ┌──────────────┐
                │ Input Guard  │
                └──────┬───────┘
                       │
                       ▼
                   Retrieval
                       │
                       ▼
             ┌──────────────────┐
             │ Context Sufficiency│
             └────────┬─────────┘
                      │
                      ▼
                    LLM
                      │
                      ▼
             ┌──────────────────┐
             │ Grounding Check  │
             └────────┬─────────┘
                      │
               ┌──────┴──────┐
               ▼             ▼
           Supported      Unsupported
               │             │
               ▼             ▼
            Answer         Refusal
```

---

# 22. Input Guard

The input guard should detect:

- Empty input
- Extremely malformed input
- Clearly off-topic queries
- Unsafe inputs where applicable

An off-topic query should not unnecessarily consume an LLM generation call.

---

# 23. Missing Context Guard

This is one of the most important controls.

```text
Query
 ↓
FAISS
 ↓
No sufficiently relevant result
 ↓
DO NOT CALL LLM
 ↓
Return refusal
```

Example:

```text
I couldn't find enough information in the provided
knowledge base to answer that question.
```

This prevents unsupported generation and saves latency.

---

# 24. Grounding Checker

After generation:

```text
Retrieved Context
        +
Generated Answer
        ↓
Grounding Checker
        ↓
Supported?
   /          \
 YES          NO
  ↓            ↓
Answer       Refusal
```

The checker should determine whether the answer is supported by the retrieved evidence.

The implementation should be as lightweight as possible because it is part of the online latency path.

---

# 25. Retry Architecture

Use:

```text
tenacity
```

Conceptually:

```text
External API
     │
     ▼
   Request
     │
 ┌───┴────┐
 │        │
Success  Transient Failure
 │        │
 ▼        ▼
Return   Retry
           │
       Backoff
           │
       Retry Limit
           │
           ▼
         Error
```

Only transient errors should be retried.

Do not retry:

- Invalid user input
- Guardrail refusal
- Missing context
- Permanent authentication errors
- Invalid structured output indefinitely

---

# 26. External Services

The architecture has two external network dependencies:

```text
Sarvam AI
Groq
```

This is important for latency.

```text
Browser
   │
   ▼
FastAPI
   │
   ├──────────────► Sarvam
   │
   └──────────────► Groq
```

Everything else in the critical retrieval path should remain local where practical.

---

# 27. Latency Architecture

Target:

```text
TOTAL < 200 ms
```

Initial engineering budget:

```text
STT             ~60 ms
Query Embedding ~10 ms
FAISS            ~5 ms
Harness          ~10 ms
LLM              ~80 ms
Grounding        ~5 ms
Other            ~10 ms
────────────────────────
Target          ~180 ms
```

These are not guaranteed numbers.

The benchmark must report actual measurements.

---

# 28. Latency Measurement Points

Use a monotonic timer.

Measure:

```text
t0 = request received

t1 = STT completed
t2 = query embedding completed
t3 = retrieval completed
t4 = generation completed
t5 = grounding completed
t6 = response ready
```

Calculate:

```text
STT        = t1 - t0
Embedding  = t2 - t1
Retrieval  = t3 - t2
Generation = t4 - t3
Grounding  = t5 - t4
Total      = t6 - t0
```

---

# 29. Important Latency Caveat

The exact definition of the official end-to-end metric must be documented.

Possible measurements include:

### Backend processing

```text
API receives audio
 ↓
Response generated
```

### Browser-to-browser

```text
User presses record
 ↓
User receives answer
```

These are not equivalent.

The project should clearly state which metric is being reported.

---

# 30. P50 / P70 / P100

For N benchmark requests:

```text
Sort latency values
```

Then report:

```text
P50 = median
P70 = 70th percentile
P100 = maximum observed latency
```

Example:

```text
P50   142 ms
P70   161 ms
P100  194 ms
```

These numbers are examples only.

Never put example values into the final submission as actual results.

---

# 31. Benchmark Architecture

```text
                 Benchmark Runner
                       │
              ┌────────┴────────┐
              │                 │
          Query Set         Audio Set
              │                 │
              └────────┬────────┘
                       ▼
                   API Server
                       │
                       ▼
               Stage Instrumentation
                       │
                       ▼
                  Raw Results
                       │
                       ▼
             Percentile Calculator
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
            P50       P70       P100
```

Benchmark output should be saved for reproducibility.

---

# 32. Failure Architecture

Every external or internal component can fail.

```text
                  Request
                     │
                     ▼
                  FastAPI
                     │
             ┌───────┼────────┐
             ▼       ▼        ▼
           STT    Retrieval   LLM
             │       │        │
           Fail?   Fail?    Fail?
             │       │        │
             ▼       ▼        ▼
          Graceful Error Responses
```

The application must not expose:

- Stack traces
- API keys
- Internal filesystem paths
- Provider credentials
- Raw provider error payloads when inappropriate

---

# 33. Startup Architecture

At startup:

```text
FastAPI starts
     ↓
Load configuration
     ↓
Load embedding model
     ↓
Load FAISS index
     ↓
Load metadata
     ↓
Initialize reusable HTTP clients
     ↓
Health = READY
```

The system should not rebuild the complete index at every restart unless explicitly running an offline build process.

---

# 34. Memory Architecture

The major in-memory components are:

```text
Embedding Model
      +
FAISS Index
      +
Chunk Metadata
      +
HTTP Client Connections
```

Memory usage must be monitored during deployment.

If the index becomes too large, optimize the index/storage strategy rather than loading duplicate copies.

---

# 35. Security Architecture

Secrets:

```text
Environment Variables
```

Never:

```text
hardcode keys
```

Never commit:

```text
.env
```

Use:

```text
.env.example
```

for documentation.

---

# 36. CORS

During development:

```text
Frontend localhost
        ↓
FastAPI localhost
```

CORS may be required.

In production, restrict allowed origins to the deployed frontend where practical.

Avoid permanently using unrestricted:

```text
allow_origins=["*"]
```

unless there is a documented reason.

---

# 37. Deployment Architecture

Target deployment:

```text
Internet
   │
   ▼
Frontend
   │
   ▼
FastAPI
   │
   ├── Local embedding model
   ├── FAISS
   ├── Dataset metadata
   │
   ├────────► Sarvam
   │
   └────────► Groq
```

Possible hosting:

```text
Hugging Face Spaces
```

or:

```text
Render
```

The final platform should be selected based on actual:

- Startup time
- RAM
- CPU
- Network latency
- Persistent storage
- API timeout limits

---

# 38. Three-Person Architecture Ownership

## Person 1 — Retrieval

```text
Dataset
   ↓
Preprocessing
   ↓
Chunking
   ↓
Embedding
   ↓
FAISS
   ↓
Retriever
```

Primary directories:

```text
app/retrieval/
data/
scripts/
```

---

## Person 2 — Voice + Frontend + Benchmark

```text
Microphone
   ↓
Frontend
   ↓
FastAPI Voice Endpoint
   ↓
Sarvam
   ↓
Transcript

and

Benchmark
   ↓
API
   ↓
Measurements
   ↓
P50/P70/P100
```

Primary directories:

```text
app/stt/
frontend/
benchmarks/
```

---

## Person 3 — Backend + LLM + Guardrails

```text
FastAPI
   ↓
Harness
   ↓
Groq
   ↓
Structured Output
   ↓
Grounding
   ↓
Response
```

Primary directories:

```text
app/api/
app/llm/
app/guardrails/
app/main.py
```

---

# 39. Integration Boundaries

The three components communicate through stable interfaces.

```text
Person 2
   │
   │ transcript
   ▼
Person 3
   │
   │ query
   ▼
Person 1
   │
   │ DocumentChunk[]
   ▼
Person 3
   │
   │ RAGResponse
   ▼
Person 2 / Frontend
```

Shared contract:

```text
schemas.py
```

This is the main integration boundary.

---

# 40. Critical Interfaces

## STT

```python
async def transcribe(audio_bytes: bytes) -> str:
    ...
```

## Retrieval

```python
async def retrieve_context(
    query: str,
    top_k: int = 3
) -> list[DocumentChunk]:
    ...
```

## RAG

```python
async def run_rag(query: str) -> RAGResponse:
    ...
```

These interfaces allow components to be developed independently.

---

# 41. Recommended Dependency Direction

Correct:

```text
API
 ↓
Harness
 ↓
Retriever / LLM / Guardrails
 ↓
Infrastructure
```

Avoid circular dependencies such as:

```text
Retriever → API
API → Retriever
```

The lower-level modules should not depend on FastAPI route implementations.

---

# 42. Directory Dependency Model

```text
frontend
    │
    ▼
api
    │
    ▼
harness
 ┌──┼──────────────┐
 ▼  ▼              ▼
STT Retriever     LLM
        │           │
        ▼           ▼
     FAISS        Groq

Guardrails operate around
input, context and output.
```

---

# 43. Data Flow Contract

## Input

```text
Audio bytes
```

## STT output

```text
str
```

## Retrieval input

```text
query: str
```

## Retrieval output

```text
list[DocumentChunk]
```

## LLM output

```text
LLMAnswer
```

## Final output

```text
RAGResponse
```

---

# 44. Example End-to-End Request

User asks:

> "What is machine learning?"

### Step 1 — Browser

Records audio.

### Step 2 — FastAPI

Receives audio.

### Step 3 — Sarvam

Returns:

```text
"What is machine learning?"
```

### Step 4 — Input Guard

Query is valid.

### Step 5 — Embedding

Query converted to vector.

### Step 6 — FAISS

Returns top relevant chunks.

### Step 7 — Context Check

Relevant evidence exists.

### Step 8 — Groq

Generates structured answer.

### Step 9 — Grounding

Answer is checked against retrieved context.

### Step 10 — Response

```json
{
  "transcript": "What is machine learning?",
  "answer": "...",
  "is_grounded": true,
  "retrieved_sources": [],
  "latency_breakdown": {
    "stt": 0,
    "retrieval": 0,
    "generation": 0,
    "total": 0
  }
}
```

Actual values must come from instrumentation.

---

# 45. Example Missing-Context Request

```text
User
 ↓
STT
 ↓
Input Guard
 ↓
FAISS
 ↓
No relevant context
 ↓
Refusal
```

The LLM should not be called.

This improves both:

```text
Safety
+
Latency
```

---

# 46. Example LLM Failure

```text
User
 ↓
STT
 ↓
Retrieval
 ↓
Context found
 ↓
Groq failure
 ↓
Tenacity retry
 ↓
Still fails
 ↓
Graceful API error
```

Do not return an invented answer.

---

# 47. Example Grounding Failure

```text
User
 ↓
Retrieval
 ↓
Context
 ↓
Groq
 ↓
Answer
 ↓
Grounding Checker
 ↓
Unsupported
 ↓
Refusal / correction
```

The generated answer must not automatically be trusted.

---

# 48. Performance Optimization Order

Optimize in this order:

```text
1. Measure
2. Identify largest bottleneck
3. Optimize largest bottleneck
4. Measure again
5. Optimize next bottleneck
```

Typical priority:

```text
STT
 ↓
LLM
 ↓
Network
 ↓
Embedding
 ↓
Retrieval
 ↓
Grounding
```

The actual project benchmark determines the real priority.

---

# 49. Do Not Optimize Prematurely

Do not spend hours optimizing:

```text
FAISS from 4 ms → 2 ms
```

if:

```text
STT = 150 ms
```

Instead:

```text
Optimize STT
```

Performance work must be evidence-driven.

---

# 50. Architecture Decision Records

Major architecture changes should be documented.

Example:

```text
ADR-001: Use FAISS instead of remote vector DB

Decision:
Use in-memory FAISS.

Reason:
Avoid network latency during retrieval.

Tradeoff:
Memory usage increases.

Status:
Accepted
```

Recommended ADRs:

```text
ADR-001 Vector database
ADR-002 Embedding model
ADR-003 STT provider
ADR-004 LLM provider
ADR-005 Chunking strategy
ADR-006 Deployment platform
```

---

# 51. AI Agent Rules

When modifying architecture:

1. Do not replace FAISS with a remote vector database without team approval.
2. Do not replace Sarvam without team approval.
3. Do not replace the mandatory dataset.
4. Do not remove P50/P70/P100 instrumentation.
5. Do not remove guardrails.
6. Do not introduce a second LLM call without measuring its impact.
7. Do not rebuild the dataset during inference.
8. Do not move expensive processing into the request path.
9. Do not change shared schemas casually.
10. Do not claim the system is under 200 ms without benchmark evidence.

---

# 52. Final Architecture

The intended final system is:

```text
                         ┌─────────────┐
                         │    USER     │
                         └──────┬──────┘
                                │
                           Voice Input
                                │
                                ▼
                     ┌───────────────────┐
                     │ Vanilla JS        │
                     │ MediaRecorder     │
                     └─────────┬─────────┘
                               │
                               ▼
                     ┌───────────────────┐
                     │     FastAPI       │
                     └─────────┬─────────┘
                               │
                               ▼
                     ┌───────────────────┐
                     │    Sarvam STT     │
                     └─────────┬─────────┘
                               │
                           Transcript
                               │
                               ▼
                     ┌───────────────────┐
                     │    Input Guard    │
                     └─────────┬─────────┘
                               │
                               ▼
                     ┌───────────────────┐
                     │ Local FastEmbed   │
                     └─────────┬─────────┘
                               │
                               ▼
                     ┌───────────────────┐
                     │   FAISS / RAM     │
                     │  MSMARCO-XI       │
                     └─────────┬─────────┘
                               │
                         Top-K Context
                               │
                               ▼
                     ┌───────────────────┐
                     │    RAG Harness    │
                     │                   │
                     │ Context Check     │
                     │ Prompt Builder    │
                     │ Retries           │
                     │ Structured Output │
                     └─────────┬─────────┘
                               │
                               ▼
                     ┌───────────────────┐
                     │      Groq LLM     │
                     └─────────┬─────────┘
                               │
                               ▼
                     ┌───────────────────┐
                     │ Grounding Checker │
                     └─────────┬─────────┘
                               │
                         ┌─────┴─────┐
                         │           │
                     Grounded    Ungrounded
                         │           │
                         ▼           ▼
                      Answer      Refusal
                         │           │
                         └─────┬─────┘
                               ▼
                     ┌───────────────────┐
                     │   RAGResponse     │
                     │ Transcript        │
                     │ Answer            │
                     │ Sources           │
                     │ Grounded          │
                     │ Latency           │
                     └─────────┬─────────┘
                               │
                               ▼
                          FRONTEND UI
```

---

# 53. Final Architecture Goals

The architecture is successful when all of the following are true:

```text
✓ MSMARCO-XI is actually used
✓ Voice input works
✓ Sarvam STT works
✓ Multiple chunking strategies exist
✓ Embeddings run locally
✓ FAISS retrieval runs in memory
✓ RAG harness is structured
✓ Groq generation works
✓ Pydantic validates outputs
✓ Retries handle transient failures
✓ Off-topic queries are blocked
✓ Missing context causes refusal
✓ Hallucinated/unsupported answers are rejected
✓ Every stage is measured
✓ P50 is reported
✓ P70 is reported
✓ P100 is reported
✓ Actual end-to-end latency is documented
✓ Deployment works
```

---

# 54. Relationship With README.md

`README.md` is the **complete project specification**. `ARCHITECTURE.md` is the **complete technical architecture reference**.

Use the compact documentation first for ordinary work:

```text
RULES.md
  ↓
ROLES.md
  ↓
roles/ROLE*_README.md
  ↓
progress/ROLE*_PROGRESS.md
  ↓
relevant rules/*.md
```

Read the full `README.md` and full `ARCHITECTURE.md` when the task requires project-wide requirements, architecture changes, cross-role integration, deployment, or final review.

The full documents remain available and authoritative; the compact files are routing aids, not replacements.
