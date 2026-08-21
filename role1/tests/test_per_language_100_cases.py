#!/usr/bin/env python3
"""
tests/test_per_language_100_cases.py — Role 1 Language-Specific Comprehensive Test Suite.

Evaluates exactly 100 real ground-truth test cases FOR EACH AND EVERY ONE OF THE 15 LANGUAGES
(15 * 100 = 1,500 total test cases) against the real retrieval subsystem.

Reports per-language accuracy (Recall@1, Recall@3, Recall@5, MRR), latency, and edge cases.
"""

import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

# Ensure parent path is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import retrieval
from schemas import RetrievalError


ALL_LANGUAGES = [
    "en", "hi", "bn", "ta", "te", "mr", "gu",
    "kn", "ml", "pa", "or", "as", "ne", "sa", "ur"
]

LANG_NAMES = {
    "en": "English", "hi": "Hindi", "bn": "Bengali", "ta": "Tamil",
    "te": "Telugu", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "or": "Odia", "as": "Assamese",
    "ne": "Nepali", "sa": "Sanskrit", "ur": "Urdu"
}


def load_100_test_cases_per_language(eval_path: str = "data/eval_queries.jsonl") -> dict[str, list[dict]]:
    """Loads 100 distinct ground-truth test cases per language from eval_queries.jsonl."""
    by_lang = defaultdict(list)
    with open(eval_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            q = json.loads(line)
            lang = q.get("lang")
            if lang in ALL_LANGUAGES and len(by_lang[lang]) < 100:
                by_lang[lang].append(q)

    # Verify every language has at least 100 test cases
    for l in ALL_LANGUAGES:
        count = len(by_lang[l])
        if count < 100:
            print(f"Warning: Language '{l}' has {count} test cases (expected 100).")
    return by_lang


async def run_language_test_suite(test_cases_by_lang: dict[str, list[dict]], top_k: int = 5):
    print("=" * 80)
    print("      PER-LANGUAGE COMPREHENSIVE TEST SUITE (100 TEST CASES PER LANGUAGE)      ")
    print("=" * 80)
    print(f"Total Languages Tested : {len(ALL_LANGUAGES)}")
    print(f"Test Cases Per Lang    : 100")
    print(f"Total Test Executions  : {sum(len(v) for v in test_cases_by_lang.values()):,}")
    print("=" * 80)

    summary_results = {}

    for lang in ALL_LANGUAGES:
        queries = test_cases_by_lang.get(lang, [])
        lang_name = LANG_NAMES.get(lang, lang)
        
        if not queries:
            print(f"Skipping {lang_name} ({lang}): No queries available.")
            continue

        hits = {1: 0, 3: 0, 5: 0}
        reciprocal_ranks = []
        latencies = []
        errors = 0

        for q in queries:
            t0 = time.perf_counter()
            try:
                results = await retrieval.retrieve_context(q["query"], top_k=top_k)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                latencies.append(elapsed_ms)
            except Exception as e:
                errors += 1
                reciprocal_ranks.append(0.0)
                continue

            expected_doc = q.get("expected_doc_id")
            rank = None
            for idx, res in enumerate(results):
                if res.doc_id == expected_doc:
                    rank = idx + 1
                    break

            reciprocal_ranks.append(1.0 / rank if rank else 0.0)
            for k in (1, 3, 5):
                if rank is not None and rank <= k:
                    hits[k] += 1

        n = len(queries)
        recall_1 = hits[1] / n if n else 0.0
        recall_3 = hits[3] / n if n else 0.0
        recall_5 = hits[5] / n if n else 0.0
        mrr = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0
        p50_lat = float(np.percentile(latencies, 50)) if latencies else 0.0
        p95_lat = float(np.percentile(latencies, 95)) if latencies else 0.0

        summary_results[lang] = {
            "lang_name": lang_name,
            "count": n,
            "recall_1": recall_1,
            "recall_3": recall_3,
            "recall_5": recall_5,
            "mrr": mrr,
            "p50_latency_ms": p50_lat,
            "p95_latency_ms": p95_lat,
            "errors": errors,
        }

    # Print Report
    print(f"\n{'Lang Code':<10}{'Language':<14}{'Tests':>8}{'Recall@1':>10}{'Recall@3':>10}{'Recall@5':>10}{'MRR':>10}{'P50 Lat':>10}{'Errors':>8}")
    print("-" * 88)
    
    total_tests = 0
    total_errors = 0
    all_recalls_5 = []
    all_mrrs = []
    all_p50s = []

    for lang in ALL_LANGUAGES:
        if lang not in summary_results:
            continue
        r = summary_results[lang]
        total_tests += r["count"]
        total_errors += r["errors"]
        all_recalls_5.append(r["recall_5"])
        all_mrrs.append(r["mrr"])
        all_p50s.append(r["p50_latency_ms"])

        print(f"{lang:<10}{r['lang_name']:<14}{r['count']:>8d}{r['recall_1']:>10.3f}{r['recall_3']:>10.3f}{r['recall_5']:>10.3f}{r['mrr']:>10.3f}{r['p50_latency_ms']:>8.1f}ms{r['errors']:>8d}")

    print("=" * 88)
    print(f"TOTAL TEST CASES EXECUTED : {total_tests:,}")
    print(f"TOTAL PASSED (0 ERRORS)   : {total_tests - total_errors:,}")
    print(f"AVERAGE RECALL@5 ACROSS   : {np.mean(all_recalls_5):.3f}")
    print(f"AVERAGE MRR ACROSS LANGS  : {np.mean(all_mrrs):.3f}")
    print(f"AVERAGE P50 LATENCY       : {np.mean(all_p50s):.1f} ms")
    print("=" * 88)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run 100 test cases per language test suite.")
    parser.add_argument("--index-dir", default="data/index")
    parser.add_argument("--eval-queries", default="data/eval_queries.jsonl")
    args = parser.parse_args()

    print(f"[test_suite] Initializing retrieval index from {args.index_dir}...")
    retrieval.init_retrieval(args.index_dir)

    print(f"[test_suite] Loading 100 test cases per language from {args.eval_queries}...")
    test_cases_by_lang = load_100_test_cases_per_language(args.eval_queries)

    asyncio.run(run_language_test_suite(test_cases_by_lang))
