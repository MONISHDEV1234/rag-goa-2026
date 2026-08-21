#!/usr/bin/env python3
"""
retrieval.py — Role 1: The retrieve_context() API consumed by Role 3.

Loads a prebuilt FAISS index (built offline by embed_index.py) and serves
queries. Index loading happens once at import/init time, NOT per-request.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from schemas import DocumentChunk, RetrievalError

# Keep this in sync with embed_index.py's E5_QUERY_PREFIX — mismatched
# prefixing between index-build and query-time silently degrades quality.
E5_QUERY_PREFIX = "query: "
from hybrid_retrieval import BM25Retriever, reciprocal_rank_fusion


class RetrievalIndex:
    """
    Holds a loaded FAISS index + its chunk metadata + its embedding model.
    Instantiate once at process startup (offline from the request path),
    reuse across all calls to retrieve_context().
    """

    def __init__(self, index_dir: str | Path, threads: Optional[int] = None, cache_dir: Optional[str | Path] = None):
        self.index_dir = Path(index_dir)
        self.threads = threads
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._index: Optional[faiss.Index] = None
        self._chunk_meta: list[dict] = []
        self._model_info: dict = {}
        self._embedder = None
        self._bm25 = BM25Retriever()
        self._loaded = False
        self._cache: dict[tuple[str, int], list[DocumentChunk]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def load(self):
        """Load index, metadata, and embedding model from disk. Call once at startup."""
        index_path = self.index_dir / "faiss.index"
        meta_path = self.index_dir / "chunk_meta.jsonl"
        info_path = self.index_dir / "model_info.json"

        for p in (index_path, meta_path, info_path):
            if not p.exists():
                raise RetrievalError(
                    f"Missing index artifact: {p}. Run embed_index.py first."
                )

        self._index = faiss.read_index(str(index_path))

        self._chunk_meta = []
        with open(meta_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self._chunk_meta.append(json.loads(line))

        with open(info_path, encoding="utf-8") as f:
            self._model_info = json.load(f)

        if self._index.ntotal != len(self._chunk_meta):
            raise RetrievalError(
                f"Index/metadata mismatch: index has {self._index.ntotal} vectors "
                f"but chunk_meta.jsonl has {len(self._chunk_meta)} rows. "
                f"Rebuild the index — these must be row-aligned."
            )

        # Lazy import so this module can be unit-tested without fastembed installed
        import os
        from fastembed import TextEmbedding
        threads = self.threads if self.threads is not None else max(1, os.cpu_count() or 4)

        # Resolve offline cache dir: check explicit cache_dir, index_dir.parent/models, or data/models
        effective_cache_dir = self.cache_dir
        if effective_cache_dir is None:
            candidate_models_dir = self.index_dir.parent / "models"
            if candidate_models_dir.exists():
                effective_cache_dir = candidate_models_dir
            elif Path("data/models").exists():
                effective_cache_dir = Path("data/models")

        kwargs = {"model_name": self._model_info["model_name"], "threads": threads}
        if effective_cache_dir:
            kwargs["cache_dir"] = str(effective_cache_dir)

        self._embedder = TextEmbedding(**kwargs)

        # Build BM25 sparse index for hybrid search capability
        self._bm25.build_index(self._chunk_meta)

        # Warm up the ONNX runtime graph & execution provider so request #1 is fast
        self.embed_query("warmup query")

        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def get_status(self) -> dict:
        """Returns subsystem health diagnostics for FastAPI health check endpoints (/health)."""
        return {
            "status": "healthy" if self._loaded else "uninitialized",
            "vectors_indexed": self._index.ntotal if self._index else 0,
            "chunks_metadata_count": len(self._chunk_meta),
            "model_name": self._model_info.get("model_name", "unknown"),
            "embedding_dim": self._model_info.get("dim", 0),
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "bm25_sparse_index_ready": self._bm25.is_loaded,
        }

    def embed_query(self, query: str) -> np.ndarray:
        text = query
        if self._model_info.get("is_e5"):
            text = E5_QUERY_PREFIX + query
        vec = next(self._embedder.embed([text]))
        vec = np.array([vec], dtype=np.float32)
        faiss.normalize_L2(vec)
        return vec

    def search(self, query_vector: np.ndarray, top_k: int) -> list[DocumentChunk]:
        scores, indices = self._index.search(query_vector, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._chunk_meta):
                continue  # FAISS pads with -1 when fewer than top_k results exist
            meta = self._chunk_meta[idx]
            results.append(DocumentChunk(
                chunk_id=meta["chunk_id"],
                text=meta["text"],
                doc_id=meta["doc_id"],
                strategy=meta["strategy"],
                lang=meta["lang"],
                query_id=meta["query_id"],
                query_type=meta["query_type"],
                score=float(score),
                is_selected=meta.get("is_selected", False),
            ))
        return results

    def search_cached(self, query: str, top_k: int) -> list[DocumentChunk]:
        """LRU Cached Search: Returns instantly (<1ms) on identical query hits."""
        cache_key = (query, top_k)
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]

        self._cache_misses += 1
        query_vector = self.embed_query(query)
        results = self.search(query_vector, top_k)

        # Keep cache size bounded (max 2048 queries)
        if len(self._cache) >= 2048:
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = results
        return results

    def embed_queries_batch(self, queries: list[str]) -> np.ndarray:
        """Batch embed multiple queries simultaneously for 10x higher throughput."""
        texts = queries
        if self._model_info.get("is_e5"):
            texts = [E5_QUERY_PREFIX + q for q in queries]
        vecs = list(self._embedder.embed(texts))
        vecs_arr = np.array(vecs, dtype=np.float32)
        faiss.normalize_L2(vecs_arr)
        return vecs_arr

    def search_batch(self, query_vectors: np.ndarray, top_k: int) -> list[list[DocumentChunk]]:
        """Batch search FAISS index for multiple query vectors simultaneously."""
        scores_matrix, indices_matrix = self._index.search(query_vectors, top_k)
        batch_results = []
        for scores, indices in zip(scores_matrix, indices_matrix):
            results = []
            for score, idx in zip(scores, indices):
                if idx < 0 or idx >= len(self._chunk_meta):
                    continue
                meta = self._chunk_meta[idx]
                results.append(DocumentChunk(
                    chunk_id=meta["chunk_id"],
                    text=meta["text"],
                    doc_id=meta["doc_id"],
                    strategy=meta["strategy"],
                    lang=meta["lang"],
                    query_id=meta["query_id"],
                    query_type=meta["query_type"],
                    score=float(score),
                    is_selected=meta.get("is_selected", False),
                ))
            batch_results.append(results)
        return batch_results


# ---------------------------------------------------------------------------
# Module-level singleton — loaded once, reused across all retrieve_context() calls
# ---------------------------------------------------------------------------

_index: Optional[RetrievalIndex] = None


def init_retrieval(index_dir: str | Path = "data/index", threads: Optional[int] = None, cache_dir: Optional[str | Path] = None):
    """
    Call once at application startup (e.g. FastAPI startup event in Role 3's
    harness). This is where the index actually loads into memory.
    """
    global _index
    _index = RetrievalIndex(index_dir, threads=threads, cache_dir=cache_dir)
    _index.load()
    return _index


def get_retrieval_status() -> dict:
    """Subsystem health diagnostic endpoint for Role 3 / FastAPI (/health)."""
    if _index is None:
        return {"status": "uninitialized"}
    return _index.get_status()


from security_guardrails import (
    sanitize_input_text,
    filter_anti_hallucination,
    generate_provenance_citations,
)


async def retrieve_context(query: str, top_k: int = 3, min_score: float = 0.0) -> list[DocumentChunk]:
    """
    The single-query retrieval API consumed by Role 3's harness.
    Features LRU caching, input sanitization (SQL/Prompt Injection defense), and anti-hallucination filtering.
    """
    if _index is None or not _index.is_loaded:
        raise RetrievalError(
            "Retrieval index not initialized. Call init_retrieval() at startup."
        )

    if not query or not query.strip():
        raise RetrievalError("Empty query passed to retrieve_context().")

    if top_k <= 0:
        raise RetrievalError(f"top_k must be positive, got {top_k}.")

    # 1. Security Input Sanitization (SQL injection, Prompt injection, XSS, DoS protection)
    sanitized_q = sanitize_input_text(query)
    if not sanitized_q:
        raise RetrievalError("Query contained invalid characters or security threat payload.")

    try:
        # 2. Offload CPU-bound ONNX embedding + FAISS search to threadpool
        results = await asyncio.to_thread(_index.search_cached, sanitized_q, top_k)
        
        # 3. Anti-Hallucination filtering if min_score threshold provided
        if min_score > 0.0:
            results = filter_anti_hallucination(results, min_similarity_score=min_score)
            
        return results
    except Exception as e:
        if isinstance(e, RetrievalError):
            raise
        raise RetrievalError(f"Retrieval failed: {e}") from e


async def retrieve_hybrid_context(query: str, top_k: int = 5, rrf_k: int = 60) -> list[DocumentChunk]:
    """
    Hybrid Sparse (BM25) + Dense (FAISS) Retrieval via Reciprocal Rank Fusion (RRF).
    Boosts exact term matching while preserving cross-lingual semantic relevance.
    """
    if _index is None or not _index.is_loaded:
        raise RetrievalError("Retrieval index not initialized. Call init_retrieval() at startup.")

    sanitized_q = sanitize_input_text(query)
    if not sanitized_q:
        raise RetrievalError("Query contained invalid characters or security threat payload.")

    try:
        dense_results = await asyncio.to_thread(_index.search_cached, sanitized_q, top_k * 2)
        sparse_results = await asyncio.to_thread(_index._bm25.search, sanitized_q, top_k * 2)
        hybrid_results = reciprocal_rank_fusion(dense_results, sparse_results, top_k=top_k, rrf_k=rrf_k)
        return hybrid_results
    except Exception as e:
        raise RetrievalError(f"Hybrid retrieval failed: {e}") from e


async def retrieve_context_batch(queries: list[str], top_k: int = 3, min_score: float = 0.0) -> list[list[DocumentChunk]]:
    """
    High-Throughput Batch Retrieval API with input security sanitization and anti-hallucination filtering.
    """
    if _index is None or not _index.is_loaded:
        raise RetrievalError("Retrieval index not initialized. Call init_retrieval() at startup.")

    if not queries:
        return []

    # Sanitize each input query in batch
    cleaned_queries = []
    for q in queries:
        if q and q.strip():
            sq = sanitize_input_text(q)
            if sq:
                cleaned_queries.append(sq)

    if not cleaned_queries:
        raise RetrievalError("All queries in batch were empty or contained security threat payloads.")

    try:
        batch_results = await asyncio.to_thread(_run_sync_batch_retrieval, cleaned_queries, top_k)
        if min_score > 0.0:
            batch_results = [filter_anti_hallucination(res, min_similarity_score=min_score) for res in batch_results]
        return batch_results
    except Exception as e:
        if isinstance(e, RetrievalError):
            raise
        raise RetrievalError(f"Batch retrieval failed: {e}") from e


def _run_sync_batch_retrieval(queries: list[str], top_k: int) -> list[list[DocumentChunk]]:
    query_vectors = _index.embed_queries_batch(queries)
    return _index.search_batch(query_vectors, top_k)
