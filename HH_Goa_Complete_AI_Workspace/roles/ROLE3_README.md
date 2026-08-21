# ROLE 3 README — BACKEND / RAG HARNESS / GUARDRAILS / INTEGRATION

## Mission
Build the central orchestration layer and integrate the verified work of Roles 1 and 2.

## First read
```text
RULES.md
ROLES.md
roles/ROLE3_README.md
progress/ROLE3_PROGRESS.md
rules/CORE.md
rules/DEVELOPMENT.md
rules/PROGRESS.md
rules/SECURITY.md
```

For latency work add `rules/PERFORMANCE.md`.

## Own
- FastAPI
- request orchestration
- shared Pydantic contracts
- Groq LLM integration
- structured model output
- tenacity/controlled retries
- input guardrail
- context sufficiency guardrail
- grounding/hallucination check
- missing-context refusal
- end-to-end integration

## RAG flow
```text
Transcript
  ↓
Input validation / safety
  ↓
Retrieve context
  ↓
Context sufficiency check
  ↓
Structured LLM generation
  ↓
Grounding validation
  ↓
RAGResponse
```

## Safety/reliability
- Reject or safely handle off-topic input.
- Handle unsafe/inappropriate input according to the implemented policy.
- Never invent an answer when context is insufficient.
- Retry only transient failures.
- Validate structured output with Pydantic.

## Integration protocol
Before integration read:

```text
README.md
ARCHITECTURE.md
progress/ROLE1_PROGRESS.md
progress/ROLE2_PROGRESS.md
progress/ROLE3_PROGRESS.md
rules/INTEGRATION.md
rules/PERFORMANCE.md
```

Verify actual code, not progress labels alone.

## Definition of done
- FastAPI works;
- Role 1 retrieval is connected;
- Role 2 voice/transcript flow is connected;
- LLM generation works;
- structured output validates;
- guardrails work;
- missing-context behavior works;
- end-to-end smoke tests pass;
- performance is measured where applicable;
- progress log is appended.
