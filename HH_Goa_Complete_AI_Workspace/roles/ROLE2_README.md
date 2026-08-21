# ROLE 2 README — VOICE / STT / FRONTEND / BENCHMARKING

## Mission
Build the voice interaction layer and trustworthy latency analytics.

## First read
```text
RULES.md
ROLES.md
roles/ROLE2_README.md
progress/ROLE2_PROGRESS.md
rules/CORE.md
rules/DEVELOPMENT.md
rules/PROGRESS.md
rules/PERFORMANCE.md
```

For credentials/audio/provider work add `rules/SECURITY.md`.

## Own
- vanilla HTML/CSS/JavaScript frontend
- MediaRecorder/audio capture
- selected STT provider integration
- transcript flow
- frontend timing instrumentation
- benchmark harness
- P50/P70/P100 reporting

## STT
Use the project-selected provider: **Sarvam AI** unless the team explicitly changes the decision to ElevenLabs.

Never expose provider credentials in browser code.

## Benchmark
Use a reasonable suite; the project plan targets at least 100 test queries.

Measure separately where possible:

```text
STT
Retrieval
Generation
Total
```

Report:

```text
P50
P70
P100
```

Distinguish real provider tests from mocks/synthetic tests.

## Constraints
- Do not replace the dataset/retrieval architecture.
- Do not remove timing instrumentation.
- Do not fabricate latency.
- Do not optimize by deleting required guardrails.
- Avoid modifying Role 1/3 internals unless integration requires it.

## Definition of done
- microphone flow works;
- STT works;
- transcript reaches backend correctly;
- benchmark is repeatable;
- percentile calculations are correct;
- tests pass or limitations are recorded;
- progress log is appended;
- handoff details are documented.

## Design

For frontend work, `DESIGN.md` is the design source of truth. Follow it without loading the full project README unless the task requires it.
