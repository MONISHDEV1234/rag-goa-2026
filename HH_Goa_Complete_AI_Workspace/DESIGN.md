# DESIGN.md — HH Goa 2026 Voice RAG

## 1. Purpose

This document defines the **minimal, practical UI/UX design** for the HH Goa 2026 Voice-Enabled RAG demo.

It is subordinate to:

1. `README.md` — complete project specification
2. `ARCHITECTURE.md` — system architecture
3. `RULES.md` — AI working rules

If a design decision conflicts with a functional or hackathon requirement in those files, the higher-level requirement wins.

The goal is a UI that is minimal, professional, fast, easy to understand during a live demo, and practical to implement before **22 August 2026**.

---

## 2. Design Principle

The interface should make one thing immediately obvious:

> **Speak → Search → Get a grounded answer.**

Do not turn the application into a complicated dashboard.

Prioritize:
1. microphone;
2. transcript;
3. answer;
4. sources;
5. latency.

Everything else is secondary.

---

## 3. Visual Direction

Use a clean modern AI-product aesthetic:

- generous whitespace;
- simple cards;
- subtle borders;
- restrained shadows;
- clear typography;
- one primary accent;
- no excessive gradients;
- no decorative animations that affect performance.

The interface should look polished without requiring a large design system.

---

## 4. Main Screen

Desktop:

```text
┌──────────────────────────────────────────────────────────────┐
│ HH Goa RAG                              ● System Ready       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                    Voice RAG Assistant                       │
│          Ask a question about the knowledge base             │
│                                                              │
│                         ┌───────┐                            │
│                         │  MIC  │                            │
│                         └───────┘                            │
│                      Click to speak                          │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ Transcript                                                   │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Your transcribed question appears here.                  │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ Answer                                                       │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Grounded answer appears here.                            │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ Sources                                      Latency         │
│ ┌──────────────────────────┐               STT       42 ms │
│ │ Document 1               │               Retrieval  5 ms │
│ │ similarity: 0.91         │               Generation 58 ms│
│ └──────────────────────────┘               Total     105ms│
└──────────────────────────────────────────────────────────────┘
```

On smaller screens, stack:

```text
Header → Voice → Transcript → Answer → Sources → Latency
```

Do not create a separate mobile application.

---

## 5. Header

Keep the header small.

Show:
- `HH Goa RAG`
- system status

Example:

```text
HH Goa RAG                         ● System Ready
```

Status must reflect actual application state where practical. Do not show fake health indicators.

---

## 6. Voice Control

The microphone is the primary interaction.

### Idle

```text
      ┌─────┐
      │ 🎙  │
      └─────┘
    Click to speak
```

### Recording

Show a clear active state:

```text
      ●
   Listening...
```

### Processing

Show the current stage when available:

```text
Transcribing...
Searching...
Generating...
```

### Completion

Return to the normal microphone state and display the answer.

---

## 7. Application States

Support:

```text
IDLE
  ↓
RECORDING
  ↓
TRANSCRIBING
  ↓
RETRIEVING
  ↓
GENERATING
  ↓
GROUNDING_CHECK
  ↓
ANSWER
```

Failure states:

```text
STT_ERROR
RETRIEVAL_ERROR
GENERATION_ERROR
INSUFFICIENT_CONTEXT
```

Each state needs a short human-readable message. Never expose raw stack traces to the user.

---

## 8. Transcript

Keep the transcript visible but secondary to the answer.

```text
Transcript

"What is ...?"
```

Use readable wrapping. Do not make it editable unless it can be added without complicating the main flow.

---

## 9. Answer

The answer is the most important content after the microphone.

Use a simple answer card.

If grounded, show:

```text
✓ Grounded
```

This must reflect the actual `is_grounded` result. Never display a positive grounding badge merely for appearance.

---

## 10. Insufficient Context

When the system cannot answer reliably:

```text
Insufficient context

I couldn't find enough relevant information in
 the knowledge base to answer reliably.
```

This is required because the project requires graceful refusal when context is missing. Do not invent an answer to make the demo look successful.

---

## 11. Sources

Show retrieved sources below or beside the answer.

Example:

```text
Source 01
Document: <doc_id>
Strategy: Semantic
Similarity: 0.91
```

Optionally show a short excerpt. Do not expose large blocks of retrieved text by default.

The source display should make it obvious that the answer came from retrieved context.

---

## 12. Latency

Latency is a core project goal and should be visible without dominating the interface.

```text
Latency

STT          42 ms
Retrieval     5 ms
Generation   58 ms
──────────────────
Total        105 ms

✓ Under 200 ms
```

The total must come from actual measured data.

If it exceeds the target:

```text
Total        247 ms

⚠ Above target
```

Never hide failed latency runs.

---

## 13. Benchmark View

The detailed benchmark dashboard is secondary to the live voice experience.

If implemented:

```text
Latency Analytics

P50     108 ms
P70     126 ms
P100    181 ms
```

A simple visualization is sufficient. Do not build a complex analytics dashboard unless time remains after the core pipeline works.

The benchmark requirements in `README.md` remain authoritative.

---

## 14. Colors

Use a small semantic system rather than a large palette:

```text
Background
Surface
Text
Muted text
Border
Primary accent
Success
Warning
Error
```

Use colors consistently. Success/warning/error colors communicate state, not decoration.

---

## 15. Typography

Use a clean system/UI font stack:

```css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  sans-serif;
```

Use clear hierarchy for product name, title, section title, body, metadata and status.

---

## 16. Components

Keep the frontend small.

Minimum components:

```text
Header
VoiceButton
StatusMessage
TranscriptCard
AnswerCard
SourceList
SourceCard
LatencyPanel
```

Optional:

```text
BenchmarkPanel
```

Do not add a component library solely for visual complexity.

---

## 17. Interaction Rules

Primary interaction:

> Click microphone → speak → receive answer.

Recoverable errors should provide a clear way to try again without refreshing the page.

Do not freeze the interface while processing. Show the current pipeline stage.

---

## 18. Accessibility

Minimum requirements:

- microphone button has an accessible label;
- visible focus state;
- sufficient text contrast;
- status is understandable without color alone;
- buttons have meaningful labels;
- avoid relying only on animation.

---

## 19. Performance-Friendly UI

The frontend is part of a latency-sensitive system.

Therefore:

- use vanilla HTML/CSS/JS as specified by the project;
- avoid unnecessary dependencies;
- avoid large images;
- avoid autoplay media;
- avoid heavy animation;
- avoid unnecessary network requests;
- do not perform retrieval or LLM work in the browser;
- keep the initial page lightweight.

The UI must not compromise the `<200 ms` engineering target.

---

## 20. What NOT to Build

To keep the 22 August deadline realistic, do not prioritize:

- complex authentication;
- multi-page dashboards;
- chat history systems;
- user profiles;
- animated 3D backgrounds;
- elaborate charts;
- large illustrations;
- unnecessary settings panels;
- social features;
- unrelated analytics.

These are outside the minimum viable demo design.

---

## 21. Design and Backend Contract

The UI consumes the agreed backend contract; it does not invent a separate response format.

It should use:

```python
RAGResponse(
    transcript=...,
    answer=...,
    is_grounded=...,
    retrieved_sources=...,
    latency_breakdown=...
)
```

Do not assume fields outside the agreed contract.

If the shared schema changes, follow the integration and progress rules before changing the UI.

---

## 22. Design Ownership

Role 2 owns frontend implementation.

Role 3 owns backend/API behavior.

Role 1 owns retrieval/source data.

A frontend change must not silently modify backend contracts. A backend contract change must be coordinated with Role 2.

---

## 23. Definition of Done

- [ ] microphone interaction works;
- [ ] recording state is visible;
- [ ] transcription is displayed;
- [ ] answer is displayed;
- [ ] grounded state is accurate;
- [ ] insufficient-context state works;
- [ ] retrieved sources are visible;
- [ ] latency breakdown is visible;
- [ ] mobile layout is usable;
- [ ] keyboard/focus behavior is acceptable;
- [ ] no fake status/latency values are displayed;
- [ ] frontend works with the actual backend contract.

---

## 24. Design Change Rule

This document is the frontend design source of truth.

If an existing design feature is changed:

1. inspect the current implementation;
2. explain why the change is required;
3. preserve the existing visual language where possible;
4. test the affected state;
5. append the change to the appropriate progress log;
6. never rewrite the historical progress entry.

Do not redesign the entire application to solve a small UI problem.

---

## 25. Priority Order for 22 August

Implement in this order:

```text
1. Voice interaction
2. Transcript
3. Answer
4. Grounding status
5. Sources
6. Latency
7. Error/refusal states
8. Responsive layout
9. Small visual polish
10. Optional benchmark visualization
```

A simple working interface is preferable to an impressive interface that compromises the RAG pipeline.

---

## 26. Final Design Principle

The product should feel like a **fast, trustworthy voice research assistant**, not a complicated dashboard.

The judge should understand the value proposition within seconds:

```text
SPEAK
  ↓
RETRIEVE
  ↓
GENERATE
  ↓
VERIFY
  ↓
ANSWER
```

**Keep it minimal. Keep it fast. Keep it grounded.**
