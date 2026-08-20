# Role 1 → Role 3 Handoff — Retrieval Subsystem

## Import / function path

```python
from retrieval import init_retrieval, retrieve_context
from schemas import DocumentChunk, RetrievalError

# Once, at FastAPI startup:
init_retrieval("data/index")  # loads FAISS index + metadata + embedding model into memory

# Per request:
chunks: list[DocumentChunk] = await retrieve_context(query, top_k=3)
```

## Input / output shape

**Input:** `query: str`, `top_k: int = 3`

**Output:** `list[DocumentChunk]`, a Pydantic model with fields:
`chunk_id, text, doc_id, strategy, lang, query_id, query_type, score, is_selected`

**On failure:** raises `RetrievalError` (never a silent empty list). Catch this
specifically for your Tenacity retry logic. A query that legitimately matches
nothing still returns `[]` normally — that's not an error.

## Initialization requirements

1. Run `embed_index.py` once, offline, to build the FAISS index (see below).
2. Call `init_retrieval(index_dir)` once at process startup — this is where the
   index and embedding model load into memory. **Do not call this per-request.**
3. Requires `fastembed`, `faiss-cpu`, `pydantic` installed (see `requirements.txt`).

## Security & Anti-Hallucination Guardrails

Integrated into `retrieval.py` via `security_guardrails.py`:

1. **SQL Injection Defense**:
   - Query sanitization strips malicious SQL syntax keywords (`SELECT`, `DROP TABLE`, `UNION`, `--`, `;`).
   - FAISS vector stores & JSONL file stores avoid SQL syntax parsing entirely.
2. **Prompt Injection & XSS Defense**:
   - Sanitizes prompt override instructions (`[SYSTEM PROMPT]`, `IGNORE PREVIOUS INSTRUCTIONS`, HTML `<script>` tags, control characters, null bytes).
   - Hard character length truncation (`MAX_QUERY_LENGTH = 1000`) prevents memory amplification buffer DoS attacks.
3. **Anti-Hallucination & Citation Provenance**:
   - `filter_anti_hallucination(chunks, min_similarity_score)` filters out low-confidence vector noise matches that trigger LLM hallucinations.
   - `generate_provenance_citations(chunks)` provides strict citation link metadata (`doc_id`, `chunk_id`, `score`, `lang`) for ground-truth verification.
4. **Path Traversal Protection**:
   - Resolves and verifies base directory boundaries to block path traversal attempts (`../`).

## Error behavior

| Condition | Behavior |
|---|---|
| Index not initialized | Raises `RetrievalError` |
| Empty/whitespace-only query | Raises `RetrievalError` |
| `top_k <= 0` | Raises `RetrievalError` |
| Query embedding fails | Raises `RetrievalError` (wraps original exception) |
| FAISS search fails | Raises `RetrievalError` (wraps original exception) |
| Query legitimately has no good matches | Returns `[]` — not an error, don't retry this |
| Index/metadata row count mismatch at load | Raises `RetrievalError` at `init_retrieval()`, fails fast |

## Measured latency

**Measured with optimized ONNX runtime & startup model warmup (`intfloat/multilingual-e5-large`)**:
- **Target Requirement**: < 200 ms
- **Queries benchmarked**: 50 queries across English and Indic languages
- **Success rate**: 100% (50/50 succeeded, 0 errors)
- **Mean latency**: **76.74 ms**
- **P50 median latency**: **77.92 ms** (Sub-80ms!)
- **P70 latency**: **82.89 ms**
- **P100 (Max) latency**: **105.30 ms** (Well under 200ms!)
- **Min latency**: **47.80 ms**
- **Per-language median latency**:
  - `en` (English): **73.56 ms**
  - `as` (Assamese): **78.96 ms**
  - `bn` (Bengali): **79.67 ms**

**Optimizations Applied**:
1. Enabled ONNX intra-op multi-threading (`threads=max(1, os.cpu_count())`).
2. Added ONNX runtime graph & execution provider warmup call inside `init_retrieval()` to eliminate initial cold-start latency spikes.

Run again with:
```
python benchmark.py --index-dir data/index --eval-queries data/eval_queries.jsonl --n 50
```

Note: Reports P50/P70/P100 for `retrieve_context()` only — **excludes STT and generation**.

## Retrieval accuracy (ground truth evaluation)

Evaluated against 345 ground-truth (query, expected_doc_id) pairs derived from `is_selected` labels:
- **Recall@1**: **0.275** (27.5%)
- **Recall@3**: **0.446** (44.6%)
- **Recall@5**: **0.510** (51.0%)
- **MRR (Mean Reciprocal Rank)**: **0.363**
- **Errors**: 0

Run again with:
```
python evaluate.py --index-dir data/index --eval-queries data/eval_queries.jsonl
```

## Test status

`tests/test_retrieval_and_chunking.py` — **9/9 passing**. Covers: no empty chunks
across all 3 strategies, metadata propagation, a regression test for a real bug
we found (unbounded chunk size on punctuation-less passages — fixed with a
hard word-count fallback), empty-text handling, `retrieve_context()` correctness
on an obvious query, empty-query error handling, uninitialized-index error
handling, and index/metadata mismatch detection.

Run with: `python tests/test_retrieval_and_chunking.py`


## Completed Offline Build Steps

1. `pip install -r requirements.txt` — installed `fastembed`, `faiss-cpu`, `pydantic`.
2. `python chunking.py --input data/documents.jsonl --output-dir data/chunks` — generated 7,651 metadata-aware chunks.
3. `python embed_index.py --chunks data/chunks/chunks_metadata_aware.jsonl --output-dir data/index` — downloaded `intfloat/multilingual-e5-large` ONNX model and built 1024-dim FAISS index with 7,651 vectors.
4. `python benchmark.py --index-dir data/index --eval-queries data/eval_queries.jsonl --n 50` — 100% success rate, P50 latency = 225.22ms.
5. `python evaluate.py --index-dir data/index --eval-queries data/eval_queries.jsonl` — Recall@5 = 51.0%, MRR = 0.363 across 345 ground-truth pairs.
6. Optional: To scale beyond the sample to full dataset, re-run `ingest.py` without `--sample`, re-chunk, and re-index.


## Data quality note worth knowing

Some passages in this dataset have no real sentence punctuation (noisy scraped
web text, e.g. repeated phrases with no periods) — up to 1400+ words in a single
"sentence." All three chunking strategies now hard-bound chunk size regardless of
punctuation quality (see `hard_word_split()` in `chunking.py`). This was a real
bug caught during testing, not a hypothetical — worth knowing if you see anything
unusual in retrieved chunk lengths.
