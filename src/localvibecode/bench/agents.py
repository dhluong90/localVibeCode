"""Agent configurations compared by the benchmark (docs/BENCHMARK_STANDARD.md, section 5.1).

- B0: raw model, one prompt with the whole repository, full-file answers, no retry.
- H:  the localVibeCode PEV harness, unchanged, instrumented to record what it does.
- O:  oracle harness: gold files + gold plan + full context, large output budget, test-feedback retries.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from localvibecode.bench.grading import run_cmd
from localvibecode.bench.llm import CONTENT_SCHEMA, FILES_SCHEMA, RecordingOllama
from localvibecode.bench.tasks import Fixture, Task
from localvibecode.bench.workspace import list_repo_files, safe_write

ORACLE_REPAIR_ROUNDS = 3
ORACLE_REPAIR_TEMPERATURES = (0.2, 0.5, 0.8)
MAX_OUTPUT_TOKENS = 8192
LARGE_CTX = 16384


def _fence(rel: str) -> str:
    return "java" if rel.endswith(".java") else ("python" if rel.endswith(".py") else "")


def _render_files(ws: Path, rels: List[str]) -> str:
    parts = []
    for rel in rels:
        path = ws / rel
        body = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else "(file does not exist yet)"
        parts.append(f"### {rel}\n```{_fence(rel)}\n{body}\n```")
    return "\n\n".join(parts)


def _write_files(ws: Path, content: str, trace: Dict[str, Any], allowed: List[str] = None) -> None:
    data = json.loads(content)
    for item in data.get("files", []):
        rel = str(item.get("path", "")).strip().lstrip("/")
        if rel.startswith("./"):
            rel = rel[2:]
        if allowed is not None and rel not in allowed:
            trace.setdefault("events", []).append({"type": "write_skipped_not_allowed", "file": rel})
            continue
        ok = safe_write(ws, rel, _ensure_newline(item.get("content", "")))
        trace.setdefault("events", []).append({"type": "write" if ok else "write_rejected_path", "file": rel})


def _ensure_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


# ----------------------------------------------------------------------------- B0

B0_SYSTEM = (
    "You are a senior software engineer. Implement the task by editing the repository below. "
    "Respond ONLY with JSON of the form {\"files\": [{\"path\": \"<relative path>\", \"content\": \"<complete file content>\"}]} "
    "listing every file you create or modify, each with its COMPLETE new content."
)


def run_b0(task: Task, fixture: Fixture, ws: Path, llm: RecordingOllama, trace: Dict[str, Any]) -> None:
    files = list_repo_files(ws)
    user = f"## Task\n{task.prompt}\n\n## Repository files\n\n{_render_files(ws, files)}"
    content = llm.chat("b0", B0_SYSTEM, user, schema=FILES_SCHEMA, num_ctx=LARGE_CTX, num_predict=MAX_OUTPUT_TOKENS)
    _write_files(ws, content, trace)


# ----------------------------------------------------------------------------- Oracle

ORACLE_SYSTEM = (
    "You are a senior software engineer executing an approved implementation plan step by step. "
    "Edit ONLY the file named in the current step. Keep everything that the step does not ask to change. "
    "Respond ONLY with JSON {\"content\": \"<complete new content of the file>\"}."
)
ORACLE_REPAIR_SYSTEM = (
    "You are a senior software engineer. The implementation below fails the repository's test command. "
    "Fix it. You may edit only the files listed as editable. Respond ONLY with JSON "
    "{\"files\": [{\"path\": \"<relative path>\", \"content\": \"<complete file content>\"}]} for the files you change."
)


def _oracle_context(task: Task, fixture: Fixture, ws: Path) -> List[str]:
    """Perfect retrieval: gold files, plus their 1-hop neighbours (all source files for small repos)."""
    files = list_repo_files(ws)
    if task.category == "T1":
        context = [f for f in files if not fixture.is_test_file(f)] + [
            f for f in files if fixture.is_test_file(f)
        ][:1]
    else:
        from localvibecode.context.graph_builder import DeterministicGraphBuilder

        graph = DeterministicGraphBuilder(ws).build()
        context = []
        for gold in task.gold_files:
            context += graph.file_imports.get(gold, []) + graph.inbound_files.get(gold, [])
    ordered = []
    for rel in list(task.gold_files) + context:
        if rel not in ordered and ((ws / rel).exists() or rel in task.gold_files):
            ordered.append(rel)
    return ordered


def run_oracle(task: Task, fixture: Fixture, ws: Path, llm: RecordingOllama, trace: Dict[str, Any]) -> None:
    context = _oracle_context(task, fixture, ws)
    trace["oracle_context"] = context
    plan_text = "\n".join(f"{i}. `{s['file']}`: {s['instruction']}" for i, s in enumerate(task.oracle_plan, 1))
    for i, step in enumerate(task.oracle_plan, 1):
        user = (
            f"## Task\n{task.prompt}\n\n## Approved plan\n{plan_text}\n\n"
            f"## Current step {i}: edit `{step['file']}`\n{step['instruction']}\n\n"
            f"## Relevant files (current state)\n\n{_render_files(ws, context)}"
        )
        content = llm.chat(f"oracle_step_{i}", ORACLE_SYSTEM, user, schema=CONTENT_SCHEMA,
                           num_ctx=LARGE_CTX, num_predict=MAX_OUTPUT_TOKENS)
        new_text = json.loads(content).get("content", "")
        safe_write(ws, step["file"], _ensure_newline(new_text))
        trace.setdefault("events", []).append({"type": "write", "file": step["file"]})

    for attempt in range(1, ORACLE_REPAIR_ROUNDS + 1):
        rc, out = run_cmd(fixture.test_cmd, ws)
        trace.setdefault("events", []).append({"type": "oracle_test", "attempt": attempt, "passed": rc == 0})
        if rc == 0:
            return
        user = (
            f"## Task\n{task.prompt}\n\n## Approved plan\n{plan_text}\n\n"
            f"## Editable files\n{', '.join(task.gold_files)}\n\n"
            f"## Test command output (tail)\n```\n{_tail_relevant(out)}\n```\n\n"
            f"## Relevant files (current state)\n\n{_render_files(ws, context)}"
        )
        # Raise temperature on each retry so repeated attempts are not identical.
        content = llm.chat(f"oracle_repair_{attempt}", ORACLE_REPAIR_SYSTEM, user, schema=FILES_SCHEMA,
                           num_ctx=LARGE_CTX, num_predict=MAX_OUTPUT_TOKENS,
                           temperature=ORACLE_REPAIR_TEMPERATURES[attempt - 1])
        _write_files(ws, content, trace, allowed=list(task.gold_files))


def _tail_relevant(out: str, limit: int = 5000) -> str:
    lines = [l for l in out.splitlines() if not l.startswith("[INFO]") and "Downloading" not in l]
    return "\n".join(lines)[-limit:]


# ----------------------------------------------------------------------------- H (localVibeCode)


def run_harness(
    task: Task, fixture: Fixture, ws: Path, model: str, project_root: Path, trace: Dict[str, Any]
) -> None:
    """Runs the unchanged PEV state machine on the workspace, recording calls via monkeypatching."""
    import localvibecode.pev.state_machine as sm
    from localvibecode.config import LocalVibeCodeConfig

    cfg = LocalVibeCodeConfig.load(project_root)
    cfg.primary_model = model
    cfg.fallback_model = model
    cfg.test_command = list(fixture.test_cmd)
    trace["h_config"] = {"num_ctx": cfg.num_ctx, "max_surgical_context_chars": cfg.max_surgical_context_chars,
                         "max_self_healing_retries": cfg.max_self_healing_retries}
    calls = trace.setdefault("llm_calls", [])
    slices = trace.setdefault("slices", [])
    patches = trace.setdefault("patches", [])
    file_checks = trace.setdefault("file_checks", [])
    logs = trace.setdefault("log", [])
    contexts = trace.setdefault("_contexts", [])

    orig_slice = sm.BlastRadiusSlicer.slice_for_file

    def slice_for_file(self, target):  # type: ignore[no-untyped-def]
        s = orig_slice(self, target)
        slices.append({"target": s.target_file, "approx_tokens": s.approx_tokens,
                       "truncated": s.rendered_context.endswith("[Truncated to fit Surgical Context Cap]"),
                       "outbound": s.outbound_files, "inbound": s.inbound_files})
        contexts.append(s.rendered_context)
        return s

    orig_apply = sm.SurgicalPatcher.__dict__["apply_llm_output"].__func__

    def apply_llm_output(cls, file_path, llm_text):  # type: ignore[no-untyped-def]
        out = orig_apply(cls, file_path, llm_text)
        patches.append({"file": _rel(ws, file_path), "applied": out.applied, "mode": out.mode,
                        "message": out.message[:300]})
        return out

    orig_check = sm.ZeroTokenVerifier.verify_file_syntax_and_security
    orig_workspace = sm.ZeroTokenVerifier.verify_workspace
    in_workspace_check = {"active": False}
    workspace_checks = trace.setdefault("workspace_checks", [])

    def verify_file(self, rel_path, previous_source=""):  # type: ignore[no-untyped-def]
        res = orig_check(self, rel_path, previous_source=previous_source)
        if not in_workspace_check["active"]:
            file_checks.append({"file": rel_path, "passed": res.passed, "error": res.error_summary[:500]})
        return res

    def verify_workspace(self):  # type: ignore[no-untyped-def]
        in_workspace_check["active"] = True
        try:
            res = orig_workspace(self)
        finally:
            in_workspace_check["active"] = False
        workspace_checks.append({"passed": res.passed, "security_ok": res.security_ok,
                                 "error": res.error_summary[:1500]})
        return res

    sm.BlastRadiusSlicer.slice_for_file = slice_for_file
    sm.SurgicalPatcher.apply_llm_output = classmethod(apply_llm_output)
    sm.ZeroTokenVerifier.verify_file_syntax_and_security = verify_file
    sm.ZeroTokenVerifier.verify_workspace = verify_workspace

    pev = sm.DeterministicPEVStateMachine(cfg, repo_path=ws, progress_callback=lambda m: logs.append(m))
    orig_generate = pev.llm.generate_fresh

    def generate_fresh(**kwargs):  # type: ignore[no-untyped-def]
        system = kwargs.get("system_prompt", "")
        phase = ("plan" if "Architect" in system else "execute" if "Surgical Coder" in system
                 else "heal" if "Debugger" in system else "critic" if "Critic" in system else "other")
        record = {"phase": phase, "num_predict": kwargs.get("num_predict", 1536), "num_ctx": cfg.num_ctx,
                  "prompt_chars": len(system) + len(kwargs.get("user_prompt", ""))}
        try:
            resp = orig_generate(**kwargs)
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            calls.append(record)
            raise
        record.update({"prompt_tokens": resp.prompt_tokens, "completion_tokens": resp.completion_tokens,
                       "elapsed_sec": resp.elapsed_sec, "response_chars": len(resp.content)})
        calls.append(record)
        return resp

    pev.llm.generate_fresh = generate_fresh  # type: ignore[assignment]
    report = pev.run(task.prompt)
    trace["h_report"] = {
        "success": report.success,
        "plan_files": [t.get("target_file", "") for t in report.plan_data.get("atomic_tasks", [])],
        "architectural_summary": report.plan_data.get("architectural_summary", ""),
        "task_records": [
            {"step_id": r.step_id, "target_file": r.target_file, "attempts": r.attempts,
             "patch_mode": r.patch_mode, "verified": r.verified, "context_tokens": r.surgical_context_tokens}
            for r in report.task_records
        ],
        "workspace_tests_passed": bool(report.test_verification and report.test_verification.passed),
        "critic_verdict": report.critic_verdict,
    }
    heal = [m for m in logs if "[Test Self-Healing]" in m]
    if heal:
        match = re.search(r"on `([^`]+)`", heal[0])
        trace["h_report"]["heal_target"] = match.group(1) if match else None


def _rel(ws: Path, path: Any) -> str:
    try:
        return Path(path).resolve().relative_to(ws.resolve()).as_posix()
    except ValueError:
        return str(path)
