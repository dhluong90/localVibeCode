"""Benchmark orchestration: task validation, per-run execution (one subprocess per run), resume."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from localvibecode.bench import grading
from localvibecode.bench.grading import install_file
from localvibecode.bench.tasks import Fixture, Task, load_fixtures, load_tasks
from localvibecode.bench.workspace import clone_workspace, collect_changes, prepare_base

RUN_TIMEOUT_SEC = 900
MAX_CONSECUTIVE_CRASHES = 3  # a broken checkout must not silently burn through the whole matrix
CONFIGS = ("B0", "H", "O", "OC", "OCV", "OCVG")


def model_slug(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


class BenchContext:
    def __init__(self, project_root: Path, round_dir: Path) -> None:
        self.project_root = project_root.resolve()
        self.bench_root = self.project_root / "benchmarks"
        self.round_dir = round_dir.resolve()
        self.fixtures: Dict[str, Fixture] = load_fixtures(self.bench_root)

    def base_dir(self, task: Task) -> Path:
        return self.round_dir / "runs" / "_base" / task.id / "repo"

    def ensure_base(self, task: Task) -> Dict[str, Any]:
        """Prepares the task's starting repo and PASS_TO_PASS baseline once per round."""
        base = self.base_dir(task)
        baseline_file = base.parent / "baseline.json"
        if base.exists() and baseline_file.exists():
            return json.loads(baseline_file.read_text(encoding="utf-8"))
        fixture = self.fixtures[task.fixture]
        prepare_base(task, fixture, base)
        baseline = grading.compute_baseline(task, fixture, base)
        baseline_file.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        return baseline

    def run_dir(self, model: str, config: str, task_id: str, k: int) -> Path:
        return self.round_dir / "runs" / model_slug(model) / config / task_id / f"k{k}"


# ----------------------------------------------------------------------------- validation


def validate_tasks(ctx: BenchContext, tasks: List[Task], log=None) -> List[Dict[str, Any]]:
    """Each task must: fail its hidden tests at base, and be resolved by its reference solution."""
    rows = []
    for task in tasks:
        fixture = ctx.fixtures[task.fixture]
        row: Dict[str, Any] = {"task": task.id, "pass_to_pass": [], "base_resolved": None,
                               "reference_resolved": None, "reference_regression": None}
        work = Path(tempfile.mkdtemp(prefix="bench-validate-"))
        try:
            baseline = ctx.ensure_base(task)
            base = ctx.base_dir(task)
            row["pass_to_pass"] = baseline["pass_to_pass"]
            ws = clone_workspace(base, work / "base_ws")
            g_base = grading.grade(task, fixture, ws, base, baseline)
            row["base_resolved"] = g_base["resolved"]
            ws = clone_workspace(base, work / "ref_ws")
            for rel, src in task.reference_files().items():
                (ws / rel).parent.mkdir(parents=True, exist_ok=True)
                install_file(src, ws / rel)
            changed, _ = collect_changes(ws)
            g_ref = grading.grade(task, fixture, ws, base, baseline)
            row["reference_resolved"] = g_ref["resolved"]
            row["reference_regression"] = g_ref["regression"]
            row["reference_own_tests_pass"] = g_ref["own_tests_pass"]
            if task.t1:
                row["reference_mutation_score"] = g_ref.get("mutation_score")
            row["valid"] = (not g_base["resolved"]) and g_ref["resolved"] and not g_ref["regression"]
            if not row["valid"]:
                row["detail"] = (g_ref.get("test_output", "") or "")[-1500:]
        except Exception as exc:  # one broken task must not stop the validation of the others
            row.update({"valid": False, "detail": f"validation error: {type(exc).__name__}: {exc}"[:1500]})
        finally:
            shutil.rmtree(work, ignore_errors=True)
        rows.append(row)
        if log:
            log(row)
    return rows


# ----------------------------------------------------------------------------- single run


def run_one(ctx: BenchContext, task: Task, config: str, model: str, k: int, keep_ws: bool = False) -> Dict[str, Any]:
    from localvibecode.bench import agents
    from localvibecode.bench.llm import RecordingOllama
    from localvibecode.bench.tagging import tag_failure
    from localvibecode.config import LocalVibeCodeConfig

    if not model_available(ctx, model):
        raise SystemExit(f"model {model} is not installed; refusing to run (the harness would silently fall back)")
    fixture = ctx.fixtures[task.fixture]
    baseline = ctx.ensure_base(task)
    base = ctx.base_dir(task)
    out_dir = ctx.run_dir(model, config, task.id, k)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Short workspace path without spaces: agents copy absolute paths into tool calls, and a long path with
    # spaces (".../AISDLC Solution/.claude/worktrees/...") was mis-copied in Round 02. Real repos have short paths.
    ws_root = Path(os.environ.get("LVC_WS_ROOT", "/tmp/lvc-ws"))
    ws = clone_workspace(base, ws_root / f"{model_slug(model)}-{config}-{task.id}-k{k}")

    trace: Dict[str, Any] = {"llm_calls": [], "_run_dir": str(out_dir)}
    cfg = LocalVibeCodeConfig.load(ctx.project_root)
    t0 = time.time()
    try:
        if config == "H":
            agents.run_harness(task, fixture, ws, model, ctx.project_root, trace)
        else:
            llm = RecordingOllama(cfg.ollama_base_url, model, cfg.keep_alive, trace["llm_calls"],
                                  num_ctx=fixture.num_ctx or cfg.num_ctx)
            if config == "B0":
                agents.run_b0(task, fixture, ws, llm, trace)
            elif config == "O":
                agents.run_oracle(task, fixture, ws, llm, trace)
            elif config in ("OC", "OCV", "OCVG"):
                budget = int((fixture.run_timeout_sec or RUN_TIMEOUT_SEC) * 0.75)  # leave time for grading
                agents.run_opencode(task, fixture, ws, model, trace, timeout=budget,
                                    verify_rounds=2 if config in ("OCV", "OCVG") else 0,
                                    agent_guide=config == "OCVG")
            else:
                raise ValueError(f"Unknown config {config}")
    except Exception as exc:  # the agent failing is a result, not a crash of the benchmark
        trace["exception"] = f"{type(exc).__name__}: {exc}"
        trace["traceback"] = traceback.format_exc()[-4000:]
    agent_sec = time.time() - t0

    changed, diff = collect_changes(ws)
    changed = [c for c in changed if not c.startswith("graphify-out/")]
    (out_dir / "diff.patch").write_text(diff, encoding="utf-8")
    grade = grading.grade(task, fixture, ws, base, baseline)
    grade.update(grading.scope_metrics(task, fixture, changed))
    tags = tag_failure(config, task, fixture, trace, grade, base)

    calls = trace.get("llm_calls", [])
    result = {
        "task": task.id, "category": task.category, "fixture": task.fixture, "difficulty": task.difficulty,
        "config": config, "model": model, "k": k,
        "resolved": bool(grade["resolved"]),
        "regression": bool(grade["regression"]),
        "own_tests_pass": grade["own_tests_pass"],
        "compile_ok": grade["compile_ok"],
        "scope_precision": grade["scope_precision"],
        "scope_recall": grade["scope_recall"],
        "changed_files": changed,
        "mutation_score": grade.get("mutation_score"),
        "tags": tags,
        "primary_tag": tags[0] if tags else None,
        "exception": trace.get("exception"),
        "agent_sec": round(agent_sec, 1),
        "grading_sec": grade["grading_sec"],
        "llm_calls": len(calls),
        "prompt_tokens": sum(c.get("prompt_tokens", 0) for c in calls),
        "completion_tokens": sum(c.get("completion_tokens", 0) for c in calls),
        "plan_files": (trace.get("h_report") or {}).get("plan_files"),
        "h_success": (trace.get("h_report") or {}).get("success"),
        "fail_to_pass": grade["fail_to_pass"],
        "pass_to_pass": grade["pass_to_pass"],
    }
    trace_out = {k2: v for k2, v in trace.items() if k2 != "_contexts"}
    trace_out["grade"] = {k2: v for k2, v in grade.items() if k2 not in ("changed_files",)}
    (out_dir / "trace.json").write_text(json.dumps(trace_out, indent=2, default=str), encoding="utf-8")
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if not keep_ws:
        shutil.rmtree(ws, ignore_errors=True)
    return result


# ----------------------------------------------------------------------------- matrix


def run_matrix(
    ctx: BenchContext,
    tasks: List[Task],
    models: List[str],
    configs: List[str],
    k_max: int,
    log=print,
) -> None:
    for task in tasks:
        ctx.ensure_base(task)
    total = len(models) * k_max * len(tasks) * len(configs)
    done = 0
    consecutive_crashes = 0
    # k outermost: every full pass gives complete coverage of all models/tasks/configs.
    for k in range(1, k_max + 1):
        for model in models:
            if not model_available(ctx, model):
                log(f"[skip] model {model} not installed in Ollama; k{k} runs for it deferred")
                done += len(tasks) * len(configs)
                continue
            for task in tasks:
                for config in configs:
                    done += 1
                    out_dir = ctx.run_dir(model, config, task.id, k)
                    if (out_dir / "result.json").exists():
                        continue
                    t0 = time.time()
                    run_timeout = ctx.fixtures[task.fixture].run_timeout_sec or RUN_TIMEOUT_SEC
                    cmd = [sys.executable, "-m", "localvibecode.bench", "run-one", "--round", str(ctx.round_dir),
                           "--task", task.id, "--config", config, "--model", model, "--k", str(k)]
                    try:
                        proc = subprocess.run(cmd, cwd=str(ctx.project_root), capture_output=True, text=True,
                                              timeout=run_timeout)
                        status = "ok" if proc.returncode == 0 else f"crash rc={proc.returncode}"
                        if proc.returncode != 0:
                            out_dir.mkdir(parents=True, exist_ok=True)
                            (out_dir / "crash.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
                            consecutive_crashes += 1
                            if consecutive_crashes >= MAX_CONSECUTIVE_CRASHES:
                                log(f"[abort] {consecutive_crashes} consecutive crashes, last log: {out_dir / 'crash.log'}")
                                raise SystemExit(2)
                        else:
                            consecutive_crashes = 0
                    except subprocess.TimeoutExpired:
                        status = "timeout"
                        _write_timeout_result(out_dir, task, config, model, k, run_timeout)
                    res_file = out_dir / "result.json"
                    resolved = json.loads(res_file.read_text())["resolved"] if res_file.exists() else None
                    log(f"[{done}/{total}] {model} {config} {task.id} k{k}: {status} resolved={resolved} "
                        f"({time.time() - t0:.0f}s)")


def model_available(ctx: BenchContext, model: str) -> bool:
    """The harness silently falls back to another model when the requested one is missing, so check first."""
    from localvibecode.config import LocalVibeCodeConfig
    from localvibecode.llm_client import SingleModelOllamaClient

    return model in SingleModelOllamaClient(LocalVibeCodeConfig.load(ctx.project_root)).list_local_models()


def _write_timeout_result(out_dir: Path, task: Task, config: str, model: str, k: int,
                          timeout: int = RUN_TIMEOUT_SEC) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(out_dir / "ws", ignore_errors=True)
    result = {"task": task.id, "category": task.category, "fixture": task.fixture, "difficulty": task.difficulty,
              "config": config, "model": model, "k": k, "resolved": False, "regression": False,
              "own_tests_pass": False, "compile_ok": False, "scope_precision": None, "scope_recall": None,
              "changed_files": [], "mutation_score": None, "tags": ["H8"], "primary_tag": "H8",
              "exception": f"run timeout after {timeout}s", "agent_sec": timeout,
              "grading_sec": 0, "llm_calls": None, "prompt_tokens": None, "completion_tokens": None,
              "plan_files": None, "h_success": None, "fail_to_pass": {}, "pass_to_pass": {}}
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


def find_task(ctx: BenchContext, task_id: str) -> Optional[Task]:
    found = load_tasks(ctx.bench_root, ids=[task_id])
    return found[0] if found else None


# ----------------------------------------------------------------------------- re-grading


def regrade_run(ctx: BenchContext, result_file: Path) -> Dict[str, Any]:
    """Re-grades a finished run from its saved diff (base + diff.patch), e.g. after a grading fix."""
    from localvibecode.bench.tagging import tag_failure
    from localvibecode.bench.workspace import _git

    run_dir = result_file.parent
    result = json.loads(result_file.read_text(encoding="utf-8"))
    trace_file = run_dir / "trace.json"
    trace = json.loads(trace_file.read_text(encoding="utf-8")) if trace_file.exists() else {}
    task = find_task(ctx, result["task"])
    fixture = ctx.fixtures[task.fixture]
    baseline = ctx.ensure_base(task)
    base = ctx.base_dir(task)
    work = Path(tempfile.mkdtemp(prefix="bench-regrade-"))
    try:
        ws = clone_workspace(base, work / "ws")
        patch = run_dir / "diff.patch"
        if patch.exists() and patch.read_text(encoding="utf-8").strip():
            _git(ws, "apply", "--whitespace=nowarn", str(patch.resolve()))
        grade = grading.grade(task, fixture, ws, base, baseline)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    grade.update(grading.scope_metrics(task, fixture, result.get("changed_files", [])))
    tags = tag_failure(result["config"], task, fixture, trace, grade, base)
    previous = {k: result.get(k) for k in ("resolved", "regression", "own_tests_pass", "primary_tag")}
    result.update({
        "resolved": bool(grade["resolved"]), "regression": bool(grade["regression"]),
        "own_tests_pass": grade["own_tests_pass"], "compile_ok": grade["compile_ok"],
        "mutation_score": grade.get("mutation_score"), "tags": tags, "primary_tag": tags[0] if tags else None,
        "fail_to_pass": grade["fail_to_pass"], "pass_to_pass": grade["pass_to_pass"],
        "regraded": {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "previous": previous},
    })
    result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if trace:
        trace["grade"] = {k: v for k, v in grade.items() if k != "changed_files"}
        trace_file.write_text(json.dumps(trace, indent=2, default=str), encoding="utf-8")
    return {"task": result["task"], "config": result["config"], "k": result["k"], "model": result["model"],
            "before": previous["resolved"], "after": result["resolved"],
            "regression_before": previous["regression"], "regression_after": result["regression"]}
