#!/usr/bin/env python3
"""
evaluate.py — Role 1: Retrieval ACCURACY against ground truth.

MSMARCO-XI's is_selected flags give us free ground truth: for each eval
query, we know which exact passage is the correct answer. This measures
whether retrieve_context() actually finds it — Recall@K and MRR — across
all three chunking strategies, so we can report which chunking strategy
performs best with real numbers instead of a guess.

This is separate from benchmark.py (which measures speed, not correctness).

Usage:
    python evaluate.py --index-dir data/index --eval-queries data/eval_queries.jsonl
"""

import argparse
import asyncio
import json

import numpy as np

import retrieval


def load_eval_queries(path: str, n: int | None = None) -> list[dict]:
    queries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    if n:
        queries = queries[:n]
    return queries


async def evaluate(queries: list[dict], top_k: int = 5) -> dict:
    """
    For each query, retrieve top_k chunks and check whether any of them
    trace back to the ground-truth expected_doc_id (a chunk's doc_id field
    preserves which source passage it came from, even after splitting).

    Reports Recall@K (did the right doc appear anywhere in top_k) and
    MRR (how highly ranked was it, when found).
    """
    hits_at_k = {1: 0, 3: 0, 5: 0}
    reciprocal_ranks = []
    errors = 0

    for q in queries:
        try:
            results = await retrieval.retrieve_context(q["query"], top_k=top_k)
        except Exception:
            errors += 1
            reciprocal_ranks.append(0.0)
            continue

        expected = q["expected_doc_id"]
        rank = None
        for i, r in enumerate(results):
            if r.doc_id == expected:
                rank = i + 1
                break

        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        for k in hits_at_k:
            if rank is not None and rank <= k:
                hits_at_k[k] += 1

    n = len(queries)
    return {
        "n_queries": n,
        "errors": errors,
        "recall_at_1": hits_at_k[1] / n if n else 0,
        "recall_at_3": hits_at_k[3] / n if n else 0,
        "recall_at_5": hits_at_k[5] / n if n else 0,
        "mrr": float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0,
    }


def print_report(results_by_strategy: dict):
    print("=" * 70)
    print("RETRIEVAL ACCURACY — against ground-truth is_selected labels")
    print("=" * 70)
    print(f"{'Strategy':<18}{'Recall@1':>10}{'Recall@3':>10}{'Recall@5':>10}{'MRR':>10}{'Errors':>8}")
    for strategy, r in results_by_strategy.items():
        print(f"{strategy:<18}{r['recall_at_1']:>10.3f}{r['recall_at_3']:>10.3f}"
              f"{r['recall_at_5']:>10.3f}{r['mrr']:>10.3f}{r['errors']:>8d}")
    print()
    print("Recall@K = fraction of queries where the ground-truth passage appeared")
    print("in the top K retrieved chunks. MRR = mean reciprocal rank (1.0 = always")
    print("ranked first when found, 0 = never found).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate retrieval accuracy against ground truth.")
    parser.add_argument("--index-dir", default="data/index",
                         help="Single index dir, OR a comma-separated list of "
                              "'strategy=path' pairs to compare multiple strategies, "
                              "e.g. 'metadata_aware=data/index_meta,fixed_size=data/index_fixed'")
    parser.add_argument("--eval-queries", default="data/eval_queries.jsonl")
    parser.add_argument("--n", type=int, default=None, help="Limit number of eval queries")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    queries = load_eval_queries(args.eval_queries, args.n)
    print(f"[evaluate] {len(queries)} ground-truth eval queries loaded")

    results_by_strategy = {}
    if "=" in args.index_dir:
        pairs = [p.split("=", 1) for p in args.index_dir.split(",")]
    else:
        pairs = [("default", args.index_dir)]

    for strategy, path in pairs:
        print(f"[evaluate] Running against index: {strategy} ({path})")
        retrieval._index = None  # force reload for each index
        retrieval.init_retrieval(path)
        results_by_strategy[strategy] = asyncio.run(evaluate(queries, top_k=args.top_k))

    print_report(results_by_strategy)
