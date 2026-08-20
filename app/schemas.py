"""
app/schemas.py — Shared Pydantic data contracts (Role 3 owns this file)

All three roles depend on these schemas.
Do NOT modify without coordinating with all roles.

Schemas:
    DocumentChunk   — a single retrieved passage (Role 1 produces)
    RAGResponse     — final API response (Role 3 produces, Role 2 consumes)
    QueryRequest    — text query API request body
    LLMAnswer       — structured LLM generation output (Role 3 internal)
    BenchmarkResult — per-query benchmark record (Role 2 uses for logging)
    HealthResponse  — /health endpoint response
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ── Role 1 → Role 3 ──────────────────────────────────────────────────────────

class DocumentChunk(BaseModel):
    """A single chunk retrieved from the FAISS index."""
    text:             str
    doc_id:           str
    chunk_strategy:   str
    similarity_score: float


# ── Role 3 → Role 2 / Frontend ────────────────────────────────────────────────

class RAGResponse(BaseModel):
    """The complete API response returned by POST /api/voice and POST /api/query."""
    transcript:         str
    answer:             str
    is_grounded:        bool
    retrieved_sources:  List[DocumentChunk] = Field(default_factory=list)
    latency_breakdown:  Dict[str, float]    = Field(default_factory=dict)


# ── API request bodies ────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Request body for POST /api/query (text-only RAG)."""
    query: str
    top_k: int = Field(default=3, ge=1, le=20)


# ── Role 3 internal ──────────────────────────────────────────────────────────

class LLMAnswer(BaseModel):
    """Structured output parsed from the Groq LLM response."""
    answer:     str
    confidence: float = Field(ge=0.0, le=1.0)
    citations:  List[str] = Field(default_factory=list)
    grounded:   bool


# ── Role 2 — benchmarking ─────────────────────────────────────────────────────

class BenchmarkResult(BaseModel):
    """Per-query latency record written by the benchmark runner."""
    query_id:       str
    stt_ms:         Optional[float] = None
    embedding_ms:   Optional[float] = None
    retrieval_ms:   Optional[float] = None
    generation_ms:  Optional[float] = None
    grounding_ms:   Optional[float] = None
    total_ms:       Optional[float] = None


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
