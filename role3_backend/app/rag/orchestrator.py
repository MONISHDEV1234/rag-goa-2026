"""
RAG Orchestrator — the central pipeline controller for Role 3.

Pipeline (text path):
  transcript
    → input_guard (validate + NSFW)
    → retrieve_context (Role 1 interface)
    → context_guard (sufficiency check)
    → prompt builder
    → groq_client (Groq LLM + tenacity retries)
    → grounding_check
    → RAGResponse

Pipeline (voice path):
  audio_bytes
    → stt (Sarvam / mock)
    → [same as text path above]

Latency is measured at each stage using time.perf_counter().
All timings are reported in milliseconds in latency_breakdown.
"""

from __future__ import annotations

import time
from typing import Callable

from app.config import settings
from app.schemas import DocumentChunk, RAGResponse, RetrievalError
from app.guardrails.input_guard import InputGuard, InputGuardException
from app.guardrails.context_guard import ContextGuard, InsufficientContextException
from app.guardrails.grounding import GroundingChecker
from app.rag.prompt import build_prompt, SYSTEM_PROMPT
from app.llm.groq_client import GroqClient

# ---------------------------------------------------------------------------
# Integration stubs — replaced when Role 1 and Role 2 code lands
# ---------------------------------------------------------------------------

# ROLE 1 INTEGRATION — COMPLETE:
# Using Role 1's real FAISS-backed retrieve_context().
# init_retrieval() is called once at app startup in app/main.py (lifespan handler).
from app.retrieval.retriever import retrieve_context  # noqa: E402

# Role 2's real Sarvam STT client.
from app.stt.sarvam_client import transcribe  # noqa: E402


def _ms(start: float) -> float:
    """Convert perf_counter delta to milliseconds, 2 decimal places."""
    return round((time.perf_counter() - start) * 1000, 2)


class RAGService:
    """
    Stateless service that executes the full RAG pipeline.
    One instance is shared across all requests (instantiated in routes.py).
    """

    def __init__(self) -> None:
        self._input_guard = InputGuard()
        self._context_guard = ContextGuard(
            threshold=settings.context_similarity_threshold
        )
        self._grounding_checker = GroundingChecker()
        self._groq = GroqClient()

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def run(self, transcript: str, top_k: int | None = None) -> RAGResponse:
        """Execute the RAG pipeline for a text (already-transcribed) query."""
        return await self._pipeline(transcript=transcript, stt_ms=0.0, top_k=top_k)

    async def run_voice(
        self, audio_bytes: bytes, content_type: str, top_k: int | None = None
    ) -> RAGResponse:
        """Execute the STT step then the RAG pipeline for a voice request."""
        t0 = time.perf_counter()
        transcript = await transcribe(audio_bytes, content_type)
        stt_ms = _ms(t0)
        return await self._pipeline(transcript=transcript, stt_ms=stt_ms, top_k=top_k)

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    async def _pipeline(
        self, transcript: str, stt_ms: float, top_k: int | None = None
    ) -> RAGResponse:
        """
        Executes the complete RAG pipeline and returns a RAGResponse.
        Handles all guardrail short-circuits and measures per-stage latency.
        """
        total_start = time.perf_counter()
        latency: dict[str, float] = {"stt": stt_ms}

        # ---- 1. Input Guard (validation + NSFW) ----
        t = time.perf_counter()
        try:
            self._input_guard.check(transcript)
        except InputGuardException as exc:
            latency["input_guard"] = _ms(t)
            latency["total"] = _ms(total_start)
            return RAGResponse(
                transcript=transcript,
                answer=str(exc),
                is_grounded=False,
                retrieved_sources=[],
                latency_breakdown=latency,
                refusal=True,
                refusal_reason=exc.reason,
            )
        latency["input_guard"] = _ms(t)

        # ---- 2. Retrieval (Role 1 FAISS) ----
        t = time.perf_counter()
        try:
            chunks: list[DocumentChunk] = await retrieve_context(
                query=transcript,
                top_k=top_k or settings.retrieval_top_k,
                min_score=settings.retrieval_min_score,
            )
        except RetrievalError as exc:
            latency["retrieval"] = _ms(t)
            latency["total"] = _ms(total_start)
            return RAGResponse(
                transcript=transcript,
                answer="The retrieval system encountered an error. Please try again.",
                is_grounded=False,
                retrieved_sources=[],
                latency_breakdown=latency,
                refusal=True,
                refusal_reason="retrieval_error",
            )
        latency["retrieval"] = _ms(t)

        # ---- 3. Context Sufficiency Guard ----
        t = time.perf_counter()
        try:
            self._context_guard.check(chunks)
        except InsufficientContextException as exc:
            latency["context_guard"] = _ms(t)
            latency["total"] = _ms(total_start)
            return RAGResponse(
                transcript=transcript,
                answer=str(exc),
                is_grounded=False,
                retrieved_sources=chunks,
                latency_breakdown=latency,
                refusal=True,
                refusal_reason="insufficient_context",
            )
        latency["context_guard"] = _ms(t)

        # ---- 4. Prompt Construction ----
        user_message = build_prompt(query=transcript, chunks=chunks)

        # ---- 5. LLM Generation (Groq + Tenacity retries) ----
        t = time.perf_counter()
        try:
            llm_answer = await self._groq.generate(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
            )
        except Exception as exc:
            latency["generation"] = _ms(t)
            latency["total"] = _ms(total_start)
            return RAGResponse(
                transcript=transcript,
                answer=f"LLM Generation Error: {exc}",
                is_grounded=False,
                retrieved_sources=chunks,
                latency_breakdown=latency,
                refusal=True,
                refusal_reason="generation_error",
            )
        latency["generation"] = _ms(t)

        # ---- 6. Grounding Check (deterministic, < 1 ms) ----
        t = time.perf_counter()
        is_grounded = self._grounding_checker.check(
            answer=llm_answer.answer,
            chunks=chunks,
            llm_grounded=llm_answer.grounded,
        )
        latency["grounding"] = _ms(t)

        # ---- 7. Final answer assembly ----
        latency["total"] = round(latency.get("retrieval", 0) + latency["generation"] + latency["grounding"], 2)

        final_answer = llm_answer.answer
        refusal = False
        refusal_reason = None

        if not is_grounded:
            final_answer = (
                "I couldn't verify this answer against the retrieved knowledge base. "
                "Please try rephrasing your question."
            )
            refusal = True
            refusal_reason = "ungrounded_answer"

        return RAGResponse(
            transcript=transcript,
            answer=final_answer,
            is_grounded=is_grounded,
            retrieved_sources=chunks,
            latency_breakdown=latency,
            refusal=refusal,
            refusal_reason=refusal_reason,
        )
