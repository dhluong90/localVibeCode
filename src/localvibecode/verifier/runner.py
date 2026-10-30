"""Zero-Token Deterministic Verification Engine (Syntax, Contract Preservation, SAST, Unit Tests)."""

from __future__ import annotations

import ast
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

    FORBIDDEN_PATTERNS = ("eval(", "exec(", "shell=True")

    def __init__(self, repo_root: Path, test_command: List[str] | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.test_command = test_command or [
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
    def extract_top_level_symbols(source: str) -> Set[str]:
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

        source = file_path.read_text(encoding="utf-8")
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

        # Contract & Symbol Preservation Guardrail (prevents LLM from overwriting file with unrelated code)
        if previous_source.strip():
            prev_syms = self.extract_top_level_symbols(previous_source)
            new_syms = self.extract_top_level_symbols(source)
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
        py_files = [
            p.relative_to(self.repo_root).as_posix()
            for p in sorted(self.repo_root.rglob("*.py"))
            if ".venv" not in p.parts and "graphify-out" not in p.parts
        ]
        for rel_file in py_files:
            res = self.verify_file_syntax_and_security(rel_file)
            if not res.passed:
                return res

        # Run unit test suite
        try:
            proc = subprocess.run(
                self.test_command,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception as exc:
            return VerificationResult(
                passed=False,
                syntax_ok=True,
                security_ok=True,
                tests_ok=False,
                error_summary=f"Failed to execute test suite: {exc}",
                checked_files=py_files,
            )

        combined_out = (proc.stdout + "\n" + proc.stderr).strip()
        if proc.returncode != 0:
            return VerificationResult(
                passed=False,
                syntax_ok=True,
                security_ok=True,
                tests_ok=False,
                error_summary=f"Unit Tests Failed (exit code {proc.returncode}):\n{combined_out[-2000:]}",
                test_output=combined_out,
                checked_files=py_files,
            )

        return VerificationResult(
            passed=True,
            syntax_ok=True,
            security_ok=True,
            tests_ok=True,
            test_output=combined_out,
            checked_files=py_files,
        )
