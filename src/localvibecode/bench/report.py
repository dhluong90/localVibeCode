"""Aggregates run results into summary.json + Markdown tables (docs/BENCHMARK_STANDARD.md, sections 1.1, 3, 9)."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# Level gates measurable without humans in the loop (section 1.1). Human-intervention gates are 0 by construction.
LEVEL_GATES = {
    "L4": {"resolve": 0.85, "pass_k": 0.70, "regression": 0.01, "scope_precision": 0.9},
    "L3": {"resolve": 0.70, "pass_k": 0.40, "regression": 0.05, "scope_precision": 0.8},
    "L2": {"resolve": 0.50, "pass_k": None, "regression": 0.15, "scope_precision": None},
}


def wilson(successes: int, n: int, z: float = 1.96) -> List[Optional[float]]:
    if n == 0:
        return [None, None]
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]


def load_results(round_dir: Path) -> List[Dict[str, Any]]:
    out = []
    for f in sorted((round_dir / "runs").glob("*/*/*/k*/result.json")):
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def _mean(values: List[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def _level(m: Dict[str, Any]) -> str:
    for level in ("L4", "L3", "L2"):
        gate = LEVEL_GATES[level]
        if m["resolve_at_1"] is None or m["resolve_at_1"] < gate["resolve"]:
            continue
        if gate["pass_k"] is not None and (m["pass_k"] is None or m["pass_k"] < gate["pass_k"]):
            continue
        if m["regression_rate"] is not None and m["regression_rate"] > gate["regression"]:
            continue
        if gate["scope_precision"] is not None and m["scope_precision"] is not None \
                and m["scope_precision"] < gate["scope_precision"]:
            continue
        return level
    return "<L2"


def aggregate(rows: List[Dict[str, Any]], k_max: int) -> Dict[str, Any]:
    n = len(rows)
    resolved = sum(1 for r in rows if r["resolved"])
    by_task: Dict[str, List[bool]] = defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r["resolved"])
    complete = [v for v in by_task.values() if len(v) >= k_max]
    failed = [r for r in rows if not r["resolved"]]
    tags = Counter(r.get("primary_tag") or "?" for r in failed)
    m = {
        "instances": len(by_task),
        "runs": n,
        "resolve_at_1": round(resolved / n, 3) if n else None,
        "resolve_ci95": wilson(resolved, n),
        "pass_k": round(sum(1 for v in complete if all(v)) / len(complete), 3) if complete else None,
        "pass_k_instances": len(complete),
        "regression_rate": round(sum(1 for r in rows if r["regression"]) / n, 3) if n else None,
        "scope_precision": _mean([r.get("scope_precision") for r in rows]),
        "scope_recall": _mean([r.get("scope_recall") for r in rows]),
        "mutation_score": _mean([r.get("mutation_score") for r in rows]),
        "mean_agent_sec": _mean([r.get("agent_sec") for r in rows]),
        "mean_prompt_tokens": _mean([r.get("prompt_tokens") for r in rows]),
        "mean_completion_tokens": _mean([r.get("completion_tokens") for r in rows]),
        "failure_tags": dict(tags.most_common()),
        "harness_failure_share": round(sum(v for t, v in tags.items() if t.startswith("H")) / len(failed), 3)
        if failed else None,
    }
    m["level"] = _level(m)
    return m


def build_summary(
    round_dir: Path, tasks_root: Path, k_max: int, sast: Optional[Dict[str, Any]] = None,
    task_prefix: str = "", models: Optional[List[str]] = None,
) -> Dict[str, Any]:
    rows = [r for r in load_results(round_dir)
            if r["task"].startswith(task_prefix) and (not models or r["model"] in models)]
    groups: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in rows:
        groups[r["model"]][r["config"]][r["category"]].append(r)
        groups[r["model"]][r["config"]]["ALL"].append(r)
    summary: Dict[str, Any] = {"k": k_max, "total_runs": len(rows), "task_prefix": task_prefix, "models": {}}
    for model, by_cfg in groups.items():
        summary["models"][model] = {}
        for cfg, by_cat in by_cfg.items():
            summary["models"][model][cfg] = {cat: aggregate(rs, k_max) for cat, rs in sorted(by_cat.items())}
        # Harness gap & value-add per category.
        gaps = {}
        for cat in by_cfg.get("H", {}):
            h = summary["models"][model]["H"][cat]["resolve_at_1"]
            o = summary["models"][model].get("O", {}).get(cat, {}).get("resolve_at_1")
            b0 = summary["models"][model].get("B0", {}).get(cat, {}).get("resolve_at_1")
            gaps[cat] = {"oracle_minus_h": round(o - h, 3) if o is not None and h is not None else None,
                         "h_minus_b0": round(h - b0, 3) if b0 is not None and h is not None else None}
        summary["models"][model]["gaps"] = gaps
        # D1 (impact analysis) derived from the H plan step.
        plan_rows = [r for r in by_cfg.get("H", {}).get("ALL", []) if r.get("plan_files") is not None]
        if plan_rows:
            summary["models"][model]["D1_plan_scope"] = _plan_scope(tasks_root, plan_rows)
    if sast:
        summary["Q2_sast"] = sast
    return summary


def _plan_scope(tasks_root: Path, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    precisions, recalls = [], []
    for r in rows:
        task = json.loads((tasks_root / r["task"] / "task.json").read_text(encoding="utf-8"))
        gold = set(task["gold_files"])
        plan = {p.strip().lstrip("./") for p in r["plan_files"]}  # same normalisation the harness applies
        if r["category"] != "T1":
            gold = {g for g in gold if "/test" not in "/" + g}
            plan = {p for p in plan if "/test" not in "/" + p}
        if plan:
            precisions.append(len(plan & gold) / len(plan))
        recalls.append(len(plan & gold) / len(gold) if gold else 1.0)
    return {"runs": len(rows), "plan_precision": _mean(precisions), "plan_recall": _mean(recalls)}


def render_markdown(summary: Dict[str, Any]) -> str:
    lines: List[str] = []
    for model, data in summary["models"].items():
        lines.append(f"### `{model}`\n")
        lines.append("| Category | Config | n | runs | resolve@1 (CI95) | pass^k | Regression | Scope P/R | "
                     "Mutation | Level | Primary failure tags | s/run |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        cats = sorted({c for cfg in ("B0", "H", "O") for c in data.get(cfg, {})}, key=lambda c: (c == "ALL", c))
        for cat in cats:
            for cfg in ("B0", "H", "O"):
                m = data.get(cfg, {}).get(cat)
                if not m:
                    continue
                ci = m["resolve_ci95"]
                tags = ", ".join(f"{t}×{c}" for t, c in m["failure_tags"].items()) or "—"
                lines.append(
                    f"| {'**ALL**' if cat == 'ALL' else cat} | {cfg} | {m['instances']} | {m['runs']} | "
                    f"{_pct(m['resolve_at_1'])} ({_pct(ci[0])}–{_pct(ci[1])}) | {_pct(m['pass_k'])} | "
                    f"{_pct(m['regression_rate'])} | {_num(m['scope_precision'])}/{_num(m['scope_recall'])} | "
                    f"{_num(m['mutation_score'])} | {m['level']} | {tags} | {_num(m['mean_agent_sec'], 0)} |"
                )
        lines.append("")
        lines.append("| Category | Oracle − H | H − B0 | % H failures caused by harness |")
        lines.append("|---|---|---|---|")
        for cat, g in sorted(data.get("gaps", {}).items(), key=lambda kv: (kv[0] == "ALL", kv[0])):
            share = data.get("H", {}).get(cat, {}).get("harness_failure_share")
            lines.append(f"| {cat} | {_pp(g['oracle_minus_h'])} | {_pp(g['h_minus_b0'])} | {_pct(share)} |")
        if "D1_plan_scope" in data:
            d1 = data["D1_plan_scope"]
            lines.append(f"\nD1 (impact analysis, from H plan step): precision {_num(d1['plan_precision'])}, "
                         f"recall {_num(d1['plan_recall'])} over {d1['runs']} runs.\n")
    if "Q2_sast" in summary:
        q = summary["Q2_sast"]
        lines.append(f"### Q2 — SAST (deterministic)\n\nRecall {_pct(q['recall'])} ({q['detected']}/{q['vulnerable']}), "
                     f"false-positive rate {_pct(q['fp_rate'])} ({q['false_positives']}/{q['safe']}).\n")
    return "\n".join(lines)


def _pct(v: Optional[float]) -> str:
    return "—" if v is None else f"{v * 100:.0f}%"


def _pp(v: Optional[float]) -> str:
    return "—" if v is None else f"{v * 100:+.0f} pp"


def _num(v: Optional[float], digits: int = 2) -> str:
    return "—" if v is None else f"{v:.{digits}f}"
