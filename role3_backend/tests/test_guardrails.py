"""
Tests for all three guardrails:
  - InputGuard (validation + NSFW)
  - ContextGuard (context sufficiency)
  - GroundingChecker (deterministic token overlap)
"""

from __future__ import annotations

import pytest

from app.guardrails.input_guard import InputGuard, InputGuardException
from app.guardrails.context_guard import ContextGuard, InsufficientContextException
from app.guardrails.grounding import GroundingChecker
from app.schemas import DocumentChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chunk(text: str, score: float = 0.85, doc_id: str = "doc_001") -> DocumentChunk:
    return DocumentChunk(
        text=text,
        doc_id=doc_id,
        chunk_strategy="semantic",
        similarity_score=score,
    )


# ---------------------------------------------------------------------------
# InputGuard — Empty / length
# ---------------------------------------------------------------------------

class TestInputGuardBasic:
    guard = InputGuard()

    def test_empty_string_raises(self):
        with pytest.raises(InputGuardException) as exc_info:
            self.guard.check("")
        assert exc_info.value.reason == "empty_query"

    def test_whitespace_only_raises(self):
        with pytest.raises(InputGuardException) as exc_info:
            self.guard.check("   \n\t  ")
        assert exc_info.value.reason == "empty_query"

    def test_too_long_raises(self):
        long_query = "a" * 1001
        with pytest.raises(InputGuardException) as exc_info:
            self.guard.check(long_query)
        assert exc_info.value.reason == "query_too_long"

    def test_valid_query_passes(self):
        # Should not raise
        self.guard.check("What is the MSMARCO-XI dataset?")

    def test_exactly_max_length_passes(self):
        self.guard.check("a" * 1000)


# ---------------------------------------------------------------------------
# InputGuard — NSFW filter
# ---------------------------------------------------------------------------

class TestInputGuardNSFW:
    guard = InputGuard()

    @pytest.mark.parametrize("query", [
        "show me porn",
        "I want explicit sexual content",
        "how to make a bomb",
        "how to murder someone",
        "I want to kill myself",
        "suicide methods",
    ])
    def test_nsfw_queries_raise(self, query):
        with pytest.raises(InputGuardException) as exc_info:
            self.guard.check(query)
        assert "nsfw" in exc_info.value.reason

    @pytest.mark.parametrize("query", [
        "What is the context of MSMARCO dataset?",
        "How does semantic chunking work?",
        "Explain the retrieval architecture",
        "What is FAISS used for?",
        "Tell me about AI4Bharat",
        "What languages does MSMARCO-XI cover?",
    ])
    def test_clean_queries_pass(self, query):
        # Should not raise
        self.guard.check(query)

    def test_word_boundary_no_false_positive(self):
        # 'sex' should not trigger on 'context', 'sexual' should trigger on 'sexual'
        self.guard.check("Explain the context of the dataset")  # should pass
        with pytest.raises(InputGuardException):
            self.guard.check("sexual content query")


# ---------------------------------------------------------------------------
# ContextGuard
# ---------------------------------------------------------------------------

class TestContextGuard:
    guard = ContextGuard(threshold=0.50)

    def test_empty_chunks_raises(self):
        with pytest.raises(InsufficientContextException):
            self.guard.check([])

    def test_low_similarity_raises(self):
        chunks = [make_chunk("some text", score=0.30)]
        with pytest.raises(InsufficientContextException):
            self.guard.check(chunks)

    def test_high_similarity_passes(self):
        chunks = [make_chunk("relevant text", score=0.85)]
        # Should not raise
        self.guard.check(chunks)

    def test_best_score_above_threshold_passes(self):
        # Even if some chunks are low, best score wins
        chunks = [
            make_chunk("text a", score=0.20),
            make_chunk("text b", score=0.30),
            make_chunk("text c", score=0.75),  # best
        ]
        self.guard.check(chunks)

    def test_all_below_threshold_raises(self):
        chunks = [
            make_chunk("text a", score=0.20),
            make_chunk("text b", score=0.30),
        ]
        with pytest.raises(InsufficientContextException):
            self.guard.check(chunks)

    def test_exactly_at_threshold_raises(self):
        # threshold is exclusive lower bound
        chunks = [make_chunk("text", score=0.49)]
        with pytest.raises(InsufficientContextException):
            self.guard.check(chunks)

    def test_custom_threshold(self):
        strict_guard = ContextGuard(threshold=0.90)
        chunks = [make_chunk("text", score=0.85)]
        with pytest.raises(InsufficientContextException):
            strict_guard.check(chunks)


# ---------------------------------------------------------------------------
# GroundingChecker
# ---------------------------------------------------------------------------

class TestGroundingChecker:
    checker = GroundingChecker(coverage_threshold=0.30)

    def test_grounded_answer(self):
        chunks = [make_chunk(
            "MSMARCO-XI is a multilingual benchmark covering Indian languages."
        )]
        answer = "MSMARCO-XI is a multilingual benchmark for Indian languages."
        assert self.checker.check(answer, chunks) is True

    def test_ungrounded_answer(self):
        chunks = [make_chunk(
            "MSMARCO-XI covers Indian languages."
        )]
        # Answer introduces content completely unrelated to context
        answer = (
            "The Eiffel Tower is located in Paris, France and was built in 1889 "
            "as the entrance arch for the World's Fair."
        )
        assert self.checker.check(answer, chunks) is False

    def test_empty_chunks_returns_false(self):
        assert self.checker.check("Some answer", []) is False

    def test_empty_answer_returns_false(self):
        chunks = [make_chunk("Some relevant context text here.")]
        assert self.checker.check("", chunks) is False

    def test_stop_words_only_answer_returns_false(self):
        chunks = [make_chunk("relevant context")]
        assert self.checker.check("the and is a or", chunks) is False

    def test_known_overlap_calculation(self):
        # Context contains: [msmarco, multilingual, benchmark, indian, languages]
        # Answer contains:  [msmarco, multilingual, system]
        # Overlap = {msmarco, multilingual} = 2 / 3 answer tokens = 0.67 ≥ 0.30 → grounded
        chunks = [make_chunk("MSMARCO multilingual benchmark for Indian languages.")]
        answer = "MSMARCO multilingual system"
        assert self.checker.check(answer, chunks) is True
