#!/usr/bin/env python3
"""
embed_index.py — Role 1: Offline embedding + FAISS index build.

Embeds all chunks with a multilingual FastEmbed model and builds a
persisted FAISS index. This is an OFFLINE build step — never run inside
the request path. retrieval.py loads the artifacts this script produces.

Requires network access to Hugging Face to download the embedding model
on first run (cached locally after that).

Usage:
    python embed_index.py --chunks data/chunks/chunks_metadata_aware.jsonl \
                           --output-dir data/index

Outputs:
    <output-dir>/faiss.index       — the FAISS index
    <output-dir>/chunk_meta.jsonl  — chunk metadata, row-aligned to the index
    <output-dir>/model_info.json   — which embedding model + dim was used
"""

import argparse
import json
import time
from pathlib import Path

import faiss
import numpy as np

# Model choice: multilingual-e5-large is the primary target (best quality
# for cross-language En/Indic matching). Falls back to the smaller MiniLM
# multilingual model if the large one is too slow/heavy to load — this is
# a real tradeoff to make on your machine, not something to guess here.
PRIMARY_MODEL = "intfloat/multilingual-e5-large"
FALLBACK_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# e5 models expect this prefix convention for best retrieval quality.
# IMPORTANT: retrieval.py must use the same "query: " prefix on the query
# side — mismatched prefixing between index-build and query-time silently
# degrades retrieval quality without throwing any error, so keep this
# constant in one shared place if you refactor.
E5_PASSAGE_PREFIX = "passage: "
E5_QUERY_PREFIX = "query: "


def get_embedder(model_name: str):
    """
    Lazy import so this module can be imported/tested without fastembed
    installed (e.g. for anything that only needs the FAISS/index logic).
    """
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=model_name)


def is_e5_model(model_name: str) -> bool:
    return "e5" in model_name.lower()


def load_chunks(path: str | Path) -> list[dict]:
    chunks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def embed_chunks(chunks: list[dict], model_name: str, batch_size: int = 64) -> np.ndarray:
    embedder = get_embedder(model_name)
    texts = [c["text"] for c in chunks]
    if is_e5_model(model_name):
        texts = [E5_PASSAGE_PREFIX + t for t in texts]

    vectors = []
    t0 = time.time()
    # fastembed's .embed() already batches internally and returns a generator
    for vec in embedder.embed(texts, batch_size=batch_size):
        vectors.append(vec)
        if len(vectors) % 500 == 0:
            print(f"  embedded {len(vectors)}/{len(texts)}...")
    elapsed = time.time() - t0
    print(f"[embed] {len(vectors)} chunks embedded in {elapsed:.1f}s "
          f"({elapsed / max(len(vectors), 1) * 1000:.1f}ms/chunk)")

    return np.array(vectors, dtype=np.float32)


def build_faiss_index(vectors: np.ndarray) -> faiss.Index:
    """
    Normalize vectors and use inner-product search, which is equivalent
    to cosine similarity on normalized vectors — standard for sentence
    embedding retrieval.
    """
    dim = vectors.shape[1]
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index


def run(chunks_path: str, output_dir: str, model_name: str):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[embed_index] Loading chunks from {chunks_path}")
    chunks = load_chunks(chunks_path)
    print(f"[embed_index] {len(chunks)} chunks loaded")

    print(f"[embed_index] Embedding with {model_name}")
    vectors = embed_chunks(chunks, model_name)

    print("[embed_index] Building FAISS index")
    index = build_faiss_index(vectors)

    faiss.write_index(index, str(out / "faiss.index"))
    with open(out / "chunk_meta.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(out / "model_info.json", "w", encoding="utf-8") as f:
        json.dump({
            "model_name": model_name,
            "dim": int(vectors.shape[1]),
            "is_e5": is_e5_model(model_name),
            "num_vectors": int(vectors.shape[0]),
        }, f, indent=2)

    print(f"\n[embed_index] Done. Index has {index.ntotal} vectors, dim={vectors.shape[1]}")
    print(f"[embed_index] Artifacts written to {out}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed chunks and build FAISS index (offline).")
    parser.add_argument("--chunks", required=True, help="Path to a chunks_*.jsonl file")
    parser.add_argument("--output-dir", default="data/index")
    parser.add_argument("--model", default=PRIMARY_MODEL,
                         help=f"FastEmbed model name. Default: {PRIMARY_MODEL}. "
                              f"Fall back to '{FALLBACK_MODEL}' if too slow to load.")
    args = parser.parse_args()
    run(args.chunks, args.output_dir, args.model)
