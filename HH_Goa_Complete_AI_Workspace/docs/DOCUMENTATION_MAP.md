# DOCUMENTATION MAP

## The two-layer strategy

The repository intentionally keeps the **complete documents** and **small routing documents**.

### Complete context

| File | Purpose | Read when |
|---|---|---|
| `README.md` | Full project specification | Requirements/major decisions/integration/submission |
| `ARCHITECTURE.md` | Full technical architecture | Architecture/integration/performance design |
| `rules/COMPLETE_GOVERNANCE_REFERENCE.md` | Full previous governance rules | Deep governance review |
| `roles/COMPLETE_ROLE_SPEC_REFERENCE.md` | Full previous role specification | Deep role review |

### Low-token context

| File | Purpose |
|---|---|
| `RULES.md` | Entry router |
| `ROLES.md` | Role router |
| `roles/ROLE1_README.md` | Role 1 compact context |
| `roles/ROLE2_README.md` | Role 2 compact context |
| `roles/ROLE3_README.md` | Role 3 compact context |
| `rules/*.md` | Conditional rules |
| `progress/*.md` | Current role history |

## Recommended ordinary task context

```text
RULES.md
→ ROLES.md
→ role README
→ role progress
→ only applicable rules
→ relevant source code/tests
```

## Recommended integration context

```text
RULES.md
→ ROLES.md
→ README.md
→ ARCHITECTURE.md
→ all progress logs
→ INTEGRATION.md
→ PERFORMANCE.md
→ source/tests
```

## Frontend design

- `DESIGN.md` — minimalist, implementation-focused UI/UX source of truth for the 22 August demo.
