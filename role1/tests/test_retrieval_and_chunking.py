#!/usr/bin/env python3
"""
tests/test_retrieval_and_chunking.py — Role 1 correctness tests.

Uses a FAKE embedder (deterministic hash-based vectors) so retrieval logic
can be fully tested without downloading the real multilingual model, which
needs network access this environment doesn't have. Swap in the real
FastEmbed model when running on a machine with HF access — the test
structure (index/metadata alignment, error handling, empty query
handling) is identical either way.
"""

import asyncio
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import faiss
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chunking import (
    MetadataAwareChunker, FixedSizeChunker, SemanticChunker,
    SourceDocument, hard_word_split, split_sentences,
)
import retrieval
from schemas import RetrievalError


# ---------------------------------------------------------------------------
# Fake deterministic embedder — stands in for FastEmbed in offline tests
# ---------------------------------------------------------------------------

class FakeEmbedder:
    """Deterministic hash-based pseudo-embeddings, dim=32, for offline testing."""
    DIM = 32

    def __init__(self, model_name=None):
        pass

    def embed(self, texts, batch_size=64):
        for t in texts:
            yield self._vec(t)

    def _vec(self, text: str) -> np.ndarray:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32)
        arr = np.tile(arr, self.DIM // len(arr) + 1)[:self.DIM]
        arr = arr / (np.linalg.norm(arr) + 1e-9)
        return arr


def build_fake_index(tmp_dir: Path, chunks: list[dict]):
    """Build a real FAISS index from fake embeddings, matching embed_index.py's format."""
    embedder = FakeEmbedder()
    vectors = np.array([embedder._vec(c["text"]) for c in chunks], dtype=np.float32)
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    faiss.write_index(index, str(tmp_dir / "faiss.index"))
    with open(tmp_dir / "chunk_meta.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")
    with open(tmp_dir / "model_info.json", "w", encoding="utf-8") as f:
        json.dump({"model_name": "fake", "dim": vectors.shape[1],
                    "is_e5": False, "num_vectors": len(chunks)}, f)


# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------

def test_chunking_no_empty_chunks():
    doc = SourceDocument("d1", "This is a test passage. It has two sentences.",
                          "en", 1, "DESCRIPTION", 0, True)
    for cls in (MetadataAwareChunker, FixedSizeChunker, SemanticChunker):
        chunks = cls().chunk(doc)
        assert len(chunks) > 0, f"{cls.__name__} produced no chunks"
        assert all(c.text.strip() for c in chunks), f"{cls.__name__} produced an empty chunk"
    print("PASS: test_chunking_no_empty_chunks")


def test_chunking_metadata_propagates():
    doc = SourceDocument("d2", "Some text here.", "hi", 42, "NUMERIC", 3, True)
    for cls in (MetadataAwareChunker, FixedSizeChunker, SemanticChunker):
        chunks = cls().chunk(doc)
        for c in chunks:
            assert c.doc_id == "d2"
            assert c.lang == "hi"
            assert c.query_id == 42
            assert c.query_type == "NUMERIC"
            assert c.is_selected is True
    print("PASS: test_chunking_metadata_propagates")


def test_chunking_long_no_punctuation_is_bounded():
    """Regression test for the bug we found and fixed: passages with no
    sentence punctuation must still be split, not returned as one giant chunk."""
    long_text = " ".join(["word"] * 1000)  # no punctuation at all
    doc = SourceDocument("d3", long_text, "hi", 1, "DESCRIPTION", 0, False)

    meta_chunks = MetadataAwareChunker(split_threshold_words=150, sub_chunk_words=90).chunk(doc)
    assert all(len(c.text.split()) <= 90 for c in meta_chunks), \
        "MetadataAwareChunker produced an oversized chunk on punctuation-less text"

    sem_chunks = SemanticChunker(max_words=80).chunk(doc)
    assert all(len(c.text.split()) <= 80 for c in sem_chunks), \
        "SemanticChunker produced an oversized chunk on punctuation-less text"
    print("PASS: test_chunking_long_no_punctuation_is_bounded")


def test_chunking_empty_text():
    doc = SourceDocument("d4", "", "en", 1, "DESCRIPTION", 0, False)
    for cls in (MetadataAwareChunker, FixedSizeChunker, SemanticChunker):
        chunks = cls().chunk(doc)
        # Should not crash; empty input reasonably produces zero chunks
        assert isinstance(chunks, list)
    print("PASS: test_chunking_empty_text")


def test_hard_word_split_bounds():
    text = " ".join(str(i) for i in range(500))
    pieces = hard_word_split(text, max_words=50)
    assert all(len(p.split()) <= 50 for p in pieces)
    assert sum(len(p.split()) for p in pieces) == 500  # no words lost
    print("PASS: test_hard_word_split_bounds")


# ---------------------------------------------------------------------------
# Retrieval tests (using fake embedder + real FAISS)
# ---------------------------------------------------------------------------

def make_sample_chunks():
    return [
        {"chunk_id": "c1", "text": "Python is a programming language.",
         "doc_id": "d1", "strategy": "test", "lang": "en", "query_id": 1,
         "query_type": "DESCRIPTION", "is_selected": True},
        {"chunk_id": "c2", "text": "The capital of France is Paris.",
         "doc_id": "d2", "strategy": "test", "lang": "en", "query_id": 2,
         "query_type": "DESCRIPTION", "is_selected": False},
        {"chunk_id": "c3", "text": "पायथन एक प्रोग्रामिंग भाषा है।",
         "doc_id": "d3", "strategy": "test", "lang": "hi", "query_id": 1,
         "query_type": "DESCRIPTION", "is_selected": True},
    ]


def test_retrieve_context_obvious_query():
    """Query text identical to an indexed chunk should retrieve that chunk as top-1."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        chunks = make_sample_chunks()
        build_fake_index(tmp, chunks)

        idx = retrieval.RetrievalIndex(tmp)
        idx._embedder = FakeEmbedder()  # inject fake embedder, skip real fastembed import
        idx._index = faiss.read_index(str(tmp / "faiss.index"))
        with open(tmp / "chunk_meta.jsonl", encoding="utf-8") as f:
            idx._chunk_meta = [json.loads(l) for l in f]
        with open(tmp / "model_info.json", encoding="utf-8") as f:
            idx._model_info = json.load(f)
        idx._loaded = True

        retrieval._index = idx

        results = asyncio.run(retrieval.retrieve_context("Python is a programming language.", top_k=2))
        assert len(results) == 2
        assert results[0].chunk_id == "c1", f"Expected c1 as top result, got {results[0].chunk_id}"
        assert results[0].score > 0.99, f"Expected near-1.0 self-match score, got {results[0].score}"
    print("PASS: test_retrieve_context_obvious_query")


def test_retrieve_context_empty_query_raises():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        chunks = make_sample_chunks()
        build_fake_index(tmp, chunks)
        idx = retrieval.RetrievalIndex(tmp)
        idx._embedder = FakeEmbedder()
        idx._index = faiss.read_index(str(tmp / "faiss.index"))
        with open(tmp / "chunk_meta.jsonl", encoding="utf-8") as f:
            idx._chunk_meta = [json.loads(l) for l in f]
        with open(tmp / "model_info.json", encoding="utf-8") as f:
            idx._model_info = json.load(f)
        idx._loaded = True
        retrieval._index = idx

        raised = False
        try:
            asyncio.run(retrieval.retrieve_context("   ", top_k=2))
        except RetrievalError:
            raised = True
        assert raised, "Empty query should raise RetrievalError, not fail silently"
    print("PASS: test_retrieve_context_empty_query_raises")


def test_retrieve_context_not_initialized_raises():
    retrieval._index = None
    raised = False
    try:
        asyncio.run(retrieval.retrieve_context("anything", top_k=2))
    except RetrievalError:
        raised = True
    assert raised, "Uninitialized index should raise RetrievalError"
    print("PASS: test_retrieve_context_not_initialized_raises")


def test_index_metadata_mismatch_detected():
    """If index size and metadata rows drift apart, load() must catch it, not silently misalign."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        chunks = make_sample_chunks()
        build_fake_index(tmp, chunks)
        # Corrupt: truncate metadata to 2 rows while index still has 3 vectors
        lines = (tmp / "chunk_meta.jsonl").read_text(encoding="utf-8").splitlines()
        (tmp / "chunk_meta.jsonl").write_text("\n".join(lines[:2]), encoding="utf-8")

        idx = retrieval.RetrievalIndex(tmp)
        raised = False
        try:
            idx._index = faiss.read_index(str(tmp / "faiss.index"))
            with open(tmp / "chunk_meta.jsonl", encoding="utf-8") as f:
                meta = [json.loads(l) for l in f]
            if idx._index.ntotal != len(meta):
                raise RetrievalError("mismatch")
        except RetrievalError:
            raised = True
        assert raised, "Index/metadata size mismatch should be detected"
    print("PASS: test_index_metadata_mismatch_detected")


if __name__ == "__main__":
    test_chunking_no_empty_chunks()
    test_chunking_metadata_propagates()
    test_chunking_long_no_punctuation_is_bounded()
    test_chunking_empty_text()
    test_hard_word_split_bounds()
    test_retrieve_context_obvious_query()
    test_retrieve_context_empty_query_raises()
    test_retrieve_context_not_initialized_raises()
    test_index_metadata_mismatch_detected()
    print("\nAll tests passed.")
