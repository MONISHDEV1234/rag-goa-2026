#!/usr/bin/env python3
"""
retriever.py — Role 1's retrieve_context() API, integrated into role3_backend.

Ported from role1/retrieval.py. All imports updated to use app.schemas
(the unified Role 3 contract). The public API surface is unchanged:

    from app.retrieval.retriever import init_retrieval, retrieve_context, get_retrieval_status

    # Once, at FastAPI startup:
    init_retrieval("data/index")

    # Per request:
    chunks = await retrieve_context(query, top_k=3)

The FAISS index is loaded once at startup (init_retrieval) and kept in memory.
Never rebuilt or reloaded per request.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from app.schemas import DocumentChunk, RetrievalError
from app.retrieval.hybrid_retrieval import BM25Retriever, reciprocal_rank_fusion
from app.retrieval.security_guardrails import (
    sanitize_input_text,
    filter_anti_hallucination,
    generate_provenance_citations,
)

# Keep in sync with embed_index.py's E5_QUERY_PREFIX — mismatched prefixing
# between index-build and query-time silently degrades quality.
E5_QUERY_PREFIX = "query: "
_CACHE_MAX_SIZE = 2048


class HFInferenceEmbedder:
    """
    Zero-RAM embedding backend: calls HuggingFace Inference API instead of
    loading a local ONNX model. Uses the same model as the FAISS index was
    built with, so all 384-dim vectors remain compatible.

    Set HF_INFERENCE_TOKEN env var to enable. Free tier is rate-limited but
    sufficient for hackathon demos. Eliminates the ~300MB ONNX runtime RAM cost.
    """

    def __init__(self, model_name: str, token: str):
        self.model_name = model_name
        self.token = token
        self._api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_name}"

    def embed(self, texts: list[str]):
        """Call HF API and yield embedding vectors (compatible with fastembed interface)."""
        import httpx
        import numpy as np
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"inputs": texts, "options": {"wait_for_model": True}}
        resp = httpx.post(self._api_url, json=payload, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        # HF returns list[list[float]] for batch or list[float] for single
        if isinstance(data[0], float):
            data = [data]
        for vec in data:
            yield np.array(vec, dtype=np.float32)


class RetrievalIndex:
    """
    Holds a loaded FAISS index + chunk metadata + embedding model.
    Instantiate once at process startup; reuse across all retrieve_context() calls.
    """

    def __init__(
        self,
        index_dir: str | Path,
        threads: Optional[int] = None,
        cache_dir: Optional[str | Path] = None,
    ):
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
        import faiss  # lazy import — only needed at startup, not on every test import
        import numpy as np
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
        from fastembed import TextEmbedding

        threads = self.threads if self.threads is not None else 1

        # Resolve offline model cache dir
        # Priority: FASTEMBED_CACHE_PATH env (Docker baked) > explicit cache_dir > index_dir.parent/models > temp
        FASTEMBED_CACHE_PATH = os.environ.get("FASTEMBED_CACHE_PATH")
        FASTEMBED_TEMP_CACHE = Path(os.environ.get("TEMP", "/tmp")) / "fastembed_cache"
        effective_cache_dir = self.cache_dir
        if effective_cache_dir is None:
            if FASTEMBED_CACHE_PATH and Path(FASTEMBED_CACHE_PATH).exists():
                # Use the model baked into the Docker image at build time
                effective_cache_dir = Path(FASTEMBED_CACHE_PATH)
            else:
                candidate = self.index_dir.parent / "models"
                if candidate.exists():
                    effective_cache_dir = candidate
                elif FASTEMBED_TEMP_CACHE.exists():
                    effective_cache_dir = FASTEMBED_TEMP_CACHE
                elif Path("data/models").exists():
                    effective_cache_dir = Path("data/models")

        # Set HF_HUB_OFFLINE=1 when we have a local cache to avoid
        # slow network calls just to check for model updates at startup
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
        if effective_cache_dir and effective_cache_dir.exists():
            os.environ.setdefault("HF_HUB_OFFLINE", "1")

        # Build BM25 sparse index for instant keyword search and low-memory fallback
        self._bm25.build_index(self._chunk_meta)

        self._embedder = None
        model_name = self._model_info.get("model_name", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

        # ── Embedder selection (in priority order) ───────────────────────────────
        # 1. HF Inference API — zero local RAM, free, same model/dimensions
        hf_token = os.environ.get("HF_INFERENCE_TOKEN", "")
        if hf_token and os.environ.get("DISABLE_ONNX_EMBEDDER", "0") != "1":
            try:
                import logging
                _hf_embedder = HFInferenceEmbedder(model_name=model_name, token=hf_token)
                # Smoke-test: embed a short string to verify connectivity
                list(_hf_embedder.embed(["test"]))
                self._embedder = _hf_embedder
                logging.getLogger("retriever").info(
                    "[Embedder] Using HF Inference API (%s) — zero local RAM.", model_name
                )
                print(f"[Role 3] Embedder: HF Inference API ({model_name})")
            except Exception as hf_err:
                import logging
                logging.getLogger("retriever").warning(
                    "HF Inference API unavailable (%s), falling back to local ONNX.", hf_err
                )

        # 2. Local ONNX via fastembed — ~300MB RAM, fast vector embeddings
        if self._embedder is None and os.environ.get("DISABLE_ONNX_EMBEDDER", "0") != "1":
            try:
                if effective_cache_dir and effective_cache_dir.exists():
                    os.environ["FASTEMBED_CACHE_PATH"] = str(effective_cache_dir)
                self._embedder = TextEmbedding(model_name=model_name, threads=threads)
                # Warm up ONNX runtime
                self.embed_query("warmup query")
                print(f"[Role 3] Embedder: local ONNX ({model_name})")
            except Exception as err:
                import logging
                logging.getLogger("retriever").warning(
                    f"Dense ONNX embedder could not be loaded ({err}). "
                    "Running in BM25-only mode (~60MB RAM)."
                )
                self._embedder = None

        # 3. BM25 only — keyword search fallback, minimal RAM
        if self._embedder is None:
            print("[Role 3] Embedder: BM25 keyword-only mode (no dense embedder available)")

        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def get_status(self) -> dict:
        """Returns subsystem health diagnostics for the /health endpoint."""
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

    def embed_query(self, query: str):
        import faiss
        import numpy as np
        text = query
        if self._model_info.get("is_e5"):
            text = E5_QUERY_PREFIX + query
        vec = next(self._embedder.embed([text]))
        vec = np.array([vec], dtype=np.float32)
        faiss.normalize_L2(vec)
        return vec

    def search(self, query_vector, top_k: int) -> list[DocumentChunk]:
        scores, indices = self._index.search(query_vector, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._chunk_meta):
                continue
            meta = self._chunk_meta[idx]
            raw_qid = meta.get("query_id")
            qid_int = int(raw_qid) if (isinstance(raw_qid, (int, float)) or (isinstance(raw_qid, str) and raw_qid.isdigit())) else None
            results.append(DocumentChunk(
                chunk_id=str(meta.get("chunk_id", f"chunk_{idx}")),
                text=meta.get("text", ""),
                doc_id=str(meta.get("doc_id", f"doc_{idx}")),
                strategy=str(meta.get("strategy", "semantic")),
                lang=str(meta.get("lang", "en")),
                query_id=qid_int,
                query_type=str(meta.get("query_type", "general")) if meta.get("query_type") else None,
                similarity_score=float(score),
                score=float(score),
                is_selected=bool(meta.get("is_selected", False)),
            ))
        return results

    def search_cached(self, query: str, top_k: int) -> list[DocumentChunk]:
        """LRU-Cached Search: returns instantly (<1 ms) on identical query hits."""
        cache_key = (query, top_k)
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]

        self._cache_misses += 1
        if self._embedder is not None and self._index is not None:
            try:
                query_vector = self.embed_query(query)
                results = self.search(query_vector, top_k)
            except Exception:
                results = self._bm25.search(query, top_k)
        else:
            results = self._bm25.search(query, top_k)

        # Bound cache size to prevent unbounded memory growth
        if len(self._cache) >= _CACHE_MAX_SIZE:
            # Evict oldest entry (simple FIFO)
            oldest = next(iter(self._cache))
            del self._cache[oldest]

        self._cache[cache_key] = results
        return results

    def embed_queries_batch(self, queries: list[str]):
        """Batch-embed multiple queries simultaneously for higher throughput."""
        import faiss
        import numpy as np
        texts = queries
        if self._model_info.get("is_e5"):
            texts = [E5_QUERY_PREFIX + q for q in queries]
        vecs = list(self._embedder.embed(texts))
        vecs_arr = np.array(vecs, dtype=np.float32)
        faiss.normalize_L2(vecs_arr)
        return vecs_arr

    def search_batch(self, query_vectors, top_k: int) -> list[list[DocumentChunk]]:
        scores, indices = self._index.search(query_vectors, top_k)
        batch_results = []
        for batch_scores, batch_indices in zip(scores, indices):
            results = []
            for score, idx in zip(batch_scores, batch_indices):
                if idx < 0 or idx >= len(self._chunk_meta):
                    continue
                meta = self._chunk_meta[idx]
                raw_qid = meta.get("query_id")
                qid_int = int(raw_qid) if (isinstance(raw_qid, (int, float)) or (isinstance(raw_qid, str) and raw_qid.isdigit())) else None
                results.append(DocumentChunk(
                    chunk_id=str(meta.get("chunk_id", f"chunk_{idx}")),
                    text=meta.get("text", ""),
                    doc_id=str(meta.get("doc_id", f"doc_{idx}")),
                    strategy=str(meta.get("strategy", "semantic")),
                    lang=str(meta.get("lang", "en")),
                    query_id=qid_int,
                    query_type=str(meta.get("query_type", "general")) if meta.get("query_type") else None,
                    similarity_score=float(score),
                    score=float(score),
                    is_selected=bool(meta.get("is_selected", False)),
                ))
            batch_results.append(results)
        return batch_results


# ---------------------------------------------------------------------------
# Module-level singleton — loaded once, reused across all retrieve_context() calls
# ---------------------------------------------------------------------------

_index: Optional[RetrievalIndex] = None


def init_retrieval(
    index_dir: str | Path = "data/index",
    threads: Optional[int] = None,
    cache_dir: Optional[str | Path] = None,
) -> RetrievalIndex:
    """
    Call once at FastAPI startup (lifespan handler in main.py).
    Loads the FAISS index, metadata, and embedding model into memory.
    Do NOT call this per-request.
    """
    global _index
    _index = RetrievalIndex(index_dir, threads=threads, cache_dir=cache_dir)
    _index.load()
    return _index


def get_retrieval_status() -> dict:
    """Subsystem health diagnostic for the /health endpoint."""
    if _index is None:
        return {"status": "uninitialized"}
    return _index.get_status()


async def retrieve_context(
    query: str,
    top_k: int = 3,
    min_score: float = 0.0,
) -> list[DocumentChunk]:
    """
    The single-query retrieval API consumed by Role 3's orchestrator.

    Features:
      - LRU caching (identical queries return instantly)
      - Input sanitization (SQL injection / prompt injection / XSS defense)
      - Anti-hallucination score filtering (when min_score > 0)
      - CPU-bound ONNX embedding offloaded to threadpool via asyncio.to_thread

    Raises RetrievalError on all failure conditions.
    Returns [] when the query is valid but no sufficiently similar chunks exist.
    """
    if _index is None or not _index.is_loaded:
        raise RetrievalError(
            "Retrieval index not initialized. Call init_retrieval() at startup."
        )

    if not query or not query.strip():
        raise RetrievalError("Empty query passed to retrieve_context().")

    if top_k <= 0:
        raise RetrievalError(f"top_k must be positive, got {top_k}.")

    # Security sanitization
    sanitized_q = sanitize_input_text(query)
    if not sanitized_q:
        raise RetrievalError(
            "Query contained invalid characters or a security threat payload."
        )

    try:
        dense_results = await asyncio.to_thread(_index.search_cached, sanitized_q, top_k * 2)
        sparse_results = await asyncio.to_thread(_index._bm25.search, sanitized_q, top_k * 2)
        results = reciprocal_rank_fusion(dense_results, sparse_results, top_k=top_k, rrf_k=60)

        # Anti-hallucination filtering when min_score threshold is provided
        if min_score > 0.0:
            results = filter_anti_hallucination(results, min_similarity_score=min_score)

        return results
    except Exception as e:
        if isinstance(e, RetrievalError):
            raise
        raise RetrievalError(f"Retrieval failed: {e}") from e


async def retrieve_hybrid_context(
    query: str,
    top_k: int = 5,
    rrf_k: int = 60,
) -> list[DocumentChunk]:
    """
    Hybrid Sparse (BM25) + Dense (FAISS) Retrieval via Reciprocal Rank Fusion.
    Boosts exact term matching while preserving cross-lingual semantic relevance.
    """
    if _index is None or not _index.is_loaded:
        raise RetrievalError(
            "Retrieval index not initialized. Call init_retrieval() at startup."
        )

    sanitized_q = sanitize_input_text(query)
    if not sanitized_q:
        raise RetrievalError(
            "Query contained invalid characters or a security threat payload."
        )

    try:
        dense_results = await asyncio.to_thread(_index.search_cached, sanitized_q, top_k * 2)
        sparse_results = await asyncio.to_thread(_index._bm25.search, sanitized_q, top_k * 2)
        return reciprocal_rank_fusion(dense_results, sparse_results, top_k=top_k, rrf_k=rrf_k)
    except Exception as e:
        raise RetrievalError(f"Hybrid retrieval failed: {e}") from e


async def retrieve_context_batch(
    queries: list[str],
    top_k: int = 3,
    min_score: float = 0.0,
) -> list[list[DocumentChunk]]:
    """
    High-throughput batch retrieval API.
    Sanitizes each query individually; raises RetrievalError if all fail sanity checks.
    """
    if _index is None or not _index.is_loaded:
        raise RetrievalError(
            "Retrieval index not initialized. Call init_retrieval() at startup."
        )

    if not queries:
        return []

    cleaned_queries = []
    for q in queries:
        if q and q.strip():
            sq = sanitize_input_text(q)
            if sq:
                cleaned_queries.append(sq)

    if not cleaned_queries:
        raise RetrievalError(
            "All queries in batch were empty or contained security threat payloads."
        )

    try:
        batch_results = await asyncio.to_thread(
            _run_sync_batch_retrieval, cleaned_queries, top_k
        )
        if min_score > 0.0:
            batch_results = [
                filter_anti_hallucination(res, min_similarity_score=min_score)
                for res in batch_results
            ]
        return batch_results
    except Exception as e:
        if isinstance(e, RetrievalError):
            raise
        raise RetrievalError(f"Batch retrieval failed: {e}") from e


def _run_sync_batch_retrieval(
    queries: list[str], top_k: int
) -> list[list[DocumentChunk]]:
    query_vectors = _index.embed_queries_batch(queries)
    return _index.search_batch(query_vectors, top_k)
