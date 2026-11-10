"""Isolated per-run workspaces backed by a throwaway git repository."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

from localvibecode.bench.tasks import Fixture, Task, apply_edits

WORKSPACE_GITIGNORE = "graphify-out/\ntarget/\n__pycache__/\n*.pyc\n"
_GIT = ["git", "-c", "user.name=bench", "-c", "user.email=bench@localhost", "-c", "commit.gpgsign=false"]


def _git(ws: Path, *args: str) -> str:
    proc = subprocess.run(_GIT + list(args), cwd=str(ws), capture_output=True, text=True, check=True)
    return proc.stdout


def prepare_base(task: Task, fixture: Fixture, dest: Path) -> Path:
    """Creates the task's starting state (fixture + setup edits) as a committed git repo."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(fixture.path, dest, ignore=shutil.ignore_patterns("target", "graphify-out", "__pycache__"))
    apply_edits(dest, task.setup)
    (dest / ".gitignore").write_text(WORKSPACE_GITIGNORE, encoding="utf-8")
    _git(dest, "init", "-q")
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", "base")
    return dest


def clone_workspace(base: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(base, dest, ignore=shutil.ignore_patterns("target", "graphify-out", "__pycache__"))
    return dest


def collect_changes(ws: Path) -> Tuple[List[str], str]:
    """Returns (changed file paths, unified diff) relative to the base commit."""
    _git(ws, "add", "-A")
    names = [n for n in _git(ws, "diff", "--cached", "--name-only", "HEAD").splitlines() if n.strip()]
    diff = _git(ws, "diff", "--cached", "HEAD")
    _git(ws, "reset", "-q")
    return names, diff


def safe_write(ws: Path, rel: str, content: str) -> bool:
    """Writes a file only if it resolves inside the workspace."""
    target = (ws / rel).resolve()
    try:
        target.relative_to(ws.resolve())
    except ValueError:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return True


def list_repo_files(ws: Path) -> List[str]:
    out = _git(ws, "ls-files")
    return [line for line in out.splitlines() if line and line != ".gitignore"]
