# PERFORMANCE RULES

Measure before optimizing.

Required analytics:
- P50
- P70
- P100

Measure relevant stages such as:
- STT
- embedding
- retrieval
- generation
- total

Distinguish cold/warm behavior when relevant.

Never:
- fabricate numbers;
- discard slow samples without documenting the rule;
- remove required guardrails merely to lower latency;
- benchmark only the fastest run and call it representative.

When optimizing:

```text
Measure → identify bottleneck → change → measure again → keep only if justified
```
