"""Builds SWE-bench-style task candidates from a large repo's git history (reverse-apply on HEAD).

For each commit C:
  - setup.patch  = reverse of C's diff (main + test Java files), applied on the pinned HEAD
  - hidden/      = HEAD versions of the test files C touched (never shown to the agent)
  - reference/   = HEAD versions of the main files C touched
Only commits whose reverse patch applies cleanly on HEAD are kept. The prompt is a placeholder
(the commit subject); it must be rewritten as a ticket before the task is used.

Usage: python3 benchmarks/tools/mine_git_tasks.py <repo> <fixture> <prefix> <commit> [<commit> ...]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=check)


def module_of(path: str) -> str:
    return path.split("/src/")[0]


def build(repo: Path, fixture: str, prefix: str, commit: str) -> str:
    files = [f for f in git(repo, "diff", "--name-only", f"{commit}^", commit).stdout.splitlines()
             if f.endswith(".java")]
    main = [f for f in files if "/src/main/" in f]
    tests = [f for f in files if "/src/test/" in f]
    if not main or not tests:
        return f"{commit}: skip (needs main + test java changes)"
    reverse = git(repo, "diff", commit, f"{commit}^", "--", *main, *tests).stdout
    patch_file = Path("/tmp") / f"lvc-mine-{commit}.patch"
    patch_file.write_text(reverse, encoding="utf-8")
    if git(repo, "apply", "--check", str(patch_file), check=False).returncode != 0:
        return f"{commit}: skip (reverse patch does not apply on HEAD)"

    subject, _, body = git(repo, "log", "-1", "--format=%s%n%b", commit).stdout.partition("\n")
    task_id = f"{prefix}-{commit[:9]}"
    out = BENCH / "tasks" / task_id
    (out / "hidden").mkdir(parents=True, exist_ok=True)
    (out / "setup.patch").write_text(reverse, encoding="utf-8")
    for rel in tests:
        head = repo / rel
        if head.exists():  # tests deleted by later commits cannot be hidden tests
            dst = out / "hidden" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(head.read_text(encoding="utf-8"), encoding="utf-8")
    for rel in main:
        head = repo / rel
        dst = out / "reference" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if head.exists():
            dst.write_text(head.read_text(encoding="utf-8"), encoding="utf-8")
    modules = sorted({module_of(f) for f in main + tests})
    added = sum(int(a) for a, *_ in (l.split("\t") for l in git(repo, "diff", "--numstat", f"{commit}^", commit, "--", *main).stdout.splitlines()) if a.isdigit())
    task = {
        "id": task_id,
        "category": "TODO",
        "fixture": fixture,
        "split": "dev",
        "difficulty": "TODO",
        "prompt": "TODO ticket. Commit: " + subject.strip() + ("\n" + body.strip() if body.strip() else ""),
        "setup": [],
        "setup_patch": "setup.patch",
        "gold_files": main,
        "test_modules": modules,
        "oracle_plan": [{"file": f, "instruction": "TODO"} for f in main],
        "source_commit": commit,
        "main_loc_changed": added,
    }
    (out / "task.json").write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return f"{commit}: OK -> {task_id} modules={modules} main={len(main)} tests={len(tests)}"


def main() -> None:
    repo, fixture, prefix, commits = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3], sys.argv[4:]
    for c in commits:
        print(build(repo, fixture, prefix, c))


if __name__ == "__main__":
    main()
