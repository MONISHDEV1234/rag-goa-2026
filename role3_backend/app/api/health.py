"""Health endpoint — GET /health

Returns liveness + Role 1 FAISS retrieval subsystem diagnostics.
Role 2 frontend polls this to show the 'System Ready' indicator.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["health"])


class RetrievalHealth(BaseModel):
    status: str
    vectors_indexed: int = 0
    model_name: str = "unknown"
    embedding_dim: int = 0
    cache_size: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    bm25_sparse_index_ready: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str
    retrieval: Optional[RetrievalHealth] = None


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Liveness probe + subsystem diagnostics.

    ``status`` is "ok" even when retrieval is uninitialized — the server is
    alive. The ``retrieval.status`` field tells Role 2 whether queries can
    actually be answered.
    """
    from app.retrieval.retriever import get_retrieval_status

    raw = get_retrieval_status()
    retrieval = RetrievalHealth(
        status=raw.get("status", "uninitialized"),
        vectors_indexed=raw.get("vectors_indexed", 0),
        model_name=raw.get("model_name", "unknown"),
        embedding_dim=raw.get("embedding_dim", 0),
        cache_size=raw.get("cache_size", 0),
        cache_hits=raw.get("cache_hits", 0),
        cache_misses=raw.get("cache_misses", 0),
        bm25_sparse_index_ready=raw.get("bm25_sparse_index_ready", False),
    )

    return HealthResponse(
        status="ok",
        service="role3-rag-backend",
        retrieval=retrieval,
    )
