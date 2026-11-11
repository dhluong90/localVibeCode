"""Agent configurations compared by the benchmark (docs/BENCHMARK_STANDARD.md, section 5.1).

- B0: raw model, one prompt with the whole repository, full-file answers, no retry.
- H:  the localVibeCode PEV harness, unchanged, instrumented to record what it does.
- O:  oracle harness: gold files + gold plan + full context, large output budget, test-feedback retries.

B0 and O ask for plain fenced code blocks (the way people vibe-code in a chat). Code inside JSON
strings made the 7B model drop Python indentation in the pilot, so it is not used as the oracle's
edit format. H keeps its own JSON-constrained format: that is the design under test.
"""

from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from localvibecode.bench.grading import run_cmd
from localvibecode.bench.llm import RecordingOllama
from localvibecode.bench.tasks import Fixture, Task
from localvibecode.bench.workspace import list_repo_files, safe_write

ORACLE_REPAIR_ROUNDS = 3
ORACLE_REPAIR_TEMPERATURES = (0.2, 0.5, 0.8)
ORACLE_CONTEXT_CHARS = 36000  # ~9k tokens of source context, leaves room for the answer in a 16k window
MAX_OUTPUT_TOKENS = 8192

FILE_BLOCK_FORMAT = (
    "For EVERY file you create or modify, output a line `FILE: <relative path>` immediately followed by a "
    "fenced code block containing the COMPLETE new content of that file. Do not output unchanged files."
)
_FILE_BLOCK = re.compile(r"FILE:\s*`?([^\s`]+)`?\s*\n+```[A-Za-z0-9_+-]*\n(.*?)\n```", re.DOTALL)
_CODE_BLOCK = re.compile(r"```[A-Za-z0-9_+-]*\n(.*?)\n```", re.DOTALL)


def _fence(rel: str) -> str:
    return "java" if rel.endswith(".java") else ("python" if rel.endswith(".py") else "")


def _render_files(ws: Path, rels: List[str]) -> str:
    parts = []
    for rel in rels:
        path = ws / rel
        body = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else "(file does not exist yet)"
        parts.append(f"FILE: {rel}\n```{_fence(rel)}\n{body}\n```")
    return "\n\n".join(parts)


def _ensure_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _write_file_blocks(
    ws: Path, text: str, trace: Dict[str, Any], allowed: Optional[List[str]] = None
) -> int:
    events = trace.setdefault("events", [])
    written = 0
    for rel, body in _FILE_BLOCK.findall(text):
        rel = rel.strip().lstrip("/")
        if rel.startswith("./"):
            rel = rel[2:]
        if allowed is not None and rel not in allowed:
            events.append({"type": "write_skipped_not_allowed", "file": rel})
            continue
        ok = safe_write(ws, rel, _ensure_newline(body))
        events.append({"type": "write" if ok else "write_rejected_path", "file": rel})
        written += int(ok)
    if written == 0:
        events.append({"type": "no_file_blocks_parsed", "response_head": text[:300]})
    return written


# ----------------------------------------------------------------------------- B0

B0_SYSTEM = "You are a senior software engineer. Implement the task by editing the repository below. " + FILE_BLOCK_FORMAT


def run_b0(task: Task, fixture: Fixture, ws: Path, llm: RecordingOllama, trace: Dict[str, Any]) -> None:
    # Small repos: the whole repo is pasted. Large repos do not fit any context window, so B0 models a
    # developer who located the relevant files and pasted only those (retrieval done by the human).
    files = list(task.gold_files) if fixture.large else list_repo_files(ws)
    user = f"## Task\n{task.prompt}\n\n## Repository files\n\n{_render_files(ws, files)}"
    text = llm.chat("b0", B0_SYSTEM, user, num_ctx=llm.num_ctx, num_predict=MAX_OUTPUT_TOKENS)
    _write_file_blocks(ws, text, trace)


# ----------------------------------------------------------------------------- Oracle

ORACLE_SYSTEM = (
    "You are a senior software engineer executing an approved implementation plan step by step. "
    "Edit ONLY the file named in the current step and keep everything the step does not ask to change. "
    "Respond with the COMPLETE new content of that file in a single fenced code block."
)
ORACLE_REPAIR_SYSTEM = (
    "You are a senior software engineer. The implementation below fails the repository's test command. "
    "Fix it. You may edit only the files listed as editable. " + FILE_BLOCK_FORMAT
)


def _oracle_context(task: Task, fixture: Fixture, ws: Path) -> List[str]:
    """Perfect retrieval: gold files plus their 1-hop neighbours (all source files for T1)."""
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
    ordered: List[str] = []
    budget = ORACLE_CONTEXT_CHARS
    for rel in list(task.gold_files) + context:
        if rel in ordered or not ((ws / rel).exists() or rel in task.gold_files):
            continue
        size = (ws / rel).stat().st_size if (ws / rel).exists() else 0
        if rel not in task.gold_files and size > budget:
            continue  # neighbours are added only while they fit; gold files always are
        ordered.append(rel)
        budget -= size
    return ordered


def run_oracle(task: Task, fixture: Fixture, ws: Path, llm: RecordingOllama, trace: Dict[str, Any]) -> None:
    context = _oracle_context(task, fixture, ws)
    trace["oracle_context"] = context
    events = trace.setdefault("events", [])
    plan_text = "\n".join(f"{i}. `{s['file']}`: {s['instruction']}" for i, s in enumerate(task.oracle_plan, 1))
    for i, step in enumerate(task.oracle_plan, 1):
        user = (
            f"## Task\n{task.prompt}\n\n## Approved plan\n{plan_text}\n\n"
            f"## Current step {i}: edit `{step['file']}`\n{step['instruction']}\n\n"
            f"## Relevant files (current state)\n\n{_render_files(ws, context)}"
        )
        text = llm.chat(f"oracle_step_{i}", ORACLE_SYSTEM, user, num_ctx=llm.num_ctx, num_predict=MAX_OUTPUT_TOKENS)
        blocks = _CODE_BLOCK.findall(text)
        if not blocks:
            events.append({"type": "no_code_block", "file": step["file"], "response_head": text[:300]})
            continue
        safe_write(ws, step["file"], _ensure_newline(max(blocks, key=len)))
        events.append({"type": "write", "file": step["file"]})

    for attempt in range(1, ORACLE_REPAIR_ROUNDS + 1):
        rc, out = run_cmd(task.effective_test_cmd(fixture), ws)
        events.append({"type": "oracle_test", "attempt": attempt, "passed": rc == 0})
        if rc == 0:
            return
        user = (
            f"## Task\n{task.prompt}\n\n## Approved plan\n{plan_text}\n\n"
            f"## Editable files\n{', '.join(task.gold_files)}\n\n"
            f"## Test command output (tail)\n```\n{_tail_relevant(out)}\n```\n\n"
            f"## Relevant files (current state)\n\n{_render_files(ws, context)}"
        )
        # Raise temperature on each retry so repeated attempts are not identical.
        text = llm.chat(f"oracle_repair_{attempt}", ORACLE_REPAIR_SYSTEM, user, num_ctx=llm.num_ctx,
                        num_predict=MAX_OUTPUT_TOKENS, temperature=ORACLE_REPAIR_TEMPERATURES[attempt - 1])
        _write_file_blocks(ws, text, trace, allowed=list(task.gold_files))


def _tail_relevant(out: str, limit: int = 5000) -> str:
    lines = [l for l in out.splitlines() if not l.startswith("[INFO]") and "Downloading" not in l]
    return "\n".join(lines)[-limit:]


# ----------------------------------------------------------------------------- H (localVibeCode)


# ----------------------------------------------------------------------------- OC (OpenCode agent)

OPENCODE_CONTEXT = 32768


def opencode_config(model: str, base_url: str = "http://localhost:11434/v1", context: int = OPENCODE_CONTEXT) -> Dict[str, Any]:
    """opencode.json pointing OpenCode at the local Ollama server (it does not auto-discover it)."""
    return {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Ollama (local)",
                "options": {"baseURL": base_url},
                "models": {model: {"name": f"{model} (local)", "tools": True,
                                   "limit": {"context": context, "output": 8192},
                                   # Qwen3 "thinking" cost ~2k output tokens per step (~2.5 min at 13 tok/s);
                                   # Ollama's OpenAI endpoint turns it off with reasoning_effort=none.
                                   "options": {"reasoningEffort": "none"}}},
            }
        },
        "model": f"ollama/{model}",
    }


PROXY_SCRIPT = Path(__file__).resolve().parents[3] / "local-ai" / "ollama_proxy.py"
AGENT_GUIDES = Path(__file__).resolve().parents[3] / "benchmarks" / "fixtures" / "agent_guides"


def _start_repair_proxy(run_dir: Path):
    """Per-run tool-call repair proxy (local-ai/ollama_proxy.py) on a free port, logging to the run dir."""
    import socket
    import subprocess
    import time as _time
    import urllib.request

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    log = run_dir / "proxy.jsonl"
    proc = subprocess.Popen([sys.executable, str(PROXY_SCRIPT), "--port", str(port), "--log", str(log)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=1).read()
            break
        except Exception:
            _time.sleep(0.1)
    return proc, port, log


def run_opencode(
    task: Task, fixture: Fixture, ws: Path, model: str, trace: Dict[str, Any], timeout: int,
    verify_rounds: int = 0, agent_guide: bool = False,
) -> None:
    """Gives the ticket to OpenCode (headless, auto-approved) and lets it work in the workspace.

    verify_rounds > 0 (config OCV): when the agent stops, run the test command; if it fails, send the
    failure back into the same OpenCode session and let it continue (agents claimed "tests pass" after a
    compile error in Round 01).
    """
    import json as _json
    import os
    import subprocess
    import time as _time

    proxy, port, proxy_log = _start_repair_proxy(ws.parent)
    # Config lives outside the workspace (OPENCODE_CONFIG): it stays out of the graded diff, and OpenCode
    # ignored an opencode.json that the VCS excluded.
    config_file = ws.parent / "opencode.json"
    config_file.write_text(
        _json.dumps(opencode_config(model, base_url=f"http://127.0.0.1:{port}/v1"), indent=2), encoding="utf-8")
    # OpenCode resolves its project from PWD, not the process cwd: pin both to the workspace.
    env = dict(os.environ, OPENCODE_CONFIG=str(config_file), PWD=str(ws))
    test_cmd = task.effective_test_cmd(fixture)
    # agent_guide: append the fixture's navigation guide to AGENTS.md (environment config, not part of the
    # task); the original file is restored before the diff is graded.
    agents_md = ws / "AGENTS.md"
    agents_md_before = agents_md.read_text(encoding="utf-8") if agents_md.exists() else None
    guide = AGENT_GUIDES / f"{fixture.name}.md"
    if agent_guide and guide.exists():
        agents_md.write_text((agents_md_before or "") + "\n" + guide.read_text(encoding="utf-8"), encoding="utf-8")
        trace["agent_guide"] = str(guide.name)
    prompt = (
        f"{task.prompt}\n\n"
        "Implement this in the repository. When you are done, make sure the code compiles and the relevant "
        f"tests pass. The relevant test command is: `{shlex.join(test_cmd)}`"  # quoted: zsh expands ** in -Dtest
    )
    events_file = ws.parent / "opencode_events.jsonl"
    deadline = _time.time() + timeout
    base_cmd = ["opencode", "run", "--print-logs", "--log-level", "WARN", "--auto", "--format", "json",
                "--dir", str(ws), "-m", f"ollama/{model}"]
    trace["opencode_cmd"] = base_cmd + ["<prompt>"]
    rounds: List[Dict[str, Any]] = []

    def run_once(extra: List[str], message: str) -> bool:
        remaining = deadline - _time.time()
        if remaining <= 30:
            trace["exception"] = f"opencode timeout after {timeout}s"
            return False
        try:
            with events_file.open("a", encoding="utf-8") as out:
                proc = subprocess.run(base_cmd + extra + [message], cwd=str(ws), stdout=out, stderr=subprocess.PIPE,
                                      text=True, timeout=remaining, env=env)
            trace["opencode_rc"] = proc.returncode
            trace["opencode_stderr_tail"] = proc.stderr[-2000:]
            return True
        except subprocess.TimeoutExpired:
            trace["exception"] = f"opencode timeout after {timeout}s"
            return False

    try:
        ok = run_once([], prompt)
        for i in range(1, verify_rounds + 1):
            if not ok:
                break
            rc, out = run_cmd(test_cmd, ws)
            rounds.append({"round": i, "tests_passed": rc == 0})
            if rc == 0:
                break
            session = _first_session_id(events_file)
            if not session:
                break
            feedback = (
                "The test command failed. Fix the code so that it passes, then run the command again to confirm.\n"
                f"Command: `{shlex.join(test_cmd)}`\nOutput (tail):\n```\n{_tail_relevant(out, 3500)}\n```"
            )
            ok = run_once(["-s", session], feedback)
    finally:
        proxy.terminate()
        if agent_guide and guide.exists():
            if agents_md_before is None:
                agents_md.unlink(missing_ok=True)
            else:
                agents_md.write_text(agents_md_before, encoding="utf-8")
    trace["verify_rounds"] = rounds

    calls = []
    for line in proxy_log.read_text(encoding="utf-8").splitlines() if proxy_log.exists() else []:
        try:
            entry = _json.loads(line)
        except ValueError:
            continue
        calls.append({"phase": "opencode", "prompt_tokens": entry.get("prompt_tokens") or 0,
                      "completion_tokens": entry.get("completion_tokens") or 0,
                      "elapsed_sec": entry.get("seconds"), "repairs": entry.get("repairs", 0)})
    trace.setdefault("llm_calls", []).extend(calls)
    trace["proxy_repairs"] = sum(c["repairs"] for c in calls)
    tools: Dict[str, int] = {}
    steps = 0
    for line in events_file.read_text(encoding="utf-8", errors="ignore").splitlines() if events_file.exists() else []:
        try:
            event = _json.loads(line)
        except ValueError:
            continue
        kind = event.get("type", "")
        steps += kind in ("step_start", "step-start")
        part = event.get("part") or {}
        tool = part.get("tool") or event.get("tool")
        if tool and kind in ("tool_use", "tool", "tool-call", "tool_call"):
            tools[tool] = tools.get(tool, 0) + 1
    trace["opencode_tool_calls"] = tools
    trace["opencode_steps"] = steps


def _first_session_id(events_file: Path) -> Optional[str]:
    import json as _json

    for line in events_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            sid = _json.loads(line).get("sessionID")
        except ValueError:
            continue
        if sid:
            return sid
    return None


def run_harness(
    task: Task, fixture: Fixture, ws: Path, model: str, project_root: Path, trace: Dict[str, Any]
) -> None:
    """Runs the unchanged PEV state machine on the workspace, recording calls via monkeypatching."""
    import localvibecode.pev.state_machine as sm
    from localvibecode.config import LocalVibeCodeConfig

    cfg = LocalVibeCodeConfig.load(project_root)
    cfg.primary_model = model
    cfg.fallback_model = model
    cfg.test_command = task.effective_test_cmd(fixture)
    if fixture.num_ctx:
        cfg.num_ctx = fixture.num_ctx
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
    heal_targets: List[str] = []
    for line in (m for m in logs if "[Test Self-Healing" in m):
        # Round 00 format: "... on `file`"; Round 01 format: "... Targeted fix on ['a', 'b']..."
        heal_targets += re.findall(r"on `([^`]+)`", line) + re.findall(r"'([^']+)'", line)
    if heal_targets:
        trace["h_report"]["heal_target"] = heal_targets[0]
        trace["h_report"]["heal_targets"] = heal_targets


def _rel(ws: Path, path: Any) -> str:
    try:
        return Path(path).resolve().relative_to(ws.resolve()).as_posix()
    except ValueError:
        return str(path)
