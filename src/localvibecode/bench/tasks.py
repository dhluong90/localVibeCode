"""Benchmark task & fixture definitions (see docs/BENCHMARK_STANDARD.md, section 4)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Fixture:
    name: str
    language: str
    test_dir: str
    test_cmd: List[str]
    path: Path

    def is_test_file(self, rel: str) -> bool:
        return rel.startswith(self.test_dir.rstrip("/") + "/")


@dataclass
class Task:
    id: str
    category: str
    fixture: str
    split: str
    difficulty: str
    prompt: str
    gold_files: List[str]
    oracle_plan: List[Dict[str, str]]
    dir: Path
    setup: List[Dict[str, str]] = field(default_factory=list)
    fail_to_pass_base: List[str] = field(default_factory=list)
    t1: Optional[Dict[str, Any]] = None

    def _files_under(self, kind: str) -> Dict[str, Path]:
        root = self.dir / kind
        if not root.exists():
            return {}
        return {p.relative_to(root).as_posix(): p for p in sorted(root.rglob("*")) if p.is_file()}

    def hidden_files(self) -> Dict[str, Path]:
        return self._files_under("hidden")

    def reference_files(self) -> Dict[str, Path]:
        return self._files_under("reference")


def load_fixtures(bench_root: Path) -> Dict[str, Fixture]:
    data = json.loads((bench_root / "fixtures" / "fixtures.json").read_text(encoding="utf-8"))
    return {
        name: Fixture(
            name=name,
            language=cfg["language"],
            test_dir=cfg["test_dir"],
            test_cmd=list(cfg["test_cmd"]),
            path=(bench_root / "fixtures" / name).resolve(),
        )
        for name, cfg in data.items()
    }


def load_tasks(
    bench_root: Path, ids: Optional[List[str]] = None, split: Optional[str] = None
) -> List[Task]:
    tasks: List[Task] = []
    for task_json in sorted((bench_root / "tasks").glob("*/task.json")):
        raw = json.loads(task_json.read_text(encoding="utf-8"))
        task = Task(dir=task_json.parent, **raw)
        if ids and task.id not in ids:
            continue
        if split and task.split != split:
            continue
        tasks.append(task)
    return tasks


def apply_edits(root: Path, edits: List[Dict[str, str]]) -> None:
    """Applies exact find/replace edits; each `find` must occur exactly once."""
    for edit in edits:
        path = root / edit["file"]
        text = path.read_text(encoding="utf-8")
        count = text.count(edit["find"])
        if count != 1:
            raise ValueError(f"Edit target in {edit['file']} found {count} times: {edit['find']!r}")
        path.write_text(text.replace(edit["find"], edit["replace"]), encoding="utf-8")
