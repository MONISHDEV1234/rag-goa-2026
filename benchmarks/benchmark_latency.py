"""
benchmarks/benchmark_latency.py — Latency Benchmark Runner (Role 2)

Usage
-----
  # Run against a live server (default: http://127.0.0.1:8000)
  python benchmarks/benchmark_latency.py

  # Custom server
  python benchmarks/benchmark_latency.py --base-url http://localhost:8000

  # Run only N queries
  python benchmarks/benchmark_latency.py --limit 20

  # Use real STT (requires audio files in benchmarks/audio/)
  python benchmarks/benchmark_latency.py --use-stt

  # Save raw results JSON
  python benchmarks/benchmark_latency.py --output benchmarks/results.json

Output
------
Prints a formatted table of P50 / P70 / P100 for each pipeline stage.
Saves raw per-query results to --output path if specified.

Notes
-----
* By default, queries are sent to POST /api/query (text endpoint) so the
  benchmark is independent of STT availability.  Pass --use-stt to send
  audio files to POST /api/voice instead.
* This benchmark does NOT mock or stub the backend.  It requires a running
  FastAPI server.  Never fabricate benchmark results.
* Latency is measured browser-side (request start → response end) and also
  extracted from the latency_breakdown field in the RAGResponse for
  server-side per-stage breakdowns.
* Cold vs warm behavior: the first 5 queries are treated as warm-up and
  excluded from percentile calculations by default.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import httpx

# ── Config ──────────────────────────────────────────────────────────────────

QUERIES_PATH    = Path(__file__).parent / "queries.json"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
WARMUP_QUERIES  = 5          # excluded from percentile stats
LATENCY_TARGET  = 200        # ms — project target from README.md

# ── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class QueryResult:
    query_id:       int
    query:          str

    # Client-measured round-trip (ms)
    client_total_ms: Optional[float] = None

    # Server-measured stage latencies from latency_breakdown (ms)
    stt_ms:         Optional[float] = None
    embedding_ms:   Optional[float] = None
    retrieval_ms:   Optional[float] = None
    generation_ms:  Optional[float] = None
    grounding_ms:   Optional[float] = None
    server_total_ms: Optional[float] = None

    # Response fields
    is_grounded:    Optional[bool]  = None
    answer_length:  Optional[int]   = None
    error:          Optional[str]   = None

    # Warm-up flag
    is_warmup: bool = False

# ── Percentile Calculation ────────────────────────────────────────────────────

def percentile(data: list[float], pct: float) -> float:
    """
    Calculate the p-th percentile of a list.

    Args:
        data: Non-empty list of float values.
        pct:  Percentile as a fraction, e.g. 0.50 for P50.

    Returns:
        Interpolated percentile value.
    """
    if not data:
        raise ValueError("Cannot compute percentile of empty list.")
    sorted_data = sorted(data)
    n = len(sorted_data)
    # Linear interpolation (same as numpy.percentile default)
    idx = pct * (n - 1)
    lo  = int(idx)
    hi  = lo + 1
    frac = idx - lo
    if hi >= n:
        return sorted_data[lo]
    return sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo])

def p50(data: list[float]) -> float: return percentile(data, 0.50)
def p70(data: list[float]) -> float: return percentile(data, 0.70)
def p100(data: list[float]) -> float: return max(data)

# ── HTTP Client ───────────────────────────────────────────────────────────────

def run_text_query(
    client: httpx.Client,
    base_url: str,
    query: str,
    top_k: int = 3,
) -> tuple[float, dict]:
    """
    Send a text query to POST /api/query and return (round_trip_ms, body).
    """
    t_start = time.perf_counter()
    response = client.post(
        f"{base_url}/api/query",
        json={"query": query, "top_k": top_k},
        timeout=30.0,
    )
    t_end = time.perf_counter()
    round_trip_ms = (t_end - t_start) * 1000
    response.raise_for_status()
    return round_trip_ms, response.json()


def run_voice_query(
    client: httpx.Client,
    base_url: str,
    audio_path: Path,
) -> tuple[float, dict]:
    """
    Send audio to POST /api/voice and return (round_trip_ms, body).
    """
    t_start = time.perf_counter()
    with audio_path.open("rb") as f:
        response = client.post(
            f"{base_url}/api/voice",
            files={"audio": (audio_path.name, f, "audio/webm")},
            timeout=30.0,
        )
    t_end = time.perf_counter()
    round_trip_ms = (t_end - t_start) * 1000
    response.raise_for_status()
    return round_trip_ms, response.json()

# ── Main Runner ────────────────────────────────────────────────────────────────

def benchmark(
    queries: list[dict],
    base_url: str,
    use_stt: bool,
    audio_dir: Path | None,
    warmup: int,
) -> list[QueryResult]:
    results: list[QueryResult] = []

    with httpx.Client(timeout=30.0) as client:
        for i, q in enumerate(queries):
            qid   = q["id"]
            query = q["query"]
            is_wu = i < warmup

            result = QueryResult(query_id=qid, query=query, is_warmup=is_wu)

            try:
                if use_stt and audio_dir:
                    # Look for a matching .webm / .ogg file
                    audio_path = None
                    for ext in ("webm", "ogg", "wav", "mp3"):
                        candidate = audio_dir / f"{qid}.{ext}"
                        if candidate.exists():
                            audio_path = candidate
                            break
                    if audio_path is None:
                        result.error = f"No audio file for query {qid} in {audio_dir}"
                        results.append(result)
                        continue
                    rt_ms, body = run_voice_query(client, base_url, audio_path)
                else:
                    rt_ms, body = run_text_query(client, base_url, query)

                result.client_total_ms = rt_ms

                lb = body.get("latency_breakdown", {}) or {}
                result.stt_ms         = lb.get("stt")
                result.embedding_ms   = lb.get("embedding")
                result.retrieval_ms   = lb.get("retrieval")
                result.generation_ms  = lb.get("generation")
                result.grounding_ms   = lb.get("grounding")
                result.server_total_ms= lb.get("total")
                result.is_grounded    = body.get("is_grounded")
                result.answer_length  = len(body.get("answer", ""))

            except httpx.HTTPStatusError as exc:
                result.error = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            except Exception as exc:                       # noqa: BLE001
                result.error = f"{type(exc).__name__}: {exc}"

            status = "WARMUP" if is_wu else ("ERROR" if result.error else "OK")
            print(
                f"  [{i+1:3d}/{len(queries)}] id={qid:<4} {status:<8}"
                f" client={_fmt(result.client_total_ms):<10}"
                f" server={_fmt(result.server_total_ms)}"
            )
            results.append(result)

    return results


def _fmt(v: float | None) -> str:
    return f"{v:.1f}ms" if v is not None else "N/A"

# ── Report ─────────────────────────────────────────────────────────────────────

def print_report(results: list[QueryResult]) -> None:
    # Exclude warm-up and error queries from stats
    valid = [r for r in results if not r.is_warmup and r.error is None]

    if not valid:
        print("\nNo valid results to report.")
        return

    def stats(field_name: str) -> tuple[float, float, float] | None:
        vals = [getattr(r, field_name) for r in valid if getattr(r, field_name) is not None]
        if not vals:
            return None
        return p50(vals), p70(vals), p100(vals)

    stages = [
        ("STT",        "stt_ms"),
        ("Embedding",  "embedding_ms"),
        ("Retrieval",  "retrieval_ms"),
        ("Generation", "generation_ms"),
        ("Grounding",  "grounding_ms"),
        ("Server Total","server_total_ms"),
        ("Client RT",  "client_total_ms"),
    ]

    w = 60
    print()
    print("=" * w)
    print("       HH GOA RAG — LATENCY BENCHMARK RESULTS")
    print("=" * w)
    print(f"  Queries tested : {len(results)}")
    print(f"  Warm-up queries: {sum(1 for r in results if r.is_warmup)}")
    print(f"  Valid queries  : {len(valid)}")
    print(f"  Errors         : {sum(1 for r in results if r.error)}")
    print(f"  Target         : < {LATENCY_TARGET} ms")
    print()
    print(f"  {'Stage':<16} {'P50':>10} {'P70':>10} {'P100':>10}")
    print(f"  {'-'*16} {'-'*10} {'-'*10} {'-'*10}")

    for label, field_name in stages:
        s = stats(field_name)
        if s is None:
            continue
        flag = "⚠" if field_name in ("server_total_ms", "client_total_ms") and s[2] > LATENCY_TARGET else " "
        print(f"  {label:<16} {s[0]:>8.1f}ms {s[1]:>8.1f}ms {s[2]:>8.1f}ms {flag}")

    # Grounding rate
    grounded = [r for r in valid if r.is_grounded is True]
    if grounded:
        rate = 100 * len(grounded) / len(valid)
        print()
        print(f"  Grounded answers: {len(grounded)}/{len(valid)} ({rate:.1f}%)")

    # P50 server total vs target
    server_totals = [r.server_total_ms for r in valid if r.server_total_ms is not None]
    if server_totals:
        p50_server = p50(server_totals)
        print()
        if p50_server < LATENCY_TARGET:
            print(f"  ✓ P50 server total ({p50_server:.1f} ms) is under the {LATENCY_TARGET} ms target.")
        else:
            print(f"  ✗ P50 server total ({p50_server:.1f} ms) EXCEEDS the {LATENCY_TARGET} ms target.")

    print()
    print("=" * w)

# ── Entry Point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="HH Goa 2026 RAG Latency Benchmark (Role 2)",
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL,
        help=f"FastAPI base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--queries", default=str(QUERIES_PATH),
        help=f"Path to queries JSON (default: {QUERIES_PATH})",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit number of queries (default: all)",
    )
    parser.add_argument(
        "--warmup", type=int, default=WARMUP_QUERIES,
        help=f"Number of warm-up queries to exclude from stats (default: {WARMUP_QUERIES})",
    )
    parser.add_argument(
        "--use-stt", action="store_true",
        help="Send audio files to /api/voice instead of text to /api/query",
    )
    parser.add_argument(
        "--audio-dir", default=None,
        help="Directory containing audio files (required with --use-stt). Files must be named <id>.webm|ogg|wav|mp3.",
    )
    parser.add_argument(
        "--output", default=None,
        help="Save raw per-query results to this JSON file.",
    )
    args = parser.parse_args()

    # Load queries
    queries_path = Path(args.queries)
    if not queries_path.exists():
        print(f"ERROR: queries file not found: {queries_path}", file=sys.stderr)
        sys.exit(1)

    with queries_path.open() as f:
        all_queries = json.load(f)

    if args.limit:
        all_queries = all_queries[: args.limit]

    audio_dir = Path(args.audio_dir) if args.audio_dir else None

    print(f"\nHH Goa 2026 RAG Benchmark")
    print(f"  Server  : {args.base_url}")
    print(f"  Queries : {len(all_queries)}")
    print(f"  Mode    : {'STT (voice)' if args.use_stt else 'Text (/api/query)'}")
    print(f"  Warm-up : {args.warmup} queries excluded from stats")
    print()

    # Health check
    try:
        resp = httpx.get(f"{args.base_url}/health", timeout=5.0)
        if resp.status_code == 200:
            print("  ✓ Server health check passed.")
        else:
            print(f"  ⚠ Server returned {resp.status_code} on /health — continuing.")
    except Exception as exc:
        print(f"  ✗ Could not reach server: {exc}", file=sys.stderr)
        sys.exit(1)

    print("\n  Running queries…\n")
    results = benchmark(
        queries=all_queries,
        base_url=args.base_url,
        use_stt=args.use_stt,
        audio_dir=audio_dir,
        warmup=args.warmup,
    )

    print_report(results)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w") as f:
            json.dump([asdict(r) for r in results], f, indent=2, default=str)
        print(f"\n  Raw results saved to: {out_path}")


if __name__ == "__main__":
    main()
