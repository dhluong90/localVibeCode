"""Blast-Radius Slicer: Extracts Surgical Context (< 4,000 tokens) for a Target File.

Instead of feeding the entire repository to the Local LLM, the Blast-Radius Slicer
constructs a deterministic 3-part Surgical Context:
1. TARGET FILE FULL SOURCE (with line numbers or exact blocks).
2. 1-HOP OUTBOUND DEPENDENCIES (Signatures, Class fields, and Docstrings ONLY — function bodies stripped!).
3. 1-HOP INBOUND CALLERS (Impact Radius contracts so the LLM avoids breaking changes).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from localvibecode.context.graph_builder import CodeKnowledgeGraph

_FENCE_LANG = {".java": "java", ".py": "python", ".ts": "typescript", ".tsx": "tsx", ".js": "javascript",
               ".jsx": "jsx", ".go": "go"}


def normalize_path(path: str):
    p = path.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p or None


@dataclass
class SurgicalContextSlice:
    target_file: str
    outbound_files: List[str]
    inbound_files: List[str]
    rendered_context: str
    approx_tokens: int


class BlastRadiusSlicer:
    """Slices the Code Knowledge Graph around a target file to stay < 4,000 tokens."""

    def __init__(self, repo_root: Path, graph: CodeKnowledgeGraph, max_chars: int = 14000) -> None:
        self.repo_root = repo_root.resolve()
        self.graph = graph
        self.max_chars = max_chars

    def slice_for_file(self, target_rel_path: str) -> SurgicalContextSlice:
        target_rel_path = normalize_path(target_rel_path) or target_rel_path.strip()
        full_path = self.repo_root / target_rel_path
        if full_path.exists():
            target_source = full_path.read_text(encoding="utf-8")
        else:
            target_source = "# [NEW FILE TO BE CREATED]"

        outbound = self.graph.file_imports.get(target_rel_path, [])
        inbound = self.graph.inbound_files.get(target_rel_path, [])
        lang = _FENCE_LANG.get(Path(target_rel_path).suffix, "")

        # The target file is always included in full; only neighbour signatures are cut to fit the cap.
        head = f"=== [1] TARGET FILE TO EDIT: `{target_rel_path}` ===\n```{lang}\n{target_source}\n```"
        budget = max(0, self.max_chars - len(head))
        neighbour_sections: List[str] = []
        truncated = False

        def add(text: str) -> None:
            nonlocal budget, truncated
            if len(text) + 1 <= budget:
                neighbour_sections.append(text)
                budget -= len(text) + 1
            else:
                truncated = True

        add("\n=== [2] 1-HOP OUTBOUND DEPENDENCIES (Signatures & Types ONLY - Bodies Stripped) ===")
        for dep_file in outbound or []:
            add(self._render_file_signatures(dep_file))
        if not outbound:
            add("(No internal module imports)")
        add("\n=== [3] 1-HOP INBOUND BLAST RADIUS (Callers that depend on this file - DO NOT BREAK CONTRACTS) ===")
        for caller_file in inbound or []:
            add(self._render_file_signatures(caller_file))
        if not inbound:
            add("(No internal callers depend on this file yet)")

        rendered = "\n".join([head] + neighbour_sections)
        if truncated:
            rendered += "\n... [Truncated to fit Surgical Context Cap]"

        approx_tokens = max(1, len(rendered) // 4)
        return SurgicalContextSlice(
            target_file=target_rel_path,
            outbound_files=outbound,
            inbound_files=inbound,
            rendered_context=rendered,
            approx_tokens=approx_tokens,
        )

    def _render_file_signatures(self, rel_file: str) -> str:
        lines = [f"--- File: `{rel_file}` ---"]
        symbols = [
            n
            for n in self.graph.nodes.values()
            if n.file_path == rel_file and n.kind in ("class", "function", "method")
        ]
        if not symbols:
            lines.append("  (No public classes/functions)")
            return "\n".join(lines)

        for sym in symbols:
            indent = "" if sym.kind in ("class", "function") else "    "
            lines.append(f"{indent}{sym.signature}")
            if sym.docstring:
                first_line = sym.docstring.splitlines()[0]
                lines.append(f'{indent}    """{first_line}"""')
        return "\n".join(lines)
