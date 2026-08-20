#!/usr/bin/env python3
"""
benchmark.py — Role 1: Retrieval latency benchmark (P50/P70/P100).

Measures retrieve_context() latency ONLY — query embedding + FAISS search +
chunk lookup. Does NOT include STT (Role 2) or generation (Role 3). Run
this against a real built index (via embed_index.py) for real numbers.

Usage:
    python benchmark.py --index-dir data/index --eval-queries data/eval_queries.jsonl --n 50
"""

import argparse
import asyncio
import json
import time

import numpy as np
import pandas as pd

import retrieval
from schemas import RetrievalError


def load_eval_queries(path: str, n: int | None) -> list[dict]:
    queries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    if n:
        queries = queries[:n]
    return queries


async def run_benchmark(queries: list[dict], top_k: int = 3) -> list[dict]:
    records = []
    for q in queries:
        t0 = time.perf_counter()
        error = None
        n_results = 0
        try:
            results = await retrieval.retrieve_context(q["query"], top_k=top_k)
            n_results = len(results)
        except RetrievalError as e:
            error = str(e)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        records.append({
            "query": q["query"][:60],
            "lang": q.get("lang", "?"),
            "latency_ms": elapsed_ms,
            "n_results": n_results,
            "error": error,
        })
    return records


def report(records: list[dict]):
    df = pd.DataFrame(records)
    ok = df[df["error"].isna()]
    failed = df[df["error"].notna()]

    if len(ok) == 0:
        print("ALL QUERIES FAILED. Check index initialization. Sample errors:")
        print(failed.head(3).to_string())
        return

    latencies = ok["latency_ms"].values
    p50 = np.percentile(latencies, 50)
    p70 = np.percentile(latencies, 70)
    p100 = np.max(latencies)  # true max, not an interpolated percentile

    print("=" * 60)
    print("RETRIEVAL LATENCY BENCHMARK")
    print("=" * 60)
    print(f"Queries run       : {len(df)}")
    print(f"Succeeded         : {len(ok)}")
    print(f"Failed            : {len(failed)}")
    print(f"Mean latency      : {latencies.mean():.2f} ms")
    print(f"P50 latency       : {p50:.2f} ms")
    print(f"P70 latency       : {p70:.2f} ms")
    print(f"P100 (max) latency: {p100:.2f} ms")
    print(f"Min latency       : {latencies.min():.2f} ms")
    print()
    print("NOTE: this measures retrieve_context() only (query embedding +")
    print("FAISS search + metadata lookup). It does NOT include STT (Role 2)")
    print("or LLM generation (Role 3) — report those separately in the final")
    print("submission so the 200ms figure isn't misread as full pipeline latency.")

    if len(failed) > 0:
        print(f"\n{len(failed)} queries failed:")
        print(failed[["query", "lang", "error"]].head(5).to_string())

    by_lang = ok.groupby("lang")["latency_ms"].agg(["mean", "median", "count"])
    print("\nBy language:")
    print(by_lang.to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark retrieve_context() latency.")
    parser.add_argument("--index-dir", default="data/index")
    parser.add_argument("--eval-queries", default="data/eval_queries.jsonl")
    parser.add_argument("--n", type=int, default=50, help="Number of queries to benchmark")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    print(f"[benchmark] Loading index from {args.index_dir}")
    retrieval.init_retrieval(args.index_dir)

    print(f"[benchmark] Loading {args.n} eval queries from {args.eval_queries}")
    queries = load_eval_queries(args.eval_queries, args.n)

    print(f"[benchmark] Running {len(queries)} queries (top_k={args.top_k})...")
    records = asyncio.run(run_benchmark(queries, top_k=args.top_k))

    report(records)
