"""Configuration and Enterprise Guardrails Loader for localVibeCode."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class LocalVibeCodeConfig:
    ollama_base_url: str = "http://localhost:11434"
    primary_model: str = "qwen2.5:7b"
    fallback_model: str = "gemma4:latest"
    keep_alive: str = "-1m"
    num_ctx: int = 8192
    temperature_plan: float = 0.1
    temperature_execute: float = 0.0
    temperature_verify: float = 0.1
    max_surgical_context_chars: int = 14000  # ~3,500 tokens
    max_self_healing_retries: int = 3
    target_repo_path: str = "demo_enterprise_repo"
    graph_output_dir: str = "graphify-out"
    enterprise_rules_dir: str = "enterprise_rules"
    test_command: List[str] = field(
        default_factory=lambda: [
            "python3",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
        ]
    )
    workspace_root: Path = field(default_factory=Path.cwd)

    @classmethod
    def load(cls, workspace_root: Path | None = None) -> "LocalVibeCodeConfig":
        root = (workspace_root or Path.cwd()).resolve()
        # Look for localvibecode.json first, then aisdlc_config.json
        for candidate in ("localvibecode.json", "aisdlc_config.json"):
            cfg_path = root / candidate
            if cfg_path.exists():
                try:
                    data = json.loads(cfg_path.read_text(encoding="utf-8"))
                    return cls(**data, workspace_root=root)
                except Exception:
                    pass
        return cls(workspace_root=root)

    def resolve_repo_path(self, custom_repo: str | Path | None = None) -> Path:
        if custom_repo:
            p = Path(custom_repo)
            if p.is_absolute():
                resolved = p.resolve()
            elif (Path.cwd() / p).exists():
                resolved = (Path.cwd() / p).resolve()
            else:
                resolved = (self.workspace_root / p).resolve()
        else:
            resolved = (self.workspace_root / self.target_repo_path).resolve()

        # Auto-detect test runner for resolved repository if default python test_command is set
        if (resolved / "pom.xml").exists() and self.test_command == [
            "python3",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
        ]:
            self.test_command = ["mvn", "test"]

        return resolved

    def load_enterprise_rules(self) -> str:
        rules_dir = self.workspace_root / self.enterprise_rules_dir
        if not rules_dir.exists():
            return "Follow Clean Architecture, strict type annotations, and backward compatibility."
        chunks: List[str] = []
        for md_file in sorted(rules_dir.glob("*.md")):
            chunks.append(md_file.read_text(encoding="utf-8").strip())
        return "\n\n".join(chunks)


# Backward-compatible alias
AISDLCConfig = LocalVibeCodeConfig
