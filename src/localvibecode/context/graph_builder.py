"""Graphify-style Deterministic AST Code Knowledge Graph Builder (0 LLM Tokens).

Parses a codebase locally using deterministic AST analysis (Python `ast` + regex fallback
for TS/JS) to generate:
1. `graphify-out/graph.json`: Full structural graph with Nodes (files, classes, functions)
   and Edges (`IMPORTS`, `CALLS`, `INHERITS`) tagged with `EXTRACTED` or `INFERRED`.
2. `graphify-out/GRAPH_REPORT.md`: Architectural summary highlighting God Nodes (core modules
   with highest degree centrality), Subsystem Clusters, and Public API Signatures.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass
class SymbolNode:
    id: str  # e.g., "services/order_service.py::OrderService.create_order"
    name: str
    kind: str  # "file" | "class" | "function" | "method"
    file_path: str  # relative to repo root
    line_start: int
    line_end: int
    signature: str
    docstring: str = ""


@dataclass
class GraphEdge:
    source: str  # file or symbol id
    target: str  # file or symbol id
    relation: str  # "IMPORTS" | "CALLS" | "INHERITS" | "CONTAINS"
    confidence: str = "EXTRACTED"  # "EXTRACTED" | "INFERRED"


@dataclass
class CodeKnowledgeGraph:
    repo_root: str
    nodes: Dict[str, SymbolNode] = field(default_factory=dict)
    edges: List[GraphEdge] = field(default_factory=list)
    file_imports: Dict[str, List[str]] = field(default_factory=dict)  # rel_file -> [target_rel_files]
    inbound_files: Dict[str, List[str]] = field(default_factory=dict)  # rel_file -> [caller_rel_files]
    god_nodes: List[Tuple[str, int]] = field(default_factory=list)


class DeterministicGraphBuilder:
    """Builds a Graphify-compatible Code Knowledge Graph with 0 LLM tokens."""

    IGNORE_DIRS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".next",
        "target",
        "graphify-out",
        ".pytest_cache",
    }
    SUPPORTED_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java"}

    def __init__(self, repo_root: Path, output_dir_name: str = "graphify-out") -> None:
        self.repo_root = repo_root.resolve()
        self.output_dir = self.repo_root / output_dir_name

    def build(self) -> CodeKnowledgeGraph:
        graph = CodeKnowledgeGraph(repo_root=str(self.repo_root))
        py_files = [
            p
            for p in sorted(self.repo_root.rglob("*.py"))
            if not any(part in self.IGNORE_DIRS for part in p.parts)
        ]
        java_files = [
            p
            for p in sorted(self.repo_root.rglob("*.java"))
            if not any(part in self.IGNORE_DIRS for part in p.parts)
        ]

        # Map module dotted names to relative file paths for deterministic import resolution
        module_to_file: Dict[str, str] = {}
        symbol_to_file: Dict[str, str] = {}

        # 1. Index Python Files
        for py_file in py_files:
            rel_path = py_file.relative_to(self.repo_root).as_posix()
            mod_name = rel_path[:-3].replace("/", ".")
            if mod_name.endswith(".__init__"):
                mod_name = mod_name[: -len(".__init__")]
            module_to_file[mod_name] = rel_path
            short_mod = py_file.stem
            module_to_file.setdefault(short_mod, rel_path)

            graph.nodes[rel_path] = SymbolNode(
                id=rel_path,
                name=py_file.name,
                kind="file",
                file_path=rel_path,
                line_start=1,
                line_end=len(py_file.read_text(encoding="utf-8", errors="ignore").splitlines()),
                signature=f"file {rel_path}",
            )
            graph.file_imports[rel_path] = []
            graph.inbound_files.setdefault(rel_path, [])

        # 2. Index Java Files
        for j_file in java_files:
            rel_path = j_file.relative_to(self.repo_root).as_posix()
            class_name = j_file.stem
            symbol_to_file[class_name] = rel_path
            try:
                j_content = j_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                j_content = ""
            lines = j_content.splitlines()
            pkg_name = ""
            for l in lines:
                l_str = l.strip()
                if l_str.startswith("package ") and l_str.endswith(";"):
                    pkg_name = l_str[8:-1].strip()
                    break
            full_fqcn = f"{pkg_name}.{class_name}" if pkg_name else class_name
            module_to_file[full_fqcn] = rel_path
            module_to_file.setdefault(class_name, rel_path)

            graph.nodes[rel_path] = SymbolNode(
                id=rel_path,
                name=j_file.name,
                kind="file",
                file_path=rel_path,
                line_start=1,
                line_end=len(lines),
                signature=f"class {full_fqcn}",
            )
            graph.file_imports[rel_path] = []
            graph.inbound_files.setdefault(rel_path, [])

        # Pass 1: Extract classes, functions, methods, signatures, and docstrings
        parsed_trees: Dict[str, ast.AST] = {}
        for py_file in py_files:
            rel_path = py_file.relative_to(self.repo_root).as_posix()
            source = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=rel_path)
            except SyntaxError:
                continue
            parsed_trees[rel_path] = tree
            lines = source.splitlines()

            file_doc = ast.get_docstring(tree) or ""
            graph.nodes[rel_path].docstring = file_doc.splitlines()[0] if file_doc else ""

            for node in getattr(tree, "body", []):
                if isinstance(node, ast.ClassDef):
                    cls_id = f"{rel_path}::{node.name}"
                    bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
                    base_str = f"({', '.join(bases)})" if bases else ""
                    cls_sig = f"class {node.name}{base_str}:"
                    cls_doc = (ast.get_docstring(node) or "").strip()
                    graph.nodes[cls_id] = SymbolNode(
                        id=cls_id,
                        name=node.name,
                        kind="class",
                        file_path=rel_path,
                        line_start=node.lineno,
                        line_end=getattr(node, "end_lineno", node.lineno),
                        signature=cls_sig,
                        docstring=cls_doc,
                    )
                    symbol_to_file[node.name] = rel_path
                    graph.edges.append(
                        GraphEdge(source=rel_path, target=cls_id, relation="CONTAINS", confidence="EXTRACTED")
                    )

                    # Extract class attributes/fields and methods
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            m_id = f"{cls_id}.{item.name}"
                            m_sig = self._format_func_signature(item, lines)
                            m_doc = (ast.get_docstring(item) or "").strip()
                            graph.nodes[m_id] = SymbolNode(
                                id=m_id,
                                name=f"{node.name}.{item.name}",
                                kind="method",
                                file_path=rel_path,
                                line_start=item.lineno,
                                line_end=getattr(item, "end_lineno", item.lineno),
                                signature=m_sig,
                                docstring=m_doc,
                            )
                            symbol_to_file[item.name] = rel_path
                            graph.edges.append(
                                GraphEdge(
                                    source=cls_id,
                                    target=m_id,
                                    relation="CONTAINS",
                                    confidence="EXTRACTED",
                                )
                            )
                        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            field_line = ast.unparse(item) if hasattr(ast, "unparse") else item.target.id
                            graph.nodes[cls_id].signature += f"\n    {field_line}"

                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn_id = f"{rel_path}::{node.name}"
                    fn_sig = self._format_func_signature(node, lines)
                    fn_doc = (ast.get_docstring(node) or "").strip()
                    graph.nodes[fn_id] = SymbolNode(
                        id=fn_id,
                        name=node.name,
                        kind="function",
                        file_path=rel_path,
                        line_start=node.lineno,
                        line_end=getattr(node, "end_lineno", node.lineno),
                        signature=fn_sig,
                        docstring=fn_doc,
                    )
                    symbol_to_file[node.name] = rel_path
                    graph.edges.append(
                        GraphEdge(source=rel_path, target=fn_id, relation="CONTAINS", confidence="EXTRACTED")
                    )

        # Pass 2: Extract IMPORTS and CALLS edges across files
        for rel_path, tree in parsed_trees.items():
            imported_files: Set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        target_file = self._resolve_module(alias.name, module_to_file)
                        if target_file and target_file != rel_path:
                            imported_files.add(target_file)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    target_file = self._resolve_module(mod, module_to_file)
                    if target_file and target_file != rel_path:
                        imported_files.add(target_file)
                    for alias in node.names:
                        sym_target = symbol_to_file.get(alias.name)
                        if sym_target and sym_target != rel_path:
                            imported_files.add(sym_target)
                elif isinstance(node, ast.Call):
                    callee_name = self._extract_call_name(node)
                    if callee_name and callee_name in symbol_to_file:
                        target_file = symbol_to_file[callee_name]
                        if target_file != rel_path:
                            graph.edges.append(
                                GraphEdge(
                                    source=rel_path,
                                    target=f"{target_file}::{callee_name}",
                                    relation="CALLS",
                                    confidence="INFERRED",
                                )
                            )

            for target_file in sorted(imported_files):
                graph.file_imports[rel_path].append(target_file)
                if rel_path not in graph.inbound_files.setdefault(target_file, []):
                    graph.inbound_files[target_file].append(rel_path)
                graph.edges.append(
                    GraphEdge(
                        source=rel_path,
                        target=target_file,
                        relation="IMPORTS",
                        confidence="EXTRACTED",
                    )
                )

        # Pass 3: Extract Java Classes, Interfaces, Methods, and IMPORTS/CALLS
        for j_file in java_files:
            rel_path = j_file.relative_to(self.repo_root).as_posix()
            try:
                j_source = j_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            self._parse_java_file(rel_path, j_source, graph, module_to_file, symbol_to_file)

        # Compute God Nodes (Files ranked by total Inbound + Outbound structural degree)
        degrees: List[Tuple[str, int]] = []
        for rel_path in graph.file_imports:
            out_deg = len(graph.file_imports.get(rel_path, []))
            in_deg = len(graph.inbound_files.get(rel_path, []))
            degrees.append((rel_path, in_deg * 2 + out_deg))
        degrees.sort(key=lambda x: x[1], reverse=True)
        graph.god_nodes = degrees

        self._write_artifacts(graph)
        return graph

    @staticmethod
    def _parse_java_file(
        rel_path: str,
        content: str,
        graph: CodeKnowledgeGraph,
        module_to_file: Dict[str, str],
        symbol_to_file: Dict[str, str],
    ) -> None:
        lines = content.splitlines()
        imported_files: Set[str] = set()

        # 1. Imports
        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith("import ") and trimmed.endswith(";"):
                imported = trimmed[7:-1].strip()
                # Resolve package.Class to relative file path
                if imported in module_to_file:
                    target_file = module_to_file[imported]
                    if target_file != rel_path:
                        imported_files.add(target_file)
                else:
                    short_cls = imported.split(".")[-1]
                    if short_cls in symbol_to_file:
                        target_file = symbol_to_file[short_cls]
                        if target_file != rel_path:
                            imported_files.add(target_file)

        # 2. Classes / Interfaces / Records
        class_regex = re.compile(
            r"^\s*(public|protected|private)?\s*(abstract|final|static)?\s*(class|interface|record|enum)\s+([A-Za-z0-9_]+)(?:<[^>]+>)?(?:\s+extends\s+[A-Za-z0-9_<,>\s]+)?(?:\s+implements\s+[A-Za-z0-9_<,>\s]+)?"
        )
        # 3. Methods
        method_regex = re.compile(
            r"^\s*(?:@\w+(?:\([^)]*\))?\s*)*(public|protected|private)\s+(?:(static|final|synchronized|abstract)\s+)*([A-Za-z0-9_<>,\[\]\s]+)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)"
        )

        current_class_id = None
        for idx, line in enumerate(lines, start=1):
            cl_match = class_regex.match(line)
            if cl_match:
                cls_name = cl_match.group(4)
                cls_id = f"{rel_path}::{cls_name}"
                current_class_id = cls_id
                sig = line.strip().rstrip("{").strip()
                graph.nodes[cls_id] = SymbolNode(
                    id=cls_id,
                    name=cls_name,
                    kind="class",
                    file_path=rel_path,
                    line_start=idx,
                    line_end=idx,
                    signature=sig,
                    docstring="",
                )
                graph.edges.append(
                    GraphEdge(source=rel_path, target=cls_id, relation="CONTAINS", confidence="EXTRACTED")
                )
                continue

            m_match = method_regex.match(line)
            if m_match and current_class_id:
                m_name = m_match.group(4)
                # Ignore control flow keywords that look like methods
                if m_name in ("if", "for", "while", "switch", "catch"):
                    continue
                m_id = f"{current_class_id}.{m_name}"
                m_sig = line.strip().rstrip("{").strip()
                graph.nodes[m_id] = SymbolNode(
                    id=m_id,
                    name=m_name,
                    kind="method",
                    file_path=rel_path,
                    line_start=idx,
                    line_end=idx,
                    signature=m_sig,
                    docstring="",
                )
                graph.edges.append(
                    GraphEdge(
                        source=current_class_id,
                        target=m_id,
                        relation="CONTAINS",
                        confidence="EXTRACTED",
                    )
                )

        # 4. Check for Calls across files
        for other_sym, other_file in symbol_to_file.items():
            if other_file != rel_path and re.search(r"\b" + re.escape(other_sym) + r"\b", content):
                imported_files.add(other_file)
                graph.edges.append(
                    GraphEdge(
                        source=rel_path,
                        target=other_file,
                        relation="CALLS",
                        confidence="INFERRED",
                    )
                )

        for target_file in sorted(imported_files):
            if target_file not in graph.file_imports.setdefault(rel_path, []):
                graph.file_imports[rel_path].append(target_file)
            if rel_path not in graph.inbound_files.setdefault(target_file, []):
                graph.inbound_files[target_file].append(rel_path)
            graph.edges.append(
                GraphEdge(
                    source=rel_path,
                    target=target_file,
                    relation="IMPORTS",
                    confidence="EXTRACTED",
                )
            )

    @staticmethod
    def _resolve_module(mod_name: str, module_to_file: Dict[str, str]) -> str | None:
        if mod_name in module_to_file:
            return module_to_file[mod_name]
        parts = mod_name.split(".")
        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in module_to_file:
                return module_to_file[candidate]
        if parts and parts[-1] in module_to_file:
            return module_to_file[parts[-1]]
        return None

    @staticmethod
    def _extract_call_name(call_node: ast.Call) -> str | None:
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        if isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return None

    @staticmethod
    def _format_func_signature(node: ast.FunctionDef | ast.AsyncFunctionDef, lines: List[str]) -> str:
        prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
        if hasattr(ast, "unparse"):
            args_str = ast.unparse(node.args)
            ret_str = f" -> {ast.unparse(node.returns)}" if node.returns else ""
            return f"{prefix}{node.name}({args_str}){ret_str}:"
        return lines[node.lineno - 1].strip()

    def _write_artifacts(self, graph: CodeKnowledgeGraph) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.output_dir / "graph.json"
        report_path = self.output_dir / "GRAPH_REPORT.md"

        serializable = {
            "repo_root": graph.repo_root,
            "god_nodes": [{"file": f, "centrality_score": s} for f, s in graph.god_nodes],
            "file_imports": graph.file_imports,
            "inbound_files": graph.inbound_files,
            "nodes": {k: asdict(v) for k, v in graph.nodes.items()},
            "edges": [asdict(e) for e in graph.edges],
        }
        json_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        report_path.write_text(self.render_markdown_report(graph), encoding="utf-8")

    @staticmethod
    def render_markdown_report(graph: CodeKnowledgeGraph) -> str:
        lines: List[str] = [
            "# GRAPH_REPORT.md — Deterministic AST Knowledge Graph",
            "",
            "## 1. Architectural God Nodes (Core Centrality Ranking)",
        ]
        for file_path, score in graph.god_nodes:
            in_callers = graph.inbound_files.get(file_path, [])
            out_deps = graph.file_imports.get(file_path, [])
            doc = graph.nodes[file_path].docstring
            lines.append(
                f"- **`{file_path}`** (Score: `{score}`) — {doc or 'Module'}"
                f" | Inbound Callers: `{in_callers}` | Outbound Imports: `{out_deps}`"
            )

        lines.append("\n## 2. Repository Structural Skeleton (Signatures Only)")
        file_nodes = [n for n in graph.nodes.values() if n.kind == "file"]
        for fnode in file_nodes:
            lines.append(f"\n### File: `{fnode.file_path}`")
            children = [
                n for n in graph.nodes.values() if n.file_path == fnode.file_path and n.kind != "file"
            ]
            for child in children:
                indent = "  " if child.kind in ("class", "function") else "    "
                doc_suffix = f"  # {child.docstring.splitlines()[0]}" if child.docstring else ""
                lines.append(f"{indent}- `{child.signature}`{doc_suffix}")

        return "\n".join(lines) + "\n"
