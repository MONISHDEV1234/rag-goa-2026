# ROLE 1 README — DATASET / CHUNKING / RETRIEVAL

## Mission
Build the knowledge ingestion and retrieval subsystem.

## First read
```text
RULES.md
ROLES.md
roles/ROLE1_README.md
progress/ROLE1_PROGRESS.md
rules/CORE.md
rules/DEVELOPMENT.md
rules/PROGRESS.md
```

For latency work add `rules/PERFORMANCE.md`.
For provider/security work add `rules/SECURITY.md`.

## Own
- AI4Bharat/MSMARCO-XI ingestion and normalization
- advanced chunking
- semantic chunking
- sliding-window overlap
- metadata-aware strategy where justified
- local FastEmbed embeddings
- in-memory FAISS index
- retrieval API
- retrieval tests and benchmarks

## Required interface

```python
async def retrieve_context(query: str, top_k: int = 3):
    ...
```

Return objects compatible with the shared `DocumentChunk` contract in the master README.

## Constraints
- Do not replace MSMARCO-XI.
- Do not submit only one naive fixed-size chunking strategy.
- Build/load indexes outside the normal request hot path.
- Avoid duplicate query embeddings/retrieval.
- Measure retrieval latency; never invent it.
- Avoid modifying Role 2/3 internals unless integration requires it.

## Definition of done
- Dataset ingestion works.
- Chunking strategies work.
- Embeddings work.
- Index builds/loads correctly.
- Retrieval works through the agreed interface.
- Relevant tests pass.
- Relevant benchmark exists.
- Progress log is appended.
- Handoff information is documented.

## Handoff
Tell Role 3 exactly:
- import/function path;
- input/output shape;
- initialization requirements;
- configuration;
- error behavior;
- measured latency;
- test status.
