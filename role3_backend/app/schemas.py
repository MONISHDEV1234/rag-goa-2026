"""
Role 3 — Backend / RAG Harness / Guardrails / Integration
HH Goa 2026 Voice-Enabled RAG System

Shared Pydantic contracts used by all three roles.
DO NOT change these schemas without coordinating with Role 1 and Role 2.
Document any change in progress/ROLE3_PROGRESS.md and changed.md before committing.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Role 1 Interface Contract
# Produced by Role 1's retrieve_context() and consumed by Role 3's orchestrator.
# ---------------------------------------------------------------------------

class DocumentChunk(BaseModel):
    """A single retrieved chunk from the FAISS index."""
    text: str = Field(..., description="The chunk text content.")
    doc_id: str = Field(..., description="Source document identifier.")
    chunk_strategy: str = Field(..., description="'semantic' or 'sliding_window'.")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score [0,1].")


# ---------------------------------------------------------------------------
# Internal LLM Contract
# The structured output Groq must return. Validated before it reaches the API response.
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
        description="Per-stage latency in milliseconds. Keys: stt, retrieval, generation, grounding, total."
    )
    refusal: bool = Field(default=False, description="True when the system refused to answer.")
    refusal_reason: Optional[str] = Field(default=None, description="Human-readable refusal reason.")
