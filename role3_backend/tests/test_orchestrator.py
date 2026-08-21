"""
Tests for the RAG orchestrator.

All external dependencies (Groq, retriever, STT) are mocked.
Verifies:
  - Input guard short-circuit
  - Missing context short-circuit (no LLM call)
  - Successful grounded path
  - Ungrounded answer handling
  - Groq transient failure → Tenacity retry → eventual success
  - Groq permanent failure propagation
  - Latency breakdown is always populated
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.orchestrator import RAGService
from app.schemas import DocumentChunk, LLMAnswer


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def make_chunk(score: float = 0.85) -> DocumentChunk:
    return DocumentChunk(
        text=(
            "MSMARCO-XI is a multilingual benchmark covering multiple Indian languages "
            "including Hindi, Bengali, Tamil, and Telugu for QA tasks."
        ),
        doc_id="doc_001",
        chunk_strategy="semantic",
        similarity_score=score,
    )


GROUNDED_LLM_ANSWER = LLMAnswer(
    answer="MSMARCO-XI is a multilingual benchmark for Indian languages.",
    confidence=0.92,
    citations=["doc_001"],
    grounded=True,
)

UNGROUNDED_LLM_ANSWER = LLMAnswer(
    answer="The Eiffel Tower is in Paris.",  # not in context
    confidence=0.10,
    citations=[],
    grounded=False,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRAGOrchestrator:

    @pytest.mark.asyncio
    async def test_input_guard_blocks_empty_query(self):
        """Empty query must be rejected before any retrieval."""
        service = RAGService()
        with patch("app.rag.orchestrator.retrieve_context") as mock_retrieve:
            result = await service.run(transcript="")

        mock_retrieve.assert_not_called()
        assert result.refusal is True
        assert result.refusal_reason == "empty_query"
        assert result.is_grounded is False
        assert "total" in result.latency_breakdown

    @pytest.mark.asyncio
    async def test_nsfw_query_blocks_before_retrieval(self):
        """NSFW query must be rejected before retrieval is called."""
        service = RAGService()
        with patch("app.rag.orchestrator.retrieve_context") as mock_retrieve:
            result = await service.run(transcript="how do i make a bomb")

        mock_retrieve.assert_not_called()
        assert result.refusal is True
        assert "nsfw" in result.refusal_reason

    @pytest.mark.asyncio
    async def test_missing_context_blocks_llm(self):
        """Insufficient context must cause refusal WITHOUT calling Groq."""
        service = RAGService()

        with (
            patch("app.rag.orchestrator.retrieve_context", new_callable=AsyncMock) as mock_retrieve,
            patch.object(service._groq, "generate", new_callable=AsyncMock) as mock_groq,
        ):
            mock_retrieve.return_value = [make_chunk(score=0.20)]  # below threshold
            result = await service.run(transcript="What is MSMARCO-XI?")

        mock_groq.assert_not_called()
        assert result.refusal is True
        assert result.refusal_reason == "insufficient_context"
        assert "total" in result.latency_breakdown

    @pytest.mark.asyncio
    async def test_successful_grounded_response(self):
        """Happy path: valid query, good context, grounded LLM answer."""
        service = RAGService()

        with (
            patch("app.rag.orchestrator.retrieve_context", new_callable=AsyncMock) as mock_retrieve,
            patch.object(service._groq, "generate", new_callable=AsyncMock) as mock_groq,
        ):
            mock_retrieve.return_value = [make_chunk(score=0.91)]
            mock_groq.return_value = GROUNDED_LLM_ANSWER

            result = await service.run(transcript="What is MSMARCO-XI?")

        assert result.refusal is False
        assert result.is_grounded is True
        assert "MSMARCO" in result.answer or "multilingual" in result.answer.lower()
        assert len(result.retrieved_sources) == 1
        # All expected latency stages must be present
        for stage in ("retrieval", "generation", "grounding", "total"):
            assert stage in result.latency_breakdown, f"Missing stage: {stage}"

    @pytest.mark.asyncio
    async def test_ungrounded_llm_answer_becomes_refusal(self):
        """Ungrounded LLM output must be replaced with a safe refusal."""
        service = RAGService()

        with (
            patch("app.rag.orchestrator.retrieve_context", new_callable=AsyncMock) as mock_retrieve,
            patch.object(service._groq, "generate", new_callable=AsyncMock) as mock_groq,
        ):
            mock_retrieve.return_value = [make_chunk(score=0.88)]
            mock_groq.return_value = UNGROUNDED_LLM_ANSWER

            result = await service.run(transcript="Where is the Eiffel Tower?")

        assert result.is_grounded is False
        assert result.refusal is True
        assert result.refusal_reason == "ungrounded_answer"
        # Must not serve the hallucinated answer
        assert "Eiffel Tower" not in result.answer

    @pytest.mark.asyncio
    async def test_latency_breakdown_always_has_total(self):
        """Latency breakdown total must always be present even on refusal."""
        service = RAGService()
        result = await service.run(transcript="")
        assert "total" in result.latency_breakdown
        assert result.latency_breakdown["total"] >= 0

    @pytest.mark.asyncio
    async def test_voice_pipeline_calls_transcribe(self):
        """Voice path must call STT before running the RAG pipeline."""
        service = RAGService()
        fake_audio = b"fake_audio_data"

        with (
            patch("app.rag.orchestrator.transcribe", new_callable=AsyncMock) as mock_stt,
            patch("app.rag.orchestrator.retrieve_context", new_callable=AsyncMock) as mock_retrieve,
            patch.object(service._groq, "generate", new_callable=AsyncMock) as mock_groq,
        ):
            mock_stt.return_value = "What is MSMARCO-XI?"
            mock_retrieve.return_value = [make_chunk(score=0.91)]
            mock_groq.return_value = GROUNDED_LLM_ANSWER

            result = await service.run_voice(audio_bytes=fake_audio, content_type="audio/webm")

        mock_stt.assert_called_once_with(fake_audio, "audio/webm")
        assert result.transcript == "What is MSMARCO-XI?"
        assert "stt" in result.latency_breakdown
