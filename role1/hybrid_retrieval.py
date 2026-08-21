#!/usr/bin/env python3
"""
hybrid_retrieval.py — Role 1: Hybrid Sparse (BM25) + Dense (FAISS) Retrieval via RRF.

Combines semantic dense vector search (multilingual-e5-large) with lexical
sparse keyword search (BM25) using Reciprocal Rank Fusion (RRF).
Boosts exact term matching (proper names, numbers, acronyms) while preserving
cross-lingual semantic relevance.
"""

import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

from schemas import DocumentChunk, RetrievalError


def tokenize_text(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric words."""
    if not text:
        return []
    return [w.lower() for w in re.findall(r"\w+", text)]


class BM25Retriever:
    """In-memory BM25 sparse keyword retriever."""

    def __init__(self):
        self.bm25: Optional[BM25Okapi] = None
        self.chunks: List[Dict[str, Any]] = []
        self._loaded = False

    def build_index(self, chunks: List[Dict[str, Any]]):
        """Build BM25 index over chunk metadata text."""
        self.chunks = chunks
        corpus_tokens = [tokenize_text(c["text"]) for c in chunks]
        self.bm25 = BM25Okapi(corpus_tokens)
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.bm25 is not None

    def search(self, query: str, top_k: int = 10) -> List[DocumentChunk]:
        """Rank chunks by BM25 keyword relevance score."""
        if not self.is_loaded:
            return []

        q_tokens = tokenize_text(query)
        if not q_tokens:
            return []

        scores = self.bm25.get_scores(q_tokens)
        top_indices = scores.argsort()[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            meta = self.chunks[idx]
            results.append(DocumentChunk(
                chunk_id=meta["chunk_id"],
                text=meta["text"],
                doc_id=meta["doc_id"],
                strategy=meta["strategy"],
                lang=meta["lang"],
                query_id=meta["query_id"],
                query_type=meta["query_type"],
                score=score,
                is_selected=meta.get("is_selected", False),
            ))
        return results


def reciprocal_rank_fusion(
    dense_chunks: List[DocumentChunk],
    sparse_chunks: List[DocumentChunk],
    top_k: int = 5,
    rrf_k: int = 60,
) -> List[DocumentChunk]:
    """
    Reciprocal Rank Fusion (RRF) algorithm:
    RRF_score(doc) = sum(1.0 / (rrf_k + rank_i))
    Combines dense FAISS rankings and sparse BM25 rankings into an optimal unified list.
    """
    rrf_scores: Dict[str, float] = {}
    chunk_map: Dict[str, DocumentChunk] = {}

    # 1. Score Dense Ranks
    for rank, chunk in enumerate(dense_chunks, 1):
        cid = chunk.chunk_id
        chunk_map[cid] = chunk
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

    # 2. Score Sparse Ranks
    for rank, chunk in enumerate(sparse_chunks, 1):
        cid = chunk.chunk_id
        if cid not in chunk_map:
            chunk_map[cid] = chunk
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

    # 3. Sort by aggregated RRF score
    sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]

    # 4. Construct hybrid DocumentChunk objects with RRF score
    hybrid_results = []
    for cid in sorted_cids:
        c = chunk_map[cid]
        combined_score = float(rrf_scores[cid])
        hybrid_results.append(DocumentChunk(
            chunk_id=c.chunk_id,
            text=c.text,
            doc_id=c.doc_id,
            strategy=c.strategy,
            lang=c.lang,
            query_id=c.query_id,
            query_type=c.query_type,
            score=combined_score,
            is_selected=c.is_selected,
        ))

    return hybrid_results
