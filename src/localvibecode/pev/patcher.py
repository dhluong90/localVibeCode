"""Surgical Code Patcher supporting Constrained JSON, SEARCH/REPLACE, and Full-File Fallback."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class PatchOutcome:
    applied: bool
    mode: str  # "json_constrained" | "search_replace" | "full_file" | "failed"
    message: str


class SurgicalPatcher:
    """Applies LLM-generated edits deterministically with JSON Schema + indentation normalization."""

    SEARCH_REPLACE_PATTERN = re.compile(
        r"<<<<<<<\s*SEARCH\s*\n(.*?)\n=======\s*\n(.*?)\n>>>>>>>\s*REPLACE",
        re.DOTALL,
    )
    CODE_FENCE_PATTERN = re.compile(r"```[A-Za-z0-9_+-]*[ \t]*\n(.*?)```", re.DOTALL)

    @classmethod
    def apply_llm_output(cls, file_path: Path, llm_text: str) -> PatchOutcome:
        original = file_path.read_text(encoding="utf-8") if file_path.exists() else ""

        # 1. Try Constrained JSON Schema output first (`{"reasoning": "...", "updated_code": "..."}`)
        try:
            parsed = json.loads(llm_text)
            if isinstance(parsed, dict) and "updated_code" in parsed:
                code = str(parsed["updated_code"]).strip()
                fences = cls.CODE_FENCE_PATTERN.findall(code)
                if fences:
                    code = max(fences, key=len).strip()
                if code:
                    code = cls._sanitize_json_escaped_python(code)
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(code + "\n", encoding="utf-8")
                    return PatchOutcome(
                        applied=True,
                        mode="json_constrained",
                        message=f"Applied Constrained JSON patch ({parsed.get('reasoning', '')}).",
                    )
        except Exception:
            pass

        # 2. Try SEARCH/REPLACE blocks
        blocks: List[Tuple[str, str]] = cls.SEARCH_REPLACE_PATTERN.findall(llm_text)
        if blocks and original:
            updated = original
            applied_count = 0
            for search_part, replace_part in blocks:
                matched, updated = cls._replace_block(updated, search_part, replace_part)
                if matched:
                    applied_count += 1
            if applied_count == len(blocks):
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(updated, encoding="utf-8")
                return PatchOutcome(
                    applied=True,
                    mode="search_replace",
                    message=f"Applied {applied_count} surgical SEARCH/REPLACE block(s).",
                )

        # 3. Fallback: first Python code fence
        fences = cls.CODE_FENCE_PATTERN.findall(llm_text)
        if fences:
            candidate = cls._sanitize_json_escaped_python(max(fences, key=len).strip()) + "\n"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(candidate, encoding="utf-8")
            return PatchOutcome(
                applied=True,
                mode="full_file",
                message="Applied first code block replacement.",
            )

        return PatchOutcome(
            applied=False,
            mode="failed",
            message="Could not find valid JSON `updated_code`, SEARCH/REPLACE block, or Python code block.",
        )

    @staticmethod
    def _replace_block(source: str, search_block: str, replace_block: str) -> Tuple[bool, str]:
        if search_block in source:
            return True, source.replace(search_block, replace_block, 1)

        src_lines = [line.rstrip() for line in source.splitlines()]
        search_lines = [line.rstrip() for line in search_block.splitlines()]
        if not search_lines:
            return False, source

        n = len(search_lines)
        for idx in range(len(src_lines) - n + 1):
            if src_lines[idx : idx + n] == search_lines:
                orig_lines = source.splitlines()
                new_lines = orig_lines[:idx] + replace_block.splitlines() + orig_lines[idx + n :]
                return True, "\n".join(new_lines) + "\n"

        return False, source

    @staticmethod
    def _sanitize_json_escaped_python(code: str) -> str:
        """Deterministically repairs common 7B JSON-escaping glitches (e.g. `\"\"\"...\"\"` on single-line docstrings)."""
        fixed_lines: List[str] = []
        for line in code.splitlines():
            stripped = line.strip()
            if (
                stripped.startswith('"""')
                and len(stripped) > 5
                and stripped.endswith('""')
                and not stripped.endswith('"""')
            ):
                line = line.rstrip() + '"'
            fixed_lines.append(line)
        return "\n".join(fixed_lines)
