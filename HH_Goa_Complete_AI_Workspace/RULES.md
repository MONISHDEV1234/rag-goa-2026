# HH Goa 2026 — AI RULES (COMPACT ROUTER)

> **Purpose:** This is the mandatory low-token entry point for every AI agent.
> It tells the agent **how to work** and **which documentation to load**.
> The big `README.md` tells the agent **what the project must build**.

## 1. FIRST ACTION

For every new project instruction:

```text
Read RULES.md first.
```

Then classify the task. Do **not** automatically read the full `README.md`, `ARCHITECTURE.md`, all role files, and all rules.

## 2. TOKEN-EFFICIENT ROUTING

### Any task
Read:

```text
RULES.md
ROLES.md
```

Then read the relevant role README and progress log.

### Role 1
Read:

```text
roles/ROLE1_README.md
progress/ROLE1_PROGRESS.md
rules/CORE.md
rules/DEVELOPMENT.md
rules/PROGRESS.md
```
Add `rules/PERFORMANCE.md` for latency work and `rules/SECURITY.md` for security/provider work.

### Role 2
Read:

```text
roles/ROLE2_README.md
progress/ROLE2_PROGRESS.md
rules/CORE.md
rules/DEVELOPMENT.md
rules/PROGRESS.md
rules/PERFORMANCE.md
```
Add `rules/SECURITY.md` for credentials/audio-data/provider work.

### Role 3
Read:

```text
roles/ROLE3_README.md
progress/ROLE3_PROGRESS.md
rules/CORE.md
rules/DEVELOPMENT.md
rules/PROGRESS.md
rules/SECURITY.md
```
Add `rules/PERFORMANCE.md` for latency work.

### Integration
Read all of:

```text
README.md
ARCHITECTURE.md
ROLES.md
progress/ROLE1_PROGRESS.md
progress/ROLE2_PROGRESS.md
progress/ROLE3_PROGRESS.md
rules/INTEGRATION.md
rules/PROGRESS.md
rules/PERFORMANCE.md
```

Read the full `README.md`/`ARCHITECTURE.md` only when the integration decision genuinely requires their complete contents.

## 3. BIG README POLICY

`README.md` is the complete master specification and remains authoritative.

Read the **full** file when:
- the user explicitly requests it;
- project-wide requirements are being reviewed;
- architecture/technology decisions are changing;
- multiple roles are being integrated;
- deployment/submission is being prepared;
- the compact docs do not contain enough information.

For small tasks, read only the relevant sections.

## 4. ACTUAL REPOSITORY IS EVIDENCE

Before editing:

```text
Inspect files → search existing implementation → inspect tests/config → then edit.
```

Never assume a feature, endpoint, dependency, benchmark, or handoff exists merely because a progress log says it should.

## 5. PROJECT SOURCE-OF-TRUTH ORDER

```text
README.md
  = project requirements

ARCHITECTURE.md
  = technical architecture

ROLES.md + role READMEs
  = ownership and role workflow

rules/*.md
  = conditional engineering governance

progress/*.md
  = historical evidence of work

source/tests/benchmarks
  = implementation evidence
```

If documentation conflicts with actual code, investigate and report the discrepancy. Do not silently invent a resolution.

## 6. CHANGE DISCIPLINE

Make the smallest justified change.

Do not:
- create duplicate implementations without checking first;
- perform unrelated refactors;
- remove instrumentation to improve reported latency;
- replace required technologies without justification;
- expose secrets;
- claim unverified results.

## 7. PROGRESS LOGGING

After meaningful work, append to the correct role progress log.

**Historical entries are immutable.**

If an existing feature changes, never rewrite its old entry. Append a new entry containing:

- previous behavior;
- change;
- reason;
- affected files;
- tests;
- benchmark results if relevant;
- integration impact;
- next step/blocker.

## 8. EVIDENCE STANDARD

Never fabricate:

```text
tests
benchmarks
latency
provider responses
deployment status
feature completion
integration status
```

Use `NOT TESTED`, `NOT MEASURED`, or `BLOCKED` when appropriate.

## 9. COMPLETION CHECK

Before reporting completion:

```text
[ ] Correct role identified
[ ] Relevant rules read
[ ] Existing code inspected
[ ] Shared contracts checked
[ ] Tests run or limitation stated
[ ] Performance measured if affected
[ ] No secrets/debug artifacts
[ ] Progress log appended
[ ] Cross-role impact documented
[ ] Claims match evidence
```

## 10. FULL REFERENCES

The previous detailed governance and role specifications are preserved at:

```text
rules/COMPLETE_GOVERNANCE_REFERENCE.md
roles/COMPLETE_ROLE_SPEC_REFERENCE.md
```

These are reference documents. Do not load them for every task.

## Frontend design

Frontend/UI tasks → read `DESIGN.md` plus the Role 2 README and applicable rules.
