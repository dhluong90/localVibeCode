#!/usr/bin/env python3
"""Standalone runner for localVibeCode Benchmark & Acceptance Suite."""

import sys
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "src").as_posix())

from localvibecode.benchmark.runner import BenchmarkRunner
from localvibecode.config import LocalVibeCodeConfig


def main() -> None:
    config = LocalVibeCodeConfig.load(ROOT)
    runner = BenchmarkRunner(config, workspace_root=ROOT)
    results = runner.run_suite()
    all_passed = all(r.passed for r in results) if results else False
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
