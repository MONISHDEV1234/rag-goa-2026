# HH Goa 2026 — AI WORK RULES & PROJECT GOVERNANCE

> **This file is mandatory for every AI agent working on this repository.**
>
> Before doing any work, an AI agent MUST read this file.
> After reading it, the agent MUST read `README.md`.
> The `README.md` is the primary source of truth for what the project must build.
>
> These rules govern **how** the AI works. The README governs **what** the project is supposed to be.

---

# 1. PRIME DIRECTIVE

The AI must behave like a disciplined engineering teammate, not an uncontrolled code generator.

Every task must follow:

```text
RECEIVE INSTRUCTION
        ↓
READ RULES.md
        ↓
READ README.md
        ↓
IDENTIFY ROLE
        ↓
READ RELEVANT PROGRESS LOGS
        ↓
INSPECT CURRENT REPOSITORY
        ↓
PLAN
        ↓
IMPLEMENT
        ↓
TEST
        ↓
VERIFY
        ↓
UPDATE PROGRESS LOG
        ↓
REPORT
```

Never skip the rules-reading step.

---

# 2. MANDATORY FIRST ACTION AFTER EVERY NEW INSTRUCTION

Whenever an AI receives a new instruction, the first project action MUST be:

```text
Read RULES.md
```

Then:

```text
Read README.md
```

Only after both have been read may the AI:

```text
inspect code
edit files
create files
delete files
run migrations
change configuration
install dependencies
```

This applies even if:

- the AI worked on the repository earlier;
- the task looks trivial;
- the AI already "remembers" the rules;
- the user asks for a quick fix;
- the instruction is only one sentence.

The AI must not rely on memory instead of reading the current files.

---

# 3. SOURCE-OF-TRUTH POLICY

## 3.1 README Is the Project Source of Truth

The project's intended requirements must come from:

```text
README.md
```

The AI must follow the README when deciding:

- project goals;
- required technologies;
- required dataset;
- required functionality;
- required deliverables;
- role responsibilities;
- constraints;
- submission requirements;
- performance targets;
- required integrations.

Do not silently replace requirements with personal preferences.

---

# 3.2 RULES.md Governs AI Behavior

`RULES.md` does not redefine the product.

It defines how an AI is allowed to work on the product.

Therefore:

```text
README.md
    ↓
What to build

RULES.md
    ↓
How the AI must work
```

If a project requirement is unclear, the AI must not invent a major requirement.

---

# 3.3 Other Documentation

Files such as:

```text
ARCHITECTURE.md
ROLES.md
PROGRESS.md
```

are working documentation.

They help the AI understand:

- architecture;
- ownership;
- current implementation state;
- previous decisions;
- completed work;
- remaining work.

They must not silently override the README.

If these documents conflict with the README:

1. Stop the affected implementation.
2. Identify the conflict.
3. Prefer the README for project requirements.
4. Report the conflict to the user/team.
5. Update documentation only after the intended decision is clear.

---

# 4. NEVER ASSUME CURRENT STATE

Before changing code, inspect the actual repository.

Do not assume:

```text
a file exists
a function exists
a dependency is installed
an endpoint works
a feature is complete
a benchmark passed
another teammate finished their task
```

Use evidence from:

```text
source code
tests
configuration
progress logs
actual command output
actual benchmark output
```

Statements such as:

> "This should already work."

are not evidence.

---

# 5. ROLE IDENTIFICATION

The project has three primary roles.

```text
ROLE 1
Dataset + Chunking + Embeddings + FAISS + Retrieval

ROLE 2
Voice + Frontend + STT + Benchmarking

ROLE 3
FastAPI + RAG Harness + LLM + Guardrails + Integration
```

If the user explicitly says:

```text
Work as Role 1
```

```text
Work as Role 2
```

```text
Work as Role 3
```

the AI MUST follow the corresponding responsibilities in:

```text
ROLES.md
```

However, the implementation requirements remain governed by:

```text
README.md
```

---

# 6. DO NOT CROSS ROLE BOUNDARIES CARELESSLY

An AI must not rewrite another role's subsystem simply because doing so appears easier.

For example:

### Role 1 should not casually rewrite:

```text
FastAPI
Groq
frontend
Sarvam integration
```

### Role 2 should not casually rewrite:

```text
FAISS
dataset ingestion
chunking
LLM orchestration
```

### Role 3 should not casually rewrite:

```text
dataset pipeline
chunking algorithms
frontend implementation
```

If cross-role work is genuinely required:

1. Identify the dependency.
2. Check the relevant progress logs.
3. Make the smallest necessary integration change.
4. Record the change in the progress log.
5. Clearly report the cross-role modification.

---

# 7. PROGRESS LOGBOOK — MANDATORY

Every role MUST maintain its own progress log.

Use:

```text
progress/
├── ROLE1_PROGRESS.md
├── ROLE2_PROGRESS.md
└── ROLE3_PROGRESS.md
```

If the repository already has a different progress-log structure, follow the existing structure rather than creating duplicates.

---

# 8. WHY PROGRESS LOGS EXIST

The progress logs are the project's engineering memory.

They prevent:

```text
duplicate work
lost decisions
conflicting implementations
repeated debugging
incorrect assumptions
unfinished tasks being treated as complete
```

An AI must treat progress logs as evidence of previous work, but it must still verify important claims against the repository.

---

# 9. CREATE THE PROGRESS LOG IF IT DOES NOT EXIST

When an AI begins work as a role and that role's progress file does not exist:

Create it.

For example:

```text
progress/ROLE1_PROGRESS.md
```

Do not wait until the end of the project.

---

# 10. PROGRESS LOG FORMAT

Each role's progress file should use a consistent structure.

Example:

```markdown
# Role 1 Progress Log

## Current Status

Status: IN PROGRESS

Last Updated:
2026-08-20

Current Focus:
FAISS retrieval optimization

---

## Completed Work

- [x] Dataset loader
- [x] Dataset normalization
- [x] Sliding-window chunking
- [ ] Semantic chunking
- [ ] Retrieval benchmark

---

## Current Task

Implement semantic chunking.

---

## Change Log

### 2026-08-20 — Entry 001

Task:
Implement dataset loader.

Changed:
- app/retrieval/dataset.py

Implemented:
- Dataset loading
- Basic normalization

Tests:
- 8 passed

Benchmark:
- Not measured

Issues:
- None

Dependencies:
- None

Next:
- Implement semantic chunking

---

## Known Issues

- None

---

## Dependencies / Blockers

- None

---

## Integration Notes

Role 3 can consume:
`retrieve_context(query, top_k=3)`

---

## Next Tasks

1. Implement semantic chunking
2. Add tests
3. Benchmark retrieval
```

---

# 11. LOG AFTER EVERY MEANINGFUL CHANGE

After every meaningful code/configuration/documentation change, update the appropriate progress log.

Examples:

```text
implemented a feature
fixed a bug
changed an API
changed a schema
changed a dependency
changed chunking behavior
changed a prompt
changed a guardrail
changed benchmark logic
changed configuration
changed deployment behavior
```

The log should be updated before the AI finishes the task.

---

# 12. DO NOT LOG EVERY CHARACTER EDIT

The purpose is an engineering log, not an editor history.

Do not create entries such as:

```text
Changed one comma.
Changed one variable name.
```

unless that tiny change materially affects behavior.

Group related changes into one meaningful log entry.

---

# 13. NEVER DELETE HISTORY

Do not rewrite progress logs as though previous work never happened.

Prefer:

```text
Change Log
Entry 001
Entry 002
Entry 003
```

If something is later reverted:

```text
Entry 009:
Reverted Entry 007 because it caused X.
```

Preserve the history.

---

# 14. PROGRESS STATUS VALUES

Use clear statuses:

```text
NOT STARTED
IN PROGRESS
BLOCKED
READY FOR INTEGRATION
INTEGRATED
VERIFIED
DONE
```

Do not mark work:

```text
DONE
```

unless it has actually been implemented and verified.

---

# 15. DEFINITION OF "DONE"

A task is NOT done merely because code was written.

A task is done only when applicable:

```text
✓ Implementation exists
✓ Relevant tests pass
✓ No known critical errors remain
✓ Integration boundary works
✓ Required documentation is updated
✓ Progress log is updated
```

For performance tasks:

```text
✓ Benchmark was actually executed
✓ Results were recorded
```

---

# 16. NO FALSE COMPLETION

Never write:

```text
DONE
VERIFIED
WORKING
<200 ms
PRODUCTION READY
```

without evidence.

Instead use:

```text
IMPLEMENTED — verification pending
```

or:

```text
IMPLEMENTED — local tests pass
```

or:

```text
BENCHMARKED — P50 84 ms, P70 101 ms, P100 176 ms
```

Use exact evidence when available.

---

# 17. NO FABRICATED PERFORMANCE

This project has a major latency requirement.

The AI MUST NOT fabricate:

```text
P50
P70
P100
TTFT
STT latency
retrieval latency
generation latency
total latency
```

If the benchmark has not been executed:

```text
Not measured.
```

If it was measured under a specific environment, record that environment.

---

# 18. UNDER-200-MS CLAIM RULE

The AI must never say:

> "The system is under 200 ms."

unless actual benchmark evidence supports the statement.

Instead distinguish:

```text
Target:
< 200 ms

Measured:
XXX ms

Environment:
...

Sample size:
...

Percentiles:
P50 ...
P70 ...
P100 ...
```

A target is not a result.

---

# 19. TEST BEFORE CLAIMING SUCCESS

After modifying code, run the smallest relevant test suite.

Examples:

```text
unit tests
integration tests
API tests
retrieval tests
frontend checks
benchmark scripts
```

If tests cannot be run:

Explain why.

Never pretend they passed.

---

# 20. PRESERVE A WORKING BASELINE

Before large changes:

1. Inspect current state.
2. Identify whether tests currently pass.
3. Make focused changes.
4. Re-run relevant tests.

Avoid turning a working subsystem into an untraceable state.

---

# 21. SMALL, REVERSIBLE CHANGES

Prefer small changes.

Instead of:

```text
rewrite the entire backend
```

prefer:

```text
fix the retrieval interface
```

then:

```text
test
```

then:

```text
integrate
```

This makes debugging and collaboration easier.

---

# 22. CHECK FOR EXISTING IMPLEMENTATION FIRST

Before creating a new:

```text
file
class
function
endpoint
utility
service
configuration
```

search the repository for an existing implementation.

Do not create:

```text
retriever.py
retriever_v2.py
retriever_final.py
retriever_new.py
```

when one retriever should exist.

---

# 23. NO DUPLICATE IMPLEMENTATIONS

If an equivalent component already exists:

```text
reuse it
extend it
refactor it carefully
```

Do not create a second implementation unless there is a documented architectural reason.

---

# 24. DEPENDENCY DISCIPLINE

Before adding a dependency:

1. Check whether an existing dependency can solve the problem.
2. Check whether the dependency is necessary.
3. Consider startup and runtime cost.
4. Consider deployment compatibility.
5. Add it only if justified.
6. Update dependency files.
7. Update the progress log.

Do not install random packages just to make an error disappear.

---

# 25. ENVIRONMENT AND SECRETS

Never put secrets into:

```text
.py
.js
.html
.md
.ipynb
```

or any tracked source file.

Use environment variables.

Never commit:

```text
.env
```

if it contains secrets.

Maintain:

```text
.env.example
```

with placeholder values when necessary.

---

# 26. DO NOT EXPOSE API KEYS TO THE FRONTEND

The browser must never receive:

```text
SARVAM_API_KEY
GROQ_API_KEY
```

or other private credentials.

Use:

```text
Browser
   ↓
FastAPI
   ↓
Provider
```

---

# 27. ERROR HANDLING

Errors must be handled deliberately.

Do not hide errors with:

```python
except Exception:
    pass
```

Avoid swallowing exceptions.

Errors should provide enough information for debugging without leaking secrets.

---

# 28. RETRIES MUST BE SAFE

Retries should be used only where appropriate.

Do not retry:

```text
invalid input
missing context
off-topic query
authentication failure
invalid configuration
```

Retry transient failures only.

Avoid infinite retries.

---

# 29. DO NOT REMOVE SAFETY FOR SPEED

The latency target does not justify removing:

```text
input validation
missing-context handling
grounding checks
structured output validation
```

If a guardrail is too slow:

1. Measure it.
2. Identify the bottleneck.
3. Optimize it.
4. Benchmark again.

Do not silently delete it.

---

# 30. DATA INTEGRITY

Never silently modify or fabricate the required dataset.

For MSMARCO-XI:

```text
inspect actual schema
preserve source identity
preserve useful metadata
document transformations
```

Do not claim dataset properties that were not verified.

---

# 31. NO HALLUCINATED DOCUMENTATION

Documentation must describe the actual implementation.

Do not document:

```text
features that do not exist
benchmarks that were not run
endpoints that do not exist
models that are not configured
deployment that has not happened
```

If something is planned:

```text
Planned
```

If implemented:

```text
Implemented
```

If tested:

```text
Verified
```

---

# 32. INTEGRATION GATE — MANDATORY

Before integrating work across roles, the AI MUST inspect:

```text
progress/ROLE1_PROGRESS.md
progress/ROLE2_PROGRESS.md
progress/ROLE3_PROGRESS.md
```

The purpose is to determine:

```text
What is complete?
What is still in progress?
What is blocked?
What interfaces exist?
What assumptions were made?
What remains?
```

---

# 33. INTEGRATION MUST NOT BE BASED ONLY ON "DONE"

A progress file saying:

```text
DONE
```

is useful but not sufficient evidence.

Before integration, verify:

```text
code exists
interface exists
tests pass
actual behavior works
```

Progress logs tell the AI what to inspect.

The repository provides final evidence.

---

# 34. INTEGRATION READINESS CHECK

Before integrating Role 1 + Role 2 + Role 3, inspect each progress file and produce an internal checklist:

```text
Role 1:
[ ] Dataset ready
[ ] Chunking ready
[ ] Embedding ready
[ ] FAISS ready
[ ] Retrieval interface ready
[ ] Tests pass

Role 2:
[ ] Frontend ready
[ ] Audio capture ready
[ ] STT ready
[ ] API connection ready
[ ] Benchmark ready

Role 3:
[ ] FastAPI ready
[ ] RAG harness ready
[ ] Groq ready
[ ] Guardrails ready
[ ] Response schema ready
```

Only then perform full integration.

---

# 35. INTEGRATION ORDER

Prefer this order:

```text
ROLE 1
Retrieval
   ↓
ROLE 3
Backend/RAG
   ↓
ROLE 2
Frontend/Voice
   ↓
FULL SYSTEM
   ↓
BENCHMARK
```

This makes failures easier to isolate.

---

# 36. INTEGRATION CONTRACT CHECK

Before connecting components, verify:

```text
input type
output type
schema
error behavior
timeout behavior
latency measurement
configuration
```

Do not integrate based on assumptions.

---

# 37. SHARED SCHEMA PROTECTION

If a shared schema changes:

```text
schemas.py
```

the AI must:

1. Identify all consumers.
2. Inspect all role progress logs.
3. Update affected implementations.
4. Run relevant tests.
5. Record the change.
6. Report the compatibility impact.

Do not make silent breaking schema changes.

---

# 38. NO "FIX IT LATER" INTEGRATION

Do not knowingly integrate:

```text
broken interface
failing tests
missing dependency
unverified response format
placeholder logic
fake benchmark
```

If the integration must proceed despite a known limitation, explicitly document it as:

```text
BLOCKED
KNOWN LIMITATION
TEMPORARY
```

---

# 39. BLOCKER RULE

If the AI cannot safely continue:

Do not guess.

Mark the relevant progress entry:

```text
Status: BLOCKED
```

Include:

```text
Blocker:
Why it blocks work:
Evidence:
What is needed:
Which role/user can resolve it:
```

---

# 40. ASK ONLY NECESSARY QUESTIONS

The AI should make reasonable engineering decisions independently when the README and repository provide enough information.

Do not ask the user about trivial implementation details.

Ask when:

```text
requirements genuinely conflict
a destructive action is required
a secret/credential is needed
a major architecture decision is ambiguous
two valid interpretations materially change the system
```

---

# 41. NO DESTRUCTIVE ACTION WITHOUT WARNING

Do not delete or overwrite major project components without understanding their purpose.

Before destructive actions:

```text
identify affected files
explain impact
preserve recoverability where possible
```

Do not run destructive database/file operations casually.

---

# 42. NO UNNECESSARY REFACTORING

If the user asks:

> "Fix retrieval latency."

Do not automatically:

```text
rewrite frontend
rename every module
change architecture
replace FastAPI
replace FAISS
```

unless evidence shows those changes are necessary.

---

# 43. PERFORMANCE WORKFLOW

When optimizing:

```text
Measure
   ↓
Profile
   ↓
Identify bottleneck
   ↓
Change one meaningful factor
   ↓
Test
   ↓
Benchmark
   ↓
Compare
```

Record important results in the progress log.

---

# 44. LATENCY BREAKDOWN

Where possible, measure:

```text
STT
Embedding
Retrieval
LLM generation
Grounding
Serialization
Total
```

This allows the team to identify the actual bottleneck.

---

# 45. WARM-UP AWARENESS

Benchmarks should distinguish between:

```text
cold start
warm execution
```

when relevant.

Do not compare a cold model load with a warm inference request and pretend they represent the same latency.

---

# 46. REPRODUCIBILITY

When recording benchmark results, include:

```text
date/time
commit/version
machine or deployment environment
sample count
query/audio set
warm-up policy
configuration
```

This makes results comparable.

---

# 47. AI MUST MAINTAIN A CLEAN WORKSPACE

Avoid leaving unnecessary:

```text
temporary files
debug scripts
random notebooks
large downloaded datasets
API responses
logs containing secrets
```

in the repository.

Use appropriate ignored directories.

---

# 48. GIT DISCIPLINE

If Git is available:

Before work:

```text
inspect git status
```

After work:

```text
inspect git diff
```

The AI should know what it changed.

Do not accidentally include:

```text
.env
credentials
large generated datasets
temporary files
```

---

# 49. REVIEW YOUR OWN DIFF

Before declaring a task complete:

Ask:

```text
Did I change only what was necessary?
Did I accidentally change another role's files?
Did I introduce a secret?
Did I break an interface?
Did I add an unnecessary dependency?
Did I leave debug code?
Did I update the progress log?
Did I run relevant tests?
```

---

# 50. PROGRESS LOG MUST BE UPDATED BEFORE FINAL RESPONSE

The AI must not finish a task and then forget the log.

The order is:

```text
Implementation
   ↓
Tests
   ↓
Verification
   ↓
Progress log update
   ↓
Final response
```

---

# 51. FINAL RESPONSE TO THE USER

After completing work, report concisely:

```text
Role:
Task:
Files changed:
What was implemented:
Tests:
Benchmark:
Progress log updated:
Integration impact:
Remaining issues:
```

Do not write a long narrative unless requested.

---

# 52. IF WORK IS INCOMPLETE

Be explicit.

Example:

```text
Status: IN PROGRESS

Implemented:
- Dataset loader
- Normalization

Not completed:
- Semantic chunking

Tests:
- 8 passed

Blocker:
Semantic chunking model needs to be selected.

Progress log:
Updated.
```

---

# 53. IF ANOTHER ROLE IS REQUIRED

Do not pretend the task is complete.

Example:

```text
Role 1 work is complete.

Role 3 integration is still required:
- connect retrieve_context()
- map DocumentChunk into RAG context

ROLE1_PROGRESS.md has been updated.
```

---

# 54. HANDOFF PROTOCOL

When handing work to another role, record:

```text
What was completed
Interface available
Files changed
How to use it
Tests passed
Known limitations
Required next step
```

Example:

```text
Role 1 → Role 3

Interface:
retrieve_context(query, top_k=3)

Returns:
list[DocumentChunk]

Verified:
FAISS search tests pass.

Next:
Integrate retrieval into RAG harness.
```

---

# 55. NO HIDDEN STATE

Important decisions must be written down.

Do not rely on:

```text
"the previous AI knows this"
```

or:

```text
"I mentioned it in an earlier chat"
```

If it matters to the project, record it in the appropriate documentation or progress log.

---

# 56. DECISION LOGGING

When making a non-trivial engineering decision, record:

```text
Decision:
Why:
Alternatives considered:
Impact:
```

Example:

```text
Decision:
Use in-memory FAISS for inference.

Why:
Avoid remote vector database latency.

Impact:
Fast retrieval but requires local index loading.
```

---

# 57. DO NOT OVER-ENGINEER

The hackathon has a deadline.

Prefer:

```text
simple
reliable
measurable
maintainable
```

over:

```text
complex
theoretical
over-abstracted
```

unless complexity is required by the README.

---

# 58. KEEP THE CRITICAL PATH SMALL

The request-time path should avoid unnecessary work.

Avoid:

```text
reloading models
rebuilding indexes
re-embedding documents
re-reading large datasets
unnecessary network calls
multiple unnecessary LLM calls
```

---

# 59. STARTUP VS REQUEST-TIME WORK

Expensive initialization should happen during startup/build where possible.

Conceptually:

```text
STARTUP
load model
load FAISS
load metadata
initialize clients

REQUEST
STT
query embedding
retrieval
generation
grounding
response
```

Do not rebuild infrastructure on every request.

---

# 60. OBSERVABILITY

Important components should provide enough information to diagnose failures.

Prefer structured logs such as:

```text
request_id
stage
duration
status
error_type
```

Never log:

```text
API keys
authorization headers
private credentials
sensitive secrets
```

---

# 61. REQUEST IDs

If the architecture supports request IDs, use them consistently across:

```text
STT
retrieval
LLM
guardrails
response
```

This makes latency debugging easier.

---

# 62. TIMEOUTS

External providers should have explicit timeouts where supported.

Never allow a provider call to hang indefinitely.

Handle timeout failures gracefully.

---

# 63. FALLBACK BEHAVIOR

When a component fails, return a controlled response.

Examples:

```text
STT unavailable
Retrieval unavailable
LLM unavailable
```

Do not return fabricated answers.

For missing or unavailable context:

```text
refuse safely
```

---

# 64. GROUNDING ETHICS

The system must prioritize truthful answers over impressive answers.

If evidence is insufficient:

```text
say that evidence is insufficient
```

Do not manufacture:

```text
facts
citations
sources
confidence
```

---

# 65. USER PRIVACY

Voice data and user queries should be handled responsibly.

Do not unnecessarily persist:

```text
raw audio
personal queries
provider responses
```

If data must be stored for benchmarking, document what is stored and why.

Avoid collecting more data than required.

---

# 66. SECURITY ETHICS

The AI must not intentionally introduce:

```text
credential leaks
unsafe deserialization
unvalidated file execution
arbitrary command execution
hardcoded secrets
unnecessary open endpoints
```

Validate external input.

---

# 67. DEPENDENCY SECURITY

When adding dependencies:

```text
use established packages
avoid suspicious/unmaintained packages where possible
pin or constrain versions when appropriate
```

Do not add packages merely because an AI-generated solution happened to use them.

---

# 68. FAIR REPRESENTATION OF RESULTS

When preparing the final hackathon submission:

Do not cherry-pick one unusually fast request and present it as the system's normal performance.

Report:

```text
P50
P70
P100
```

as required.

If the system misses the target, report the real result and work on optimization.

---

# 69. NO PERFORMANCE CHEATING

The AI must not:

```text
exclude slow requests without documenting it
stop the timer early
hide STT time
hide network time
use a fake mock result in a real benchmark
precompute the answer for benchmark queries
claim local latency as production latency
```

If a benchmark is synthetic, clearly label it.

---

# 70. NO SUBMISSION MISREPRESENTATION

Do not claim:

```text
live deployment
successful demo
completed integration
mandatory feature support
```

unless it is actually true.

The final submission should accurately represent the implementation.

---

# 71. DOCUMENTATION CONSISTENCY

When behavior changes materially:

```text
code
tests
progress log
relevant documentation
```

should remain consistent.

Do not allow README claims to become obviously false after implementation changes.

If the README needs updating, flag it and make the smallest appropriate documentation update consistent with the source-of-truth policy.

---

# 72. BEFORE INTEGRATION — THREE-ROLE AUDIT

The integrating AI MUST inspect:

```text
README.md
RULES.md
ROLES.md
ARCHITECTURE.md
progress/ROLE1_PROGRESS.md
progress/ROLE2_PROGRESS.md
progress/ROLE3_PROGRESS.md
```

Then inspect the actual implementation.

The integration should answer:

```text
What does each role claim to have completed?
What does the code actually contain?
What interfaces are available?
What tests pass?
What remains incomplete?
What could collide?
```

---

# 73. INTEGRATION STATUS TABLE

Before a major integration, create or mentally verify:

| Role | Claimed Status | Code Verified | Tests Verified | Integration Ready |
|---|---|---|---|---|
| Role 1 | ... | ... | ... | ... |
| Role 2 | ... | ... | ... | ... |
| Role 3 | ... | ... | ... | ... |

Do not mark integration-ready solely because the progress file says `DONE`.

---

# 74. INTEGRATION FAILURE PROTOCOL

If Role 1 is incomplete:

```text
Do not pretend retrieval is ready.
```

If Role 2 is incomplete:

```text
Do not pretend voice is ready.
```

If Role 3 is incomplete:

```text
Do not pretend end-to-end RAG is ready.
```

Instead report the exact missing component.

---

# 75. FINAL END-TO-END VERIFICATION

Before calling the entire project complete:

```text
README requirements
        ↓
Role 1 verification
        ↓
Role 2 verification
        ↓
Role 3 verification
        ↓
Integration tests
        ↓
Voice end-to-end test
        ↓
Latency benchmark
        ↓
P50/P70/P100
        ↓
Deployment test
        ↓
Final documentation
```

---

# 76. FINAL PROJECT STATUS

The AI should help maintain a clear distinction between:

```text
PLANNED
IN PROGRESS
BLOCKED
IMPLEMENTED
TESTED
INTEGRATED
BENCHMARKED
DEPLOYED
DONE
```

These are not interchangeable.

---

# 77. EMERGENCY RULE — IF YOU ARE UNSURE

If an AI is unsure whether an action violates these rules:

```text
STOP
READ RULES.md AGAIN
READ README.md AGAIN
INSPECT CURRENT STATE
```

Then proceed only if the action is clear.

If still ambiguous, ask the user rather than guessing.

---

# 78. AI SELF-CHECK BEFORE EVERY FINAL RESPONSE

Before replying that work is complete, verify:

```text
[ ] I read RULES.md
[ ] I read README.md
[ ] I identified the correct role
[ ] I inspected existing implementation
[ ] I avoided unnecessary cross-role changes
[ ] I did not fabricate results
[ ] I ran relevant tests
[ ] I checked my changes
[ ] I updated the role progress log
[ ] I documented blockers
[ ] I documented integration requirements
```

---

# 79. GOLDEN RULES

If the AI remembers only a few rules, remember these:

### Rule 1

```text
READ RULES.md BEFORE EVERY NEW INSTRUCTION.
```

### Rule 2

```text
READ README.md AFTER RULES.md.
```

### Rule 3

```text
README = WHAT TO BUILD.
RULES = HOW TO WORK.
```

### Rule 4

```text
NEVER ASSUME — INSPECT AND VERIFY.
```

### Rule 5

```text
LOG EVERY MEANINGFUL CHANGE.
```

### Rule 6

```text
NEVER FABRICATE TEST OR LATENCY RESULTS.
```

### Rule 7

```text
RESPECT ROLE BOUNDARIES.
```

### Rule 8

```text
BEFORE INTEGRATION, READ ALL THREE ROLE PROGRESS LOGS.
```

### Rule 9

```text
CODE + TEST + VERIFY + LOG + REPORT.
```

### Rule 10

```text
WHEN UNSURE, STOP AND CHECK THE DOCUMENTATION INSTEAD OF GUESSING.
```

---

# 80. MASTER AI OPERATING LOOP

Every AI agent working on this repository should effectively operate as:

```text
┌─────────────────────────────────────────┐
│          NEW USER INSTRUCTION            │
└────────────────────┬────────────────────┘
                     ↓
              READ RULES.md
                     ↓
              READ README.md
                     ↓
            IDENTIFY ROLE / TASK
                     ↓
         READ RELEVANT PROGRESS LOG
                     ↓
           INSPECT ACTUAL REPO
                     ↓
               MAKE A PLAN
                     ↓
               IMPLEMENT
                     ↓
                 TEST
                     ↓
               VERIFY DIFF
                     ↓
       CHECK CROSS-ROLE IMPACT
                     ↓
          UPDATE PROGRESS LOG
                     ↓
              REPORT RESULT
                     ↓
          WAIT FOR NEXT INSTRUCTION
                     ↓
             READ RULES.md AGAIN
```

This loop is mandatory.

---

# 81. FINAL ETHICAL PRINCIPLE

The objective is not merely to make the project appear complete.

The objective is to make the project:

```text
truthful
reproducible
safe
maintainable
measurable
collaborative
```

The AI must optimize for the team's actual success, not for producing impressive-looking output.

A smaller feature that is:

```text
implemented
tested
measured
documented
```

is better than a larger feature that is:

```text
unverified
fabricated
fragile
```

The repository should remain understandable to the next teammate and the next AI agent.

---

# 82. FINAL PROJECT GOVERNANCE SUMMARY

```text
README.md
    │
    │  Defines WHAT the project must build
    ▼
RULES.md
    │
    │  Defines HOW every AI must work
    ▼
ROLES.md
    │
    │  Defines WHO owns each subsystem
    ▼
PROGRESS LOGS
    │
    │  Record WHAT HAS ACTUALLY HAPPENED
    ▼
SOURCE CODE + TESTS
    │
    │  Provide the implementation evidence
    ▼
BENCHMARKS
    │
    │  Provide the performance evidence
    ▼
INTEGRATION
    │
    │  Combines verified work
    ▼
FINAL SYSTEM
```

**No AI should bypass this chain.**
