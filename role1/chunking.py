#!/usr/bin/env python3
"""
chunking.py — Role 1: Multi-strategy chunking for retrieval-ready documents.

Passage length in this corpus is bimodal: most passages are short
(median ~43 words) and are already natural retrieval units, but a real
long tail exists (up to 1400+ words) that needs splitting. The three
strategies below are designed around that reality rather than applied
blindly:

  1. MetadataAwareChunker  — treats each source passage as one chunk when
     it's already a coherent unit (uses existing structure: query_id,
     passage_idx, language, is_selected — the dataset's natural
     boundaries), only falling back to splitting when a passage is long
     enough that a single chunk would hurt retrieval precision.
  2. FixedSizeChunker      — word-count sliding window with overlap.
     Baseline strategy, useful on the long-tail passages and as a
     comparison point for the others.
  3. SemanticChunker       — splits on sentence boundaries, packing
     sentences up to a max chunk size, so we never cut mid-sentence.

All three share a common interface (`Chunker.chunk(document) -> list[Chunk]`)
so they can be run independently, compared, or combined.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SourceDocument:
    """One row from documents.jsonl (a single passage from ingest.py)."""
    doc_id: str
    text: str
    lang: str
    query_id: int
    query_type: str
    passage_idx: int
    is_selected: bool

    @classmethod
    def from_dict(cls, d: dict) -> "SourceDocument":
        return cls(
            doc_id=d["doc_id"], text=d["text"], lang=d["lang"],
            query_id=d["query_id"], query_type=d["query_type"],
            passage_idx=d["passage_idx"], is_selected=d["is_selected"],
        )


@dataclass
class Chunk:
    """A retrieval-ready unit produced by a chunking strategy."""
    chunk_id: str
    text: str
    doc_id: str          # source document this chunk came from
    strategy: str         # which chunker produced this
    lang: str
    query_id: int
    query_type: str
    passage_idx: int
    is_selected: bool
    chunk_idx: int = 0    # position within the source document (0 if not split)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Shared tokenization helpers
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?।॥])\s+")
# includes Devanagari danda (।) and double danda (॥) as sentence terminators,
# since several Indic scripts in this corpus use them instead of/alongside '.'


def split_sentences(text: str) -> list[str]:
    sentences = _SENTENCE_SPLIT_RE.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def word_count(text: str) -> int:
    return len(text.split())


def hard_word_split(text: str, max_words: int, overlap: int = 0) -> list[str]:
    """
    Fallback splitter for text with no usable sentence punctuation
    (common in noisy scraped passages — repeated phrases, no periods).
    Guarantees every returned piece is <= max_words, regardless of
    punctuation quality.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text]
    step = max(max_words - overlap, 1)
    pieces = []
    start = 0
    while start < len(words):
        pieces.append(" ".join(words[start:start + max_words]))
        start += step
    return pieces


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------

class Chunker:
    name: str = "base"

    def chunk(self, doc: SourceDocument) -> list[Chunk]:
        raise NotImplementedError

    def chunk_all(self, docs: Iterable[SourceDocument]) -> list[Chunk]:
        out = []
        for doc in docs:
            out.extend(self.chunk(doc))
        return out


# ---------------------------------------------------------------------------
# Strategy 1: Metadata-aware
# ---------------------------------------------------------------------------

class MetadataAwareChunker(Chunker):
    """
    Respects the dataset's existing structure: each passage (query_id +
    passage_idx + lang) is already a coherent, independently-retrievable
    unit as defined by the corpus itself. Only splits when a passage is
    long enough that returning it whole would hurt retrieval precision
    (a single chunk covering many distinct sub-topics).
    """
    name = "metadata_aware"

    def __init__(self, split_threshold_words: int = 150, sub_chunk_words: int = 90):
        self.split_threshold_words = split_threshold_words
        self.sub_chunk_words = sub_chunk_words

    def chunk(self, doc: SourceDocument) -> list[Chunk]:
        wc = word_count(doc.text)
        if wc <= self.split_threshold_words:
            return [Chunk(
                chunk_id=f"{doc.doc_id}::meta::0",
                text=doc.text, doc_id=doc.doc_id, strategy=self.name,
                lang=doc.lang, query_id=doc.query_id, query_type=doc.query_type,
                passage_idx=doc.passage_idx, is_selected=doc.is_selected,
                chunk_idx=0,
            )]

        # Long passage: fall back to sentence-packed sub-chunks, but still
        # tag them under the metadata-aware strategy since the split point
        # is still driven by the passage's own natural sentence structure.
        sentences = split_sentences(doc.text)
        chunks, current, current_wc, idx = [], [], 0, 0
        for sent in sentences:
            sw = word_count(sent)
            # A single "sentence" can itself be huge if the passage has no
            # real punctuation (noisy scraped text) — hard-split it so one
            # sentence can never become an oversized chunk on its own.
            if sw > self.sub_chunk_words:
                if current:
                    chunks.append(self._make_chunk(doc, " ".join(current), idx))
                    idx += 1
                    current, current_wc = [], 0
                for piece in hard_word_split(sent, self.sub_chunk_words):
                    chunks.append(self._make_chunk(doc, piece, idx))
                    idx += 1
                continue
            if current and current_wc + sw > self.sub_chunk_words:
                chunks.append(self._make_chunk(doc, " ".join(current), idx))
                idx += 1
                current, current_wc = [], 0
            current.append(sent)
            current_wc += sw
        if current:
            chunks.append(self._make_chunk(doc, " ".join(current), idx))
        return chunks

    def _make_chunk(self, doc, text, idx) -> Chunk:
        return Chunk(
            chunk_id=f"{doc.doc_id}::meta::{idx}",
            text=text, doc_id=doc.doc_id, strategy=self.name,
            lang=doc.lang, query_id=doc.query_id, query_type=doc.query_type,
            passage_idx=doc.passage_idx, is_selected=doc.is_selected,
            chunk_idx=idx,
        )


# ---------------------------------------------------------------------------
# Strategy 2: Fixed-size with overlap
# ---------------------------------------------------------------------------

class FixedSizeChunker(Chunker):
    """Word-count sliding window with configurable overlap. Baseline."""
    name = "fixed_size"

    def __init__(self, window_words: int = 60, overlap_words: int = 15):
        assert overlap_words < window_words, "overlap must be smaller than window"
        self.window_words = window_words
        self.overlap_words = overlap_words

    def chunk(self, doc: SourceDocument) -> list[Chunk]:
        words = doc.text.split()
        if len(words) <= self.window_words:
            return [Chunk(
                chunk_id=f"{doc.doc_id}::fixed::0",
                text=doc.text, doc_id=doc.doc_id, strategy=self.name,
                lang=doc.lang, query_id=doc.query_id, query_type=doc.query_type,
                passage_idx=doc.passage_idx, is_selected=doc.is_selected,
                chunk_idx=0,
            )]

        step = self.window_words - self.overlap_words
        chunks = []
        idx = 0
        start = 0
        while start < len(words):
            window = words[start:start + self.window_words]
            if not window:
                break
            chunks.append(Chunk(
                chunk_id=f"{doc.doc_id}::fixed::{idx}",
                text=" ".join(window), doc_id=doc.doc_id, strategy=self.name,
                lang=doc.lang, query_id=doc.query_id, query_type=doc.query_type,
                passage_idx=doc.passage_idx, is_selected=doc.is_selected,
                chunk_idx=idx,
            ))
            idx += 1
            start += step
        return chunks


# ---------------------------------------------------------------------------
# Strategy 3: Semantic (sentence-boundary) splitting
# ---------------------------------------------------------------------------

class SemanticChunker(Chunker):
    """
    Packs whole sentences into chunks up to max_words, never cutting
    mid-sentence. Unlike MetadataAwareChunker, this applies uniformly
    regardless of passage length, and has no notion of a "keep as-is"
    threshold — useful as a genuinely different comparison strategy.
    """
    name = "semantic"

    def __init__(self, max_words: int = 80):
        self.max_words = max_words

    def chunk(self, doc: SourceDocument) -> list[Chunk]:
        sentences = split_sentences(doc.text)
        if not sentences:
            return []

        chunks, current, current_wc, idx = [], [], 0, 0
        for sent in sentences:
            sw = word_count(sent)
            if sw > self.max_words:
                if current:
                    chunks.append(self._make_chunk(doc, " ".join(current), idx))
                    idx += 1
                    current, current_wc = [], 0
                for piece in hard_word_split(sent, self.max_words):
                    chunks.append(self._make_chunk(doc, piece, idx))
                    idx += 1
                continue
            if current and current_wc + sw > self.max_words:
                chunks.append(self._make_chunk(doc, " ".join(current), idx))
                idx += 1
                current, current_wc = [], 0
            current.append(sent)
            current_wc += sw
        if current:
            chunks.append(self._make_chunk(doc, " ".join(current), idx))
        return chunks

    def _make_chunk(self, doc, text, idx) -> Chunk:
        return Chunk(
            chunk_id=f"{doc.doc_id}::sem::{idx}",
            text=text, doc_id=doc.doc_id, strategy=self.name,
            lang=doc.lang, query_id=doc.query_id, query_type=doc.query_type,
            passage_idx=doc.passage_idx, is_selected=doc.is_selected,
            chunk_idx=idx,
        )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_documents(path: str | Path) -> list[SourceDocument]:
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            docs.append(SourceDocument.from_dict(json.loads(line)))
    return docs


def write_chunks(chunks: list[Chunk], path: str | Path):
    with open(path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")


STRATEGIES = {
    "metadata_aware": MetadataAwareChunker,
    "fixed_size": FixedSizeChunker,
    "semantic": SemanticChunker,
}


def run_all_strategies(docs: list[SourceDocument]) -> dict[str, list[Chunk]]:
    results = {}
    for name, cls in STRATEGIES.items():
        chunker = cls()
        results[name] = chunker.chunk_all(docs)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run chunking strategies over documents.jsonl")
    parser.add_argument("--input", default="data/documents.jsonl")
    parser.add_argument("--output-dir", default="data/chunks")
    args = parser.parse_args()

    docs = load_documents(args.input)
    print(f"[chunking] Loaded {len(docs)} source documents")

    results = run_all_strategies(docs)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("CHUNKING COMPARISON")
    print("=" * 60)
    for name, chunks in results.items():
        lens = [word_count(c.text) for c in chunks]
        avg_len = sum(lens) / len(lens) if lens else 0
        out_path = out_dir / f"chunks_{name}.jsonl"
        write_chunks(chunks, out_path)
        print(f"{name:16s}: {len(chunks):5d} chunks | avg {avg_len:5.1f} words "
              f"| min {min(lens) if lens else 0} | max {max(lens) if lens else 0} "
              f"-> {out_path}")
