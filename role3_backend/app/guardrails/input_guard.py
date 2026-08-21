"""
Input Guard — the first guardrail in the pipeline.

Checks (in order, short-circuits on first failure):
  1. Empty / whitespace-only input
  2. Input too long (> 1000 chars)
  3. NSFW / unsafe content filter

The NSFW filter is a lightweight keyword-category approach to stay within
the < 200 ms latency budget. A secondary LLM call for safety classification
would cost ~100 ms extra and is not justified here.

If any check fails, InputGuardException is raised with a human-readable reason.
The orchestrator catches this and returns a RAGResponse with refusal=True.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# NSFW keyword categories
# Each entry: (category_label, set_of_trigger_terms)
# Terms are lowercased. Matching uses word-boundary regex for precision.
# ---------------------------------------------------------------------------

_NSFW_CATEGORIES: list[tuple[str, frozenset[str]]] = [
    (
        "explicit_sexual",
        frozenset({
            "porn", "pornography", "nude", "nudity", "naked", "sex", "sexual",
            "xxx", "erotic", "fetish", "hentai", "nsfw", "masturbat",
            "genitalia", "penis", "vagina", "orgasm", "intercourse",
        }),
    ),
    (
        "violence_harm",
        frozenset({
            "murder", "kill", "killing", "stab", "shoot", "bomb", "explosive",
            "terrorist", "terrorism", "massacre", "genocide", "torture",
            "assassinate", "assault", "rape", "kidnap",
        }),
    ),
    (
        "hate_speech",
        frozenset({
            "nigger", "faggot", "kike", "spic", "chink", "wetback",
            "retard", "tranny", "slut", "whore",
        }),
    ),
    (
        "self_harm",
        frozenset({
            "suicide", "self-harm", "self harm", "cut myself", "kill myself",
            "end my life", "overdose", "hang myself",
        }),
    ),
]

# Pre-compiled pattern for fast multi-word phrase matching
_PHRASE_PATTERNS: list[tuple[str, re.Pattern[str]]] = []
_WORD_SETS: list[tuple[str, frozenset[str]]] = []

for _cat, _terms in _NSFW_CATEGORIES:
    # Split into single-word terms and multi-word phrases for efficiency
    _single = frozenset(t for t in _terms if " " not in t and "-" not in t)
    _phrases = [t for t in _terms if " " in t or "-" in t]
    _WORD_SETS.append((_cat, _single))
    if _phrases:
        _pattern = re.compile(
            r"|".join(re.escape(p) for p in _phrases), re.IGNORECASE
        )
        _PHRASE_PATTERNS.append((_cat, _pattern))


class InputGuardException(Exception):
    """Raised when an input guard check fails."""

    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason  # machine-readable reason code


class InputGuard:
    """
    Validates and screens queries before they enter the expensive RAG pipeline.
    All checks are O(n) string operations — no LLM calls, no network.
    """

    MAX_LENGTH = 1000

    def check(self, query: str) -> None:
        """
        Run all input checks.
        Raises InputGuardException on the first failure found.
        Passes silently if the query is acceptable.
        """
        self._check_empty(query)
        self._check_length(query)
        self._check_nsfw(query)

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_empty(query: str) -> None:
        if not query or not query.strip():
            raise InputGuardException(
                "Query is empty. Please speak or type a question.",
                reason="empty_query",
            )

    def _check_length(self, query: str) -> None:
        if len(query) > self.MAX_LENGTH:
            raise InputGuardException(
                f"Query is too long (max {self.MAX_LENGTH} characters).",
                reason="query_too_long",
            )

    @staticmethod
    def _check_nsfw(query: str) -> None:
        """
        Lightweight NSFW check using pre-built word sets and phrase patterns.
        Word-boundary matching prevents false positives (e.g. 'sex' in 'context').
        """
        lower = query.lower()
        words = set(re.findall(r"\b\w+\b", lower))

        # Single-word checks (O(1) set intersection)
        for category, term_set in _WORD_SETS:
            hit = words & term_set
            if hit:
                raise InputGuardException(
                    "Your query contains content that cannot be processed. "
                    "Please ask a question related to the knowledge base.",
                    reason=f"nsfw_{category}",
                )

        # Multi-word phrase checks
        for category, pattern in _PHRASE_PATTERNS:
            if pattern.search(lower):
                raise InputGuardException(
                    "Your query contains content that cannot be processed. "
                    "Please ask a question related to the knowledge base.",
                    reason=f"nsfw_{category}",
                )
