"""Objective grading: hidden tests (FAIL_TO_PASS), regression (PASS_TO_PASS), mutation score for T1.

Test granularity is the test module (Python) / test class (Java).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from localvibecode.bench.tasks import Fixture, Task, apply_edits

TEST_TIMEOUT_SEC = 300


def run_cmd(cmd: List[str], cwd: Path, timeout: int = TEST_TIMEOUT_SEC) -> Tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout + "\n" + proc.stderr)
    except subprocess.TimeoutExpired as exc:
        return 124, f"TIMEOUT after {timeout}s: {exc}"


# ----------------------------------------------------------------------------- test units


def _java_class(rel: str, test_dir: str) -> str:
    return rel[len(test_dir.rstrip("/")) + 1 : -len(".java")].replace("/", ".")


def base_test_units(fixture: Fixture, base: Path) -> List[str]:
    """Test modules/classes that exist in the base repo (relative paths)."""
    root = base / fixture.test_dir
    pattern = "test_*.py" if fixture.language == "python" else "*Test.java"
    return sorted(p.relative_to(base).as_posix() for p in root.rglob(pattern))


def unit_name(fixture: Fixture, rel: str) -> str:
    """Display name: Python module path, or simple Java class name."""
    if fixture.language == "java":
        return Path(rel).stem
    return rel


def run_units(fixture: Fixture, ws: Path, units: List[str]) -> Dict[str, object]:
    """Runs the given test units; returns {"compile_ok", "results": {unit: bool}, "output"}."""
    if fixture.language == "python":
        results: Dict[str, bool] = {}
        outputs: List[str] = []
        for rel in units:
            rc, out = run_cmd(
                ["python3", "-m", "unittest", "discover", "-s", fixture.test_dir, "-p", Path(rel).name], ws
            )
            results[rel] = rc == 0 and "Ran 0 tests" not in out
            if not results[rel]:
                outputs.append(f"--- {rel}\n{out[-3000:]}")
        return {"compile_ok": python_compile_errors(ws) == [], "results": results, "output": "\n".join(outputs)}

    reports = ws / "target" / "surefire-reports"
    if reports.exists():
        shutil.rmtree(reports)
    classes = [_java_class(rel, fixture.test_dir) for rel in units]
    rc, out = run_cmd(
        ["mvn", "-o", "-q", "test", "-Dtest=" + ",".join(Path(r).stem for r in units),
         "-Dsurefire.failIfNoSpecifiedTests=false", "-DfailIfNoTests=false"],
        ws,
    )
    compile_ok = "COMPILATION ERROR" not in out and "Compilation failure" not in out
    results = {}
    for rel, fqcn in zip(units, classes):
        report = reports / f"TEST-{fqcn}.xml"
        ok = False
        if report.exists():
            suite = ET.parse(report).getroot()
            ok = (
                int(suite.get("tests", 0)) > 0
                and int(suite.get("failures", 0)) == 0
                and int(suite.get("errors", 0)) == 0
            )
        results[rel] = ok
    return {"compile_ok": compile_ok, "results": results, "output": out[-6000:]}


def python_compile_errors(ws: Path) -> List[str]:
    errors = []
    for p in ws.rglob("*.py"):
        if any(part in {"graphify-out", "__pycache__", ".git"} for part in p.parts):
            continue
        try:
            compile(p.read_text(encoding="utf-8", errors="ignore"), str(p), "exec")
        except SyntaxError as exc:
            errors.append(f"{p.relative_to(ws).as_posix()}:{exc.lineno}: {exc.msg}")
    return errors


# ----------------------------------------------------------------------------- baseline


def compute_baseline(task: Task, fixture: Fixture, base: Path) -> Dict[str, object]:
    """Which base test units pass at the task's starting state (defines PASS_TO_PASS)."""
    work = Path(tempfile.mkdtemp(prefix="bench-baseline-"))
    try:
        shutil.copytree(base, work / "repo")
        repo = work / "repo"
        units = base_test_units(fixture, base)
        res = run_units(fixture, repo, units)
        f2p_base = set(task.fail_to_pass_base)
        p2p = [u for u in units if res["results"].get(u) and unit_name(fixture, u) not in f2p_base and u not in f2p_base]
        return {"base_units": units, "pass_to_pass": p2p, "base_results": res["results"]}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def fail_to_pass_units(task: Task, fixture: Fixture, base_units: List[str]) -> List[str]:
    units = list(task.hidden_files().keys())
    for name in task.fail_to_pass_base:
        units += [u for u in base_units if u == name or unit_name(fixture, u) == name]
    return units


# ----------------------------------------------------------------------------- grading


def grade(task: Task, fixture: Fixture, ws: Path, base: Path, baseline: Dict[str, object]) -> Dict[str, object]:
    """Grades the agent's final workspace. Mutates `ws` (restores base tests, adds hidden tests)."""
    t0 = time.time()
    result: Dict[str, object] = {}

    # 1. The agent's own deliverable: does the repo's normal test command pass as left by the agent?
    rc, out = run_cmd(fixture.test_cmd, ws)
    result["own_tests_pass"] = rc == 0
    result["own_tests_output"] = out[-3000:]

    if task.t1:
        result.update(_grade_t1(task, fixture, ws, base))

    # 2. Restore the base versions of pre-existing test files and run PASS_TO_PASS
    #    before adding hidden tests (a non-compiling hidden test must not count as a regression).
    for rel in baseline["base_units"]:
        shutil.copy2(base / rel, ws / rel)
    p2p = list(baseline["pass_to_pass"])
    p2p_res = run_units(fixture, ws, p2p) if p2p else {"compile_ok": True, "results": {}, "output": ""}
    result["pass_to_pass"] = {u: bool(p2p_res["results"].get(u, False)) for u in p2p}
    result["p2p_compile_ok"] = p2p_res["compile_ok"]
    result["regression"] = any(not ok for ok in result["pass_to_pass"].values())

    # 3. Add hidden tests and run FAIL_TO_PASS.
    for rel, src in task.hidden_files().items():
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, ws / rel)
    f2p = fail_to_pass_units(task, fixture, baseline["base_units"])
    f2p_res = run_units(fixture, ws, f2p) if f2p else {"compile_ok": True, "results": {}, "output": ""}
    result["compile_ok"] = f2p_res["compile_ok"]
    result["fail_to_pass"] = {u: bool(f2p_res["results"].get(u, False)) for u in f2p}
    result["test_output"] = str(f2p_res["output"]) + "\n" + str(p2p_res["output"])
    if task.t1:
        result["resolved"] = bool(result["t1_resolved"])
    else:
        result["resolved"] = bool(f2p) and all(result["fail_to_pass"].values())
    result["grading_sec"] = round(time.time() - t0, 1)
    return result


def _run_single(fixture: Fixture, repo: Path, rel: str) -> Tuple[bool, str]:
    res = run_units(fixture, repo, [rel])
    return bool(res["results"].get(rel)), str(res["output"])


def _grade_t1(task: Task, fixture: Fixture, ws: Path, base: Path) -> Dict[str, object]:
    """Agent's test file must pass on base code and fail on each mutant."""
    spec = task.t1 or {}
    test_rel = spec["test_file"]
    out: Dict[str, object] = {"t1_test_file_exists": (ws / test_rel).exists()}
    if not out["t1_test_file_exists"]:
        out.update({"t1_passes_on_base": False, "mutation_score": 0.0, "t1_resolved": False})
        return out

    work = Path(tempfile.mkdtemp(prefix="bench-t1-"))
    try:
        repo = work / "repo"
        shutil.copytree(base, repo)
        (repo / test_rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ws / test_rel, repo / test_rel)
        passes, log = _run_single(fixture, repo, test_rel)
        out["t1_passes_on_base"] = passes
        out["t1_base_output"] = log[-2000:]
        killed = 0
        mutants = spec.get("mutants", [])
        for mutant in mutants:
            original = (repo / mutant["file"]).read_text(encoding="utf-8")
            apply_edits(repo, [mutant])
            survived, _ = _run_single(fixture, repo, test_rel)
            killed += 0 if survived else 1
            (repo / mutant["file"]).write_text(original, encoding="utf-8")
        # A test file that already fails on correct code "kills" every mutant trivially.
        score = killed / len(mutants) if mutants and passes else 0.0
        out["mutation_score"] = round(score, 3)
        out["t1_resolved"] = passes and score >= float(spec.get("min_mutation_score", 1.0))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return out


def scope_metrics(task: Task, fixture: Fixture, changed: List[str]) -> Dict[str, Optional[float]]:
    if task.category == "T1":
        considered = changed
        gold = set(task.gold_files)
    else:
        considered = [f for f in changed if not fixture.is_test_file(f)]
        gold = {f for f in task.gold_files if not fixture.is_test_file(f)}
    hit = len(set(considered) & gold)
    return {
        "scope_precision": round(hit / len(considered), 3) if considered else None,
        "scope_recall": round(hit / len(gold), 3) if gold else None,
        "changed_files": changed,
    }
