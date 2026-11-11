"""Zero-Token Deterministic Verification Engine (Syntax, Contract Preservation, SAST, Unit Tests)."""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set


@dataclass
class VerificationResult:
    passed: bool
    syntax_ok: bool
    security_ok: bool
    tests_ok: bool
    error_summary: str = ""
    test_output: str = ""
    checked_files: List[str] = field(default_factory=list)


class ZeroTokenVerifier:
    """Runs fast CPU-only checks (0 LLM tokens): AST Syntax + Symbol Preservation + SAST + Unit Tests."""

    FORBIDDEN_PATTERNS = (
        "eval(",
        "exec(",
        "shell=True",
        "Runtime.getRuntime().exec",
        "ProcessBuilder(",
        "System.exit(",
    )

    def __init__(
        self, repo_root: Path, test_command: List[str] | None = None, test_timeout_sec: int | None = None
    ) -> None:
        self.test_timeout_sec = test_timeout_sec
        self.repo_root = repo_root.resolve()
        if test_command:
            self.test_command = test_command
        elif (self.repo_root / "pom.xml").exists():
            self.test_command = ["mvn", "test"]
        else:
            self.test_command = [
                "python3",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*.py",
            ]

    @staticmethod
    def extract_top_level_symbols(source: str, is_java: bool = False) -> Set[str]:
        if not is_java:
            try:
                tree = ast.parse(source)
            except SyntaxError:
                return set()
            symbols: Set[str] = set()
            for node in getattr(tree, "body", []):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.add(node.name)
                    if isinstance(node, ast.ClassDef):
                        for sub in node.body:
                            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                symbols.add(f"{node.name}.{sub.name}")
            return symbols

        # Java Symbol Extraction
        symbols = set()
        for m in re.finditer(r"\b(?:class|interface|record|enum)\s+([A-Za-z0-9_]+)", source):
            symbols.add(m.group(1))
        method_regex = re.compile(
            r"^\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:public|protected|private)\s+(?:(?:static|final|synchronized|abstract)\s+)*([A-Za-z0-9_<>,\[\]\s]+)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)",
            re.MULTILINE,
        )
        for m in method_regex.finditer(source):
            name = m.group(2)
            if name not in ("if", "for", "while", "switch", "catch"):
                symbols.add(name)
        return symbols

    def verify_file_syntax_and_security(
        self, rel_path: str, previous_source: str = ""
    ) -> VerificationResult:
        file_path = self.repo_root / rel_path
        if not file_path.exists():
            return VerificationResult(
                passed=False,
                syntax_ok=False,
                security_ok=False,
                tests_ok=False,
                error_summary=f"Target file `{rel_path}` does not exist.",
            )

        source = file_path.read_text(encoding="utf-8", errors="ignore")
        is_java = rel_path.endswith(".java")

        if not is_java:
            try:
                ast.parse(source, filename=rel_path)
            except SyntaxError as exc:
                return VerificationResult(
                    passed=False,
                    syntax_ok=False,
                    security_ok=True,
                    tests_ok=False,
                    error_summary=(
                        f"AST SyntaxError in `{rel_path}` line {exc.lineno}: {exc.msg}\n"
                        f"Offending line: {exc.text}"
                    ),
                    checked_files=[rel_path],
                )
        else:
            # Java bracket balance validation
            open_br = source.count("{")
            close_br = source.count("}")
            if open_br != close_br or (open_br == 0 and "interface " not in source and "class " not in source):
                return VerificationResult(
                    passed=False,
                    syntax_ok=False,
                    security_ok=True,
                    tests_ok=False,
                    error_summary=(
                        f"Java Syntax Error in `{rel_path}`: Unbalanced brackets (open '{{' count: {open_br}, close '}}' count: {close_br})."
                    ),
                    checked_files=[rel_path],
                )

        # Contract & Symbol Preservation Guardrail
        if previous_source.strip():
            prev_syms = self.extract_top_level_symbols(previous_source, is_java=is_java)
            new_syms = self.extract_top_level_symbols(source, is_java=is_java)
            missing = prev_syms - new_syms
            if missing:
                return VerificationResult(
                    passed=False,
                    syntax_ok=True,
                    security_ok=True,
                    tests_ok=False,
                    error_summary=(
                        f"Breaking Change Guardrail in `{rel_path}`: "
                        f"Existing required symbol(s) {sorted(missing)} were accidentally removed! "
                        f"You MUST preserve all existing classes and methods in `{rel_path}`."
                    ),
                    checked_files=[rel_path],
                )

        for idx, line in enumerate(source.splitlines(), start=1):
            for forbidden in self.FORBIDDEN_PATTERNS:
                if forbidden in line:
                    return VerificationResult(
                        passed=False,
                        syntax_ok=True,
                        security_ok=False,
                        tests_ok=False,
                        error_summary=(
                            f"Enterprise Security Violation in `{rel_path}` line {idx}: "
                            f"Forbidden pattern `{forbidden}` detected."
                        ),
                        checked_files=[rel_path],
                    )

        return VerificationResult(
            passed=True,
            syntax_ok=True,
            security_ok=True,
            tests_ok=True,
            checked_files=[rel_path],
        )

    def verify_workspace(self) -> VerificationResult:
        ignore_dirs = {".git", ".venv", "target", "build", "node_modules", "graphify-out"}
        checked_files: List[str] = []
        for ext in ("*.py", "*.java"):
            for p in sorted(self.repo_root.rglob(ext)):
                if not any(part in ignore_dirs for part in p.parts):
                    rel_file = p.relative_to(self.repo_root).as_posix()
                    checked_files.append(rel_file)
                    res = self.verify_file_syntax_and_security(rel_file)
                    if not res.passed:
                        return res

        # Run test suite
        try:
            timeout_sec = self.test_timeout_sec or (90 if (self.repo_root / "pom.xml").exists() else 30)
            proc = subprocess.run(
                self.test_command,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except Exception as exc:
            return VerificationResult(
                passed=False,
                syntax_ok=True,
                security_ok=True,
                tests_ok=False,
                error_summary=f"Failed to execute test suite ({self.test_command}): {exc}",
                checked_files=checked_files,
            )

        combined_out = (proc.stdout + "\n" + proc.stderr).strip()
        if proc.returncode != 0:
            return VerificationResult(
                passed=False,
                syntax_ok=True,
                security_ok=True,
                tests_ok=False,
                error_summary=f"Automated Tests Failed (exit code {proc.returncode}):\n{combined_out[-2000:]}",
                test_output=combined_out,
                checked_files=checked_files,
            )

        return VerificationResult(
            passed=True,
            syntax_ok=True,
            security_ok=True,
            tests_ok=True,
            test_output=combined_out,
            checked_files=checked_files,
        )
