#!/usr/bin/env python3
"""
scripts/benchmark.py — Convenience wrapper for running latency benchmarks (Role 2)

Usage:
    python scripts/benchmark.py [--base-url http://127.0.0.1:8080] [--limit 10] [--use-stt]
"""

import sys
from pathlib import Path

# Ensure root directory is on PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from benchmarks.benchmark_latency import main

if __name__ == "__main__":
    main()
