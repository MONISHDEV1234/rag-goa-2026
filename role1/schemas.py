"""
schemas.py — Role 1: Shared Pydantic models for the retrieval subsystem.

This is the contract Role 3's harness depends on. DocumentChunk is what
retrieve_context() returns; RetrievalError is what it raises on failure
(so Role 3's Tenacity retry logic has a concrete, catchable exception
type instead of a silently-empty result).
"""

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """A single retrieved chunk, returned by retrieve_context()."""

    chunk_id: str = Field(..., description="Unique id of this chunk")
    text: str = Field(..., description="Chunk text content")
    doc_id: str = Field(..., description="Source document/passage id")
    strategy: str = Field(..., description="Chunking strategy that produced this chunk")
    lang: str = Field(..., description="Language code of this chunk (e.g. 'en', 'hi')")
    query_id: int = Field(..., description="Source dataset query_id this chunk was derived from")
    query_type: str = Field(..., description="Source dataset query_type")
    score: float = Field(..., description="Similarity/relevance score from vector search")
    is_selected: bool = Field(
        default=False,
        description="Ground-truth relevance flag from the source dataset, where available",
    )

    class Config:
        frozen = True  # chunks are immutable once retrieved


class RetrievalError(Exception):
    """
    Raised by retrieve_context() on any failure (index not loaded, empty
    query, embedding failure, etc.) — never return a silent empty list on
    error, since Role 3's retry logic needs a real exception to catch.
    A retrieval that legitimately finds nothing relevant should still
    return an empty list; this is only for actual failures.
    """
    pass
