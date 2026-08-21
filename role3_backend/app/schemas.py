"""
Shared Pydantic contracts — HH Goa 2026 Voice-Enabled RAG System.

This is the SINGLE SOURCE OF TRUTH for all three roles.
DO NOT change these schemas without coordinating with Role 1 and Role 2.

Field naming design
-------------------
``DocumentChunk`` accepts both Role 1's native field names (``strategy``,
``score``) and Role 3/mock field names (``chunk_strategy``,
``similarity_score``) as optional. The properties ``effective_score`` and
``effective_strategy`` let all consumers use a single access path without
caring which side populated the field.

This means:
  - Role 1's ``retrieve_context()`` can return chunks with ``strategy`` /
    ``score`` as it always has — zero code change on Role 1's side.
  - Role 3's tests, mock_retriever, context_guard, and prompt builder
    continue to use ``similarity_score`` / ``chunk_strategy`` — zero
    breakage on the Role 3 test side.
  - ``context_guard`` and ``prompt.py`` call ``.effective_score`` so
    they work transparently with both sources.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Role 1 Interface Contract
# ---------------------------------------------------------------------------

class DocumentChunk(BaseModel):
    """A single retrieved chunk from the FAISS index.

    Fields with dual naming (Role 1 vs Role 3):
      - ``strategy``  ↔ ``chunk_strategy``   (chunking method used)
      - ``score``     ↔ ``similarity_score``  (vector similarity)

    All four are Optional. Use the properties ``effective_score`` and
    ``effective_strategy`` for safe unified access in all pipeline code.
    """

    # Core fields — always required
    text: str = Field(..., description="The chunk text content.")
    doc_id: str = Field(..., description="Source document identifier.")

    # Role 1 native field names
    strategy: Optional[str] = Field(
        default=None,
        description="Chunking strategy (Role 1 name). E.g. 'metadata_aware', 'fixed_size', 'semantic'.",
    )
    score: Optional[float] = Field(
        default=None,
        description="Similarity / relevance score from vector search (Role 1 field name).",
    )

    # Role 3 / mock field names — kept for backward compat
    chunk_strategy: Optional[str] = Field(
        default=None,
        description="Chunking strategy (Role 3 alias). Use ``strategy`` or ``chunk_strategy``.",
    )
    similarity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Cosine similarity score (Role 3 alias). Use ``score`` or ``similarity_score``.",
    )

    # Role 1 extended metadata — all optional for backward compat
    chunk_id: Optional[str] = Field(default=None, description="Unique id of this chunk.")
    lang: Optional[str] = Field(default=None, description="Language code (e.g. 'en', 'hi').")
    query_id: Optional[int] = Field(default=None, description="Source dataset query_id.")
    query_type: Optional[str] = Field(default=None, description="Source dataset query_type.")
    is_selected: bool = Field(
        default=False,
        description="Ground-truth relevance flag from the dataset, where available.",
    )

    @property
    def effective_score(self) -> float:
        """Return similarity score regardless of which field was populated."""
        if self.score is not None:
            return self.score
        if self.similarity_score is not None:
            return self.similarity_score
        return 0.0

    @property
    def effective_strategy(self) -> str:
        """Return chunking strategy regardless of which field was populated."""
        return self.strategy or self.chunk_strategy or "unknown"

    model_config = {"populate_by_name": True}


class RetrievalError(Exception):
    """
    Raised by retrieve_context() on any failure (index not loaded, empty query,
    embedding failure, etc.). Never return a silent empty list on error — Role 3's
    Tenacity retry logic needs a real exception to catch.
    A retrieval that legitimately finds nothing relevant returns []; this is only
    for actual failures.
    """
    pass


# ---------------------------------------------------------------------------
# Internal LLM Contract
# ---------------------------------------------------------------------------

class LLMAnswer(BaseModel):
    """Structured output returned by the Groq LLM."""
    answer: str = Field(..., description="The generated answer.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model self-reported confidence.")
    citations: list[str] = Field(default_factory=list, description="doc_ids the answer is based on.")
    grounded: bool = Field(..., description="Model self-reports whether its answer is grounded.")


# ---------------------------------------------------------------------------
# API Request Models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Request body for POST /api/query (text path)."""
    query: str = Field(..., min_length=1, max_length=1000, description="User's text query.")


class VoiceRequest(BaseModel):
    """Request body for POST /api/voice (voice path).

    Audio is base64-encoded. Role 2 frontend encodes audio before sending.
    Format assumed: base64(audio/webm). Can be adapted to multipart later.
    """
    audio_b64: str = Field(..., description="Base64-encoded audio bytes.")
    content_type: str = Field(default="audio/webm", description="MIME type of the audio.")


# ---------------------------------------------------------------------------
# API Response Contract
# Role 2 frontend depends on this schema. Do not change field names without
# coordinating with Role 2 and updating changed.md.
# ---------------------------------------------------------------------------

class RAGResponse(BaseModel):
    """Final API response returned by /api/query and /api/voice."""
    transcript: str = Field(..., description="The text query (transcribed if voice, echoed if text).")
    answer: str = Field(..., description="The generated or refusal answer.")
    is_grounded: bool = Field(..., description="Whether the answer is grounded in retrieved context.")
    retrieved_sources: list[DocumentChunk] = Field(default_factory=list)
    latency_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Per-stage latency in milliseconds. Keys: stt, retrieval, generation, grounding, total.",
    )
    refusal: bool = Field(default=False, description="True when the system refused to answer.")
    refusal_reason: Optional[str] = Field(default=None, description="Human-readable refusal reason.")
