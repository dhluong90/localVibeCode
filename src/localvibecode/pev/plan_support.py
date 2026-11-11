"""Deterministic (0-token) helpers around planning and self-healing.

Round 00/00b showed three harness failure modes this module addresses:
- the full GRAPH_REPORT of a real repo (~1.3M chars on Apollo) does not fit any context window, so the
  planner needs a requirement-focused subgraph instead (`focused_context`);
- planners emit several steps for the same file and full-file rewrites then undo each other
  (`consolidate_plan`), and `lstrip("./")` mangled paths such as `.github/...` (`normalize_path`);
- self-healing always edited the last planned file instead of the file the failure points at
  (`files_in_failure_output`).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from localvibecode.context.graph_builder import CodeKnowledgeGraph

_IDENT = re.compile(r"\b([A-Z][A-Za-z0-9]{2,})\b")  # CamelCase type names: OrderService, ReleaseController
_PATH = re.compile(r"[\w./-]+\.(?:java|py|ts|tsx|js|go)\b")
_JAVA_FRAME = re.compile(r"at\s+((?:[\w$]+\.)+)([\w$]+)\.[\w$<>]+\(([\w$]+)\.java:\d+\)")
_JAVA_COMPILE = re.compile(r"(/[^\s:\[]+\.java):\[\d+")
_PY_FRAME = re.compile(r'File "([^"]+\.py)", line \d+')


def normalize_path(path: str) -> Optional[str]:
    """Normalises a repo-relative path from model output; None if it escapes the repository."""
    p = path.strip().strip("`'\"").replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    if not p or p.startswith("/") or any(part == ".." for part in p.split("/")):
        return None
    return p


def consolidate_plan(atomic_tasks: Sequence[Dict], repo_root: Path) -> Tuple[List[Dict], List[str]]:
    """One step per file (instructions merged, first-occurrence order); drops unsafe paths."""
    merged: Dict[str, Dict] = {}
    dropped: List[str] = []
    for task in atomic_tasks:
        target = normalize_path(str(task.get("target_file", "")))
        if target is None:
            dropped.append(str(task.get("target_file", "")))
            continue
        if target in merged:
            entry = merged[target]
            entry["instruction"] += "\n" + str(task.get("instruction", ""))
            criteria = str(task.get("verification_criteria", ""))
            if criteria:
                entry["verification_criteria"] = (entry.get("verification_criteria", "") + "\n" + criteria).strip()
        else:
            merged[target] = {**task, "target_file": target}
    steps = list(merged.values())
    for i, step in enumerate(steps, 1):
        step["step_id"] = i
    return steps, dropped


def _file_index(graph: CodeKnowledgeGraph) -> Dict[str, List[str]]:
    """Simple name (e.g. 'ReleaseService') -> files declaring it (file stem or class/function name)."""
    index: Dict[str, List[str]] = {}
    for node in graph.nodes.values():
        name = Path(node.file_path).stem if node.kind == "file" else node.name.split(".")[-1]
        index.setdefault(name, [])
        if node.file_path not in index[name]:
            index[name].append(node.file_path)
    return index


def files_mentioned(text: str, graph: CodeKnowledgeGraph) -> List[str]:
    """Repository files named in free text: paths, CamelCase type names, stack frames."""
    files = list(graph.file_imports.keys())
    found: List[str] = []

    def add(rel: str) -> None:
        if rel in graph.file_imports and rel not in found:
            found.append(rel)

    for raw in _PATH.findall(text):
        p = normalize_path(raw)
        if p:
            for rel in files:
                if rel == p or rel.endswith("/" + p) or p.endswith("/" + rel):
                    add(rel)
    index = _file_index(graph)
    for name in _IDENT.findall(text):
        for rel in index.get(name, []):
            if Path(rel).stem == name:  # prefer the file that declares the type
                add(rel)
    return found


def files_in_failure_output(output: str, graph: CodeKnowledgeGraph, repo_root: Path) -> List[str]:
    """Files a test/compile failure points at, most specific first (compile errors, then stack frames)."""
    root = str(repo_root.resolve())
    found: List[str] = []

    def add(rel: str) -> None:
        if rel in graph.file_imports and rel not in found:
            found.append(rel)

    for abs_path in _JAVA_COMPILE.findall(output):
        if abs_path.startswith(root):
            add(abs_path[len(root):].lstrip("/"))
    index = _file_index(graph)
    for _pkg, cls, file_stem in _JAVA_FRAME.findall(output):
        for rel in index.get(file_stem, []):
            add(rel)
    for py in _PY_FRAME.findall(output):
        p = py[len(root):].lstrip("/") if py.startswith(root) else normalize_path(py)
        if p:
            add(p)
    return found


def is_test_path(rel: str) -> bool:
    return "/src/test/" in "/" + rel or rel.startswith("tests/") or "/tests/" in rel or Path(rel).name.startswith("test_")


def focused_context(
    requirement: str,
    graph: CodeKnowledgeGraph,
    failure_output: str = "",
    repo_root: Optional[Path] = None,
    max_chars: int = 24000,
) -> Tuple[str, List[str]]:
    """Requirement-focused view of the code graph for the planner, bounded by `max_chars`.

    Seeds = files named in the requirement and in any failure output; expanded with their 1-hop
    outbound dependencies and inbound callers. Each file is rendered as its public signatures.
    """
    seeds = files_mentioned(requirement, graph)
    if failure_output and repo_root is not None:
        for rel in files_in_failure_output(failure_output, graph, repo_root):
            if rel not in seeds:
                seeds.append(rel)
    ordered: List[str] = list(seeds)
    for rel in seeds:
        for dep in graph.file_imports.get(rel, []) + graph.inbound_files.get(rel, []):
            if dep not in ordered:
                ordered.append(dep)
    if not ordered:  # nothing named: fall back to the most central files
        ordered = [f for f, _ in graph.god_nodes[:15]]

    by_file: Dict[str, List[str]] = {}
    for node in graph.nodes.values():
        if node.kind in ("class", "function", "method"):
            by_file.setdefault(node.file_path, []).append(
                ("    " if node.kind == "method" else "") + node.signature.strip())
    parts: List[str] = []
    used = 0
    included: List[str] = []
    for rel in ordered:
        tag = "named in requirement/failure" if rel in seeds else "1-hop neighbour"
        block = f"--- {rel} ({tag})\n" + "\n".join(by_file.get(rel, ["(no declarations parsed)"])[:40])
        if used + len(block) > max_chars:
            if rel in seeds and used < max_chars:
                block = block[: max_chars - used]
            else:
                continue
        parts.append(block)
        included.append(rel)
        used += len(block)
    return "\n".join(parts), included


def mentions_failure(requirement: str) -> bool:
    return re.search(r"\b(fail\w*|error|exception|crash\w*|bug|incident|broken|regression)\b",
                     requirement, re.IGNORECASE) is not None


def unique(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    return [i for i in items if not (i in seen or seen.add(i))]
