#!/usr/bin/env python3
"""
build_faiss_index.py — Builds faiss.index using sentence-transformers directly.
Uses the same MiniLM model as model_info.json, bypassing fastembed download issues.

Outputs (to data/index_minilm/):
  faiss.index       — the FAISS vector index
  chunk_meta.jsonl  — re-written chunk metadata (row-aligned to the index)
  model_info.json   — model metadata (overwritten to reflect final build)
"""

import json
import time
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # Cached locally — 384-dim, same as original
INPUT_CHUNKS = Path("data/index_minilm/chunk_meta.jsonl")
OUTPUT_DIR = Path("data/index_minilm")
BATCH_SIZE = 128

def load_chunks(path: Path) -> list[dict]:
    chunks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[build] Loading chunks from {INPUT_CHUNKS}")
    chunks = load_chunks(INPUT_CHUNKS)
    print(f"[build] {len(chunks)} chunks loaded")

    print(f"[build] Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    texts = [c["text"] for c in chunks]
    print(f"[build] Embedding {len(texts)} chunks (batch_size={BATCH_SIZE})...")

    t0 = time.time()
    vectors = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,  # L2 normalize = cosine similarity via inner product
        convert_to_numpy=True,
    )
    elapsed = time.time() - t0
    print(f"[build] Embedded {len(vectors)} chunks in {elapsed:.1f}s")

    vectors = vectors.astype(np.float32)
    dim = vectors.shape[1]
    print(f"[build] Vector dim={dim}, Building FAISS IndexFlatIP...")

    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    print(f"[build] FAISS index has {index.ntotal} vectors")

    # Write artifacts
    faiss.write_index(index, str(OUTPUT_DIR / "faiss.index"))
    print(f"[build] Written: {OUTPUT_DIR / 'faiss.index'}")

    with open(OUTPUT_DIR / "chunk_meta.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"[build] Written: {OUTPUT_DIR / 'chunk_meta.jsonl'}")

    with open(OUTPUT_DIR / "model_info.json", "w", encoding="utf-8") as f:
        json.dump({
            "model_name": MODEL_NAME,
            "dim": int(dim),
            "is_e5": False,
            "note": "Built with all-MiniLM-L6-v2 (cached locally). Same 384-dim as original.",
            "num_vectors": int(index.ntotal),
        }, f, indent=2)
    print(f"[build] Written: {OUTPUT_DIR / 'model_info.json'}")
    print(f"\n[build] Done! {index.ntotal} vectors, dim={dim}")
    print(f"[build] Set FAISS_INDEX_DIR=role1/data/index_minilm in your .env")

if __name__ == "__main__":
    main()
