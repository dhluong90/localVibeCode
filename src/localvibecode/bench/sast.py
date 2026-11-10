"""Q2: deterministic SAST detection benchmark for the Zero-Token Verifier (no LLM)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

from localvibecode.verifier.runner import ZeroTokenVerifier


def run_sast_suite(bench_root: Path) -> Dict[str, Any]:
    cases_dir = bench_root / "sast_cases"
    cases = json.loads((cases_dir / "cases.json").read_text(encoding="utf-8"))
    work = Path(tempfile.mkdtemp(prefix="bench-sast-"))
    rows = []
    try:
        for case in cases:
            shutil.copy2(cases_dir / case["file"], work / case["file"])
            res = ZeroTokenVerifier(work).verify_file_syntax_and_security(case["file"])
            rows.append({**case, "flagged": not res.security_ok, "syntax_ok": res.syntax_ok,
                         "message": res.error_summary[:200]})
    finally:
        shutil.rmtree(work, ignore_errors=True)
    vulnerable = [r for r in rows if r["vulnerable"]]
    safe = [r for r in rows if not r["vulnerable"]]
    detected = sum(1 for r in vulnerable if r["flagged"])
    false_pos = sum(1 for r in safe if r["flagged"])
    return {
        "vulnerable": len(vulnerable), "detected": detected,
        "recall": round(detected / len(vulnerable), 3) if vulnerable else None,
        "safe": len(safe), "false_positives": false_pos,
        "fp_rate": round(false_pos / len(safe), 3) if safe else None,
        "cases": rows,
    }
