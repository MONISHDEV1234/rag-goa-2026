# HH Goa 2026 — QUICK INDEX

This is the small project index. It is intentionally lightweight.

## What are we building?

A voice-enabled RAG system using the mandatory AI4Bharat MSMARCO-XI dataset, approved STT, retrieval, structured generation and guardrails, with a target of under 200 ms and P50/P70/P100 analytics.

## Start here

```text
RULES.md
  ↓
ROLES.md
  ↓
Role README
  ↓
Role progress
  ↓
Relevant rules
  ↓
Code/tests
```

## Main files

| Need | Read |
|---|---|
| Complete project specification | `README.md` |
| Small AI entry router | `RULES.md` |
| Role router | `ROLES.md` |
| Full architecture | `ARCHITECTURE.md` |
| Role 1 | `roles/ROLE1_README.md` |
| Role 2 | `roles/ROLE2_README.md` |
| Role 3 | `roles/ROLE3_README.md` |
| Progress | `progress/ROLE*_PROGRESS.md` |
| Conditional rules | `rules/*.md` |
| Templates | `templates/*.md` |

## Critical requirements

- Dataset: `ai4bharat/MSMARCO-XI`
- STT: Sarvam AI or ElevenLabs; current decision: Sarvam AI
- Multiple/non-naive chunking strategies
- Target: `< 200 ms` end-to-end
- Analytics: P50 / P70 / P100
- Structured model harness
- Guardrails and groundedness checks
- Safe missing-context refusal

## Important

The big `README.md` is intentionally retained. Do not delete or replace it with this quick file. The quick file exists only to reduce context consumption during ordinary work.
