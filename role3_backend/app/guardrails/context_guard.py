"""
Context Sufficiency Guard.

Checks whether retrieved chunks are good enough to justify calling the LLM.

Logic:
  - If no chunks are returned → refuse.
  - If the best (highest) similarity score is below the configured threshold → refuse.

This guard prevents the LLM from being called with useless context and generating
a hallucinated answer. It also saves significant latency on hopeless queries.

The threshold (default 0.50) MUST be tuned experimentally once the real
FAISS index is built from MSMARCO-XI. A wrong threshold will cause either
too many false refusals or too many hallucinations.
"""

from __future__ import annotations

from app.schemas import DocumentChunk


class InsufficientContextException(Exception):
    """Raised when retrieved context is not sufficient to answer reliably."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ContextGuard:
    """
    Evaluates retrieved DocumentChunk objects for sufficiency.
    Instantiated once and reused across requests.
    """

    def __init__(self, threshold: float = 0.50) -> None:
        self._threshold = threshold

    def check(self, chunks: list[DocumentChunk]) -> None:
        """
        Validates context sufficiency.
        Raises InsufficientContextException if retrieval is insufficient.
        Passes silently otherwise.
        """
        if not chunks:
            raise InsufficientContextException(
                "I couldn't find any relevant information in the knowledge base "
                "to answer your question."
            )

        best_score = max(c.similarity_score for c in chunks)
        if best_score < self._threshold:
            raise InsufficientContextException(
                "I couldn't find enough relevant information in the knowledge base "
                f"to answer reliably (best similarity: {best_score:.2f}, "
                f"threshold: {self._threshold:.2f})."
            )
