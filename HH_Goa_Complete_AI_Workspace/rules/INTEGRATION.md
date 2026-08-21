# INTEGRATION RULES

Before cross-role integration read:

```text
README.md
ARCHITECTURE.md
ROLES.md
progress/ROLE1_PROGRESS.md
progress/ROLE2_PROGRESS.md
progress/ROLE3_PROGRESS.md
```

Verify actual code, interfaces and tests.

Check:
- shared Pydantic schemas;
- request/response shapes;
- initialization order;
- errors/timeouts;
- environment configuration;
- dependency compatibility;
- frontend/backend compatibility;
- latency instrumentation;
- guardrail behavior.

Do not claim integration complete from unit tests alone. Run an end-to-end smoke test and benchmark the integrated path where possible.

If a shared interface must change, document the reason and impact before/with the change.
