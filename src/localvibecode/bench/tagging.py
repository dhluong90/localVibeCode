"""Automatic failure attribution (docs/BENCHMARK_STANDARD.md, section 5.3).

Every failed run gets an ordered list of tags; the first one is the primary cause.
H* = harness-caused, M* = model-caused. Rules are heuristics; unmatched failures get M1.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from localvibecode.bench.tasks import Fixture, Task

_SYMBOL_PATTERNS = [
    re.compile(r"symbol:\s+(?:method|class|variable|constructor)\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"has no attribute '([A-Za-z_][A-Za-z0-9_]*)'"),
    re.compile(r"cannot import name '([A-Za-z_][A-Za-z0-9_]*)'"),
    re.compile(r"name '([A-Za-z_][A-Za-z0-9_]*)' is not defined"),
    re.compile(r"constructor ([A-Za-z_][A-Za-z0-9_]*) in class"),
]


def _norm(path: str) -> str:
    return path.strip().lstrip("./")  # same normalisation the harness applies to plan targets


def _base_source(base: Path) -> str:
    chunks = []
    for ext in ("*.py", "*.java"):
        for p in base.rglob(ext):
            if ".git" not in p.parts:
                chunks.append(p.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def tag_failure(
    config: str, task: Task, fixture: Fixture, trace: Dict[str, Any], grade: Dict[str, Any], base: Path
) -> List[str]:
    if grade.get("resolved"):
        return []
    tags: List[str] = []
    exc = trace.get("exception") or ""
    if exc:
        if "JSONDecodeError" in exc or "Expecting" in exc:
            tags.append("H5")
        else:
            tags.append("H8")

    calls = trace.get("llm_calls", [])
    gold_src = [g for g in task.gold_files if task.category == "T1" or not fixture.is_test_file(g)]

    if config == "H":
        report = trace.get("h_report") or {}
        plan_files = {_norm(f) for f in report.get("plan_files", [])}
        if report and gold_src and not set(gold_src) <= plan_files:
            tags.append("H1")
    if any(c.get("completion_tokens", 0) >= c.get("num_predict", 10 ** 9) or c.get("done_reason") == "length"
           for c in calls if c.get("phase") != "critic"):
        tags.append("H4")
    if any(c.get("prompt_tokens", 0) >= 0.98 * c.get("num_ctx", 10 ** 9) for c in calls):
        tags.append("H3")
    if any(not p.get("applied") for p in trace.get("patches", [])) or any(
        e.get("type") in ("no_file_blocks_parsed", "no_code_block") for e in trace.get("events", [])
    ):
        tags.append("H5")
    if any(s.get("truncated") and s.get("target") in task.gold_files for s in trace.get("slices", [])):
        tags.append("H3")
    if config == "H":
        heal = (trace.get("h_report") or {}).get("heal_target")
        if heal and heal not in task.gold_files:
            tags.append("H7")
        if any("Security Violation" in c.get("error", "") for c in trace.get("file_checks", [])):
            tags.append("H6")
        passed_files = {c["file"] for c in trace.get("file_checks", []) if c.get("passed")}
        compile_text = grade.get("test_output", "") if not grade.get("compile_ok", True) else ""
        if compile_text and any(f in compile_text for f in passed_files if f.endswith(".java")):
            tags.append("H6")

    output = str(grade.get("test_output", "")) + "\n" + str(grade.get("own_tests_output", ""))
    symbols = {m.group(1) for pat in _SYMBOL_PATTERNS for m in pat.finditer(output)}
    if symbols:
        given = "\n".join(trace.get("_contexts", []))
        base_src = _base_source(base)
        if config == "H" and any(s in base_src and s not in given for s in symbols):
            tags.append("H2")
        else:
            tags.append("M2")

    changed = set(grade.get("changed_files", []))
    if not changed & set(task.gold_files):
        tags.append("M4")
    tags.append("M1")

    ordered: List[str] = []
    for t in tags:
        if t not in ordered:
            ordered.append(t)
    return ordered
