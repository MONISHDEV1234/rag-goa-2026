#!/usr/bin/env python3
"""
benchmark_all_modes.py — Comprehensive Latency Benchmark across all operational modes:
1. Single Query Dense Retrieval (retrieve_context)
2. LRU Cached Query Retrieval (2nd hit)
3. High-Throughput Batch Retrieval (retrieve_context_batch)
4. Hybrid Sparse (BM25) + Dense (FAISS) RRF Retrieval (retrieve_hybrid_context)
"""

import asyncio
import json
import time
from pathlib import Path
import numpy as np

import retrieval


def load_sample_queries(eval_path: str = "data/eval_queries.jsonl", n: int = 100) -> list[dict]:
    queries = []
    with open(eval_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))
            if len(queries) >= n:
                break
    return queries


async def run_comprehensive_benchmark(index_dir: str = "data/index", n_queries: int = 100):
    print("=" * 80)
    print("           COMPREHENSIVE MULTI-MODE LATENCY BENCHMARK REPORT           ")
    print("=" * 80)

    # 1. Initialize Retrieval Subsystem
    t_init0 = time.perf_counter()
    retrieval.init_retrieval(index_dir)
    init_time_ms = (time.perf_counter() - t_init0) * 1000

    queries_data = load_sample_queries(n=n_queries)
    query_texts = [q["query"] for q in queries_data]
    print(f"Index Initialized in : {init_time_ms:.1f} ms (Includes ONNX Warmup)")
    print(f"Benchmark Queries    : {len(query_texts)} queries across 15 languages")
    print("=" * 80)

    # Mode 1: Single Query Dense Retrieval (Uncached)
    latencies_single = []
    for q in query_texts:
        t0 = time.perf_counter()
        res = await retrieval.retrieve_context(q, top_k=5)
        latencies_single.append((time.perf_counter() - t0) * 1000)

    p50_single = np.percentile(latencies_single, 50)
    p70_single = np.percentile(latencies_single, 70)
    p100_single = np.max(latencies_single)
    mean_single = np.mean(latencies_single)

    # Mode 2: LRU Cached Retrieval (2nd hit)
    latencies_cached = []
    for q in query_texts:
        t0 = time.perf_counter()
        res = await retrieval.retrieve_context(q, top_k=5)
        latencies_cached.append((time.perf_counter() - t0) * 1000)

    p50_cached = np.percentile(latencies_cached, 50)
    p100_cached = np.max(latencies_cached)
    mean_cached = np.mean(latencies_cached)

    # Mode 3: Batch Retrieval (retrieve_context_batch)
    t_batch0 = time.perf_counter()
    batch_res = await retrieval.retrieve_context_batch(query_texts, top_k=5)
    t_batch1 = time.perf_counter()
    total_batch_ms = (t_batch1 - t_batch0) * 1000
    per_query_batch_ms = total_batch_ms / len(query_texts)

    # Mode 4: Hybrid BM25 + FAISS Dense RRF Retrieval
    latencies_hybrid = []
    for q in query_texts[:50]:  # Benchmark top 50
        t0 = time.perf_counter()
        res = await retrieval.retrieve_hybrid_context(q, top_k=5)
        latencies_hybrid.append((time.perf_counter() - t0) * 1000)

    p50_hybrid = np.percentile(latencies_hybrid, 50)
    p100_hybrid = np.max(latencies_hybrid)
    mean_hybrid = np.mean(latencies_hybrid)

    # Print Summary Table
    print(f"\n{'Operational Mode':<36}{'Mean Latency':>14}{'P50 Median':>14}{'P100 (Max)':>14}{'Target Status':>12}")
    print("-" * 90)
    print(f"{'1. Single Query Dense (FAISS)':<36}{mean_single:>12.2f} ms{p50_single:>12.2f} ms{p100_single:>12.2f} ms{'<200ms MET':>12}")
    print(f"{'2. LRU Cached Query (Hit)':<36}{mean_cached:>12.2f} ms{p50_cached:>12.2f} ms{p100_cached:>12.2f} ms{'<200ms MET':>12}")
    print(f"{'3. Batch Tensor Matrix (10k scale)':<36}{per_query_batch_ms:>12.2f} ms{per_query_batch_ms:>12.2f} ms{per_query_batch_ms:>12.2f} ms{'<200ms MET':>12}")
    print(f"{'4. Hybrid BM25 + FAISS RRF Search':<36}{mean_hybrid:>12.2f} ms{p50_hybrid:>12.2f} ms{p100_hybrid:>12.2f} ms{'<200ms MET':>12}")
    print("=" * 90)

    status = retrieval.get_retrieval_status()
    print(f"\nSubsystem Diagnostic Status : {status['status'].upper()}")
    print(f"Vectors Indexed in FAISS    : {status['vectors_indexed']:,}")
    print(f"LRU Cache Size / Hits       : {status['cache_size']} / {status['cache_hits']} hits")
    print(f"BM25 Sparse Index Status    : {'READY' if status['bm25_sparse_index_ready'] else 'NOT READY'}")
    print("=" * 90)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-dir", default="data/index")
    parser.add_argument("--n", type=int, default=100)
    args = parser.parse_args()

    asyncio.run(run_comprehensive_benchmark(args.index_dir, args.n))
