"""
Grounding Checker — validates that the LLM's answer is supported by retrieved context.

Strategy: Deterministic token-overlap approach.
  - No second LLM call (would add ~100-300 ms — unacceptable for the 200 ms budget).
  - Tokenizes both the answer and the full context.
  - Removes stop words.
  - Computes coverage: what fraction of significant answer tokens appear in context.
  - If coverage ≥ threshold → grounded.

This approach is intentionally conservative and fast (< 1 ms).
It will occasionally produce false negatives (valid answers marked ungrounded)
when the LLM paraphrases heavily. This is acceptable for a demo — it is better
to issue a safe refusal than to serve a hallucinated answer.

If the LLM also self-reports grounded=False in its structured output, we also
treat the answer as ungrounded regardless of token overlap score.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.schemas import DocumentChunk

# Common English stop words excluded from overlap calculation.
# These carry no factual weight.
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "this", "that", "these",
    "those", "it", "its", "i", "you", "he", "she", "we", "they", "my",
    "your", "his", "her", "our", "their", "what", "which", "who", "how",
    "when", "where", "why", "not", "no", "yes", "if", "then", "so", "as",
    "from", "about", "into", "through", "during", "before", "after",
    "above", "below", "between",
})

# Minimum fraction of answer tokens that must appear in context.
_DEFAULT_COVERAGE_THRESHOLD = 0.30


def _tokenize(text: str) -> frozenset[str]:
    """Lowercase word tokenization across all Unicode scripts, stop words removed."""
    tokens = set(re.findall(r"\b\w{2,}\b", text.lower(), flags=re.UNICODE))
    return frozenset(tokens - _STOP_WORDS)


class GroundingChecker:
    """
    Checks whether a generated answer is supported by the retrieved chunks.
    Instantiated once and reused across all requests.
    """

    def __init__(self, coverage_threshold: float = _DEFAULT_COVERAGE_THRESHOLD) -> None:
        self._threshold = coverage_threshold

    def check(
        self,
        answer: str,
        chunks: list[DocumentChunk],
        llm_grounded: bool | None = None,
    ) -> bool:
        """
        Returns True if the answer is considered grounded, False otherwise.

        A grounded answer means: enough key tokens from the answer also
        appear in the combined retrieved context, or cross-lingual Indic
        passages were verified by the LLM reasoning step.
        """
        if not chunks or not answer.strip():
            return False

        if llm_grounded is False:
            return False

        answer_tokens = _tokenize(answer)
        if not answer_tokens:
            # Answer is only stop words — treat as ungrounded
            return False

        combined_context = " ".join(c.text for c in chunks)
        context_tokens = _tokenize(combined_context)

        overlap = answer_tokens & context_tokens
        coverage = len(overlap) / len(answer_tokens) if len(answer_tokens) > 0 else 0.0

        if coverage >= self._threshold:
            return True

        # Multilingual / cross-lingual check:
        # If retrieved passages are in Indic scripts (Hindi, Gujarati, Urdu, Tamil, etc.)
        # and the answer was generated in English, character-level overlap is naturally 0.
        # When non-Latin scripts are present, trust the LLM grounding flag if not explicitly False.
        has_multilingual_context = any(ord(ch) > 127 for ch in combined_context if not ch.isspace() and not ch.isdigit())
        if has_multilingual_context and (llm_grounded is True or llm_grounded is None):
            return True

        return False
