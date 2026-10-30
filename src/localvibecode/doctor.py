"""Preflight Diagnostic and Environment Health Check for localVibeCode.

Validates that the host environment has all prerequisites to run 100% offline
local vibe coding (Python, RAM, Ollama daemon, recommended coding models, and Git).
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from localvibecode.ui import Colors, badge, error, info, rule, success, warning


@dataclass
class DiagnosticItem:
    category: str
    name: str
    status: bool  # True = Pass, False = Fail/Warning
    details: str
    fix_advice: Optional[str] = None


@dataclass
class DoctorReport:
    items: List[DiagnosticItem] = field(default_factory=list)
    ollama_running: bool = False
    installed_models: List[str] = field(default_factory=list)
    recommended_model_present: bool = False
    all_critical_passed: bool = True


RECOMMENDED_MODELS = [
    "qwen2.5-coder:14b",
    "qwen2.5-coder:7b",
    "qwen2.5:7b",
    "gemma4:latest",
    "qwen2.5:14b",
    "deepseek-r1:14b",
    "deepseek-r1:8b",
]


class PreflightDoctor:
    """Performs system diagnostics and environment checks."""

    def __init__(self, ollama_url: str = "http://localhost:11434") -> None:
        self.ollama_url = ollama_url.rstrip("/")

    def run_diagnostics(self) -> DoctorReport:
        report = DoctorReport()

        # 1. Check Python version
        py_ver = sys.version_info
        py_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
        py_ok = py_ver >= (3, 9)
        report.items.append(
            DiagnosticItem(
                category="Runtime",
                name="Python Version",
                status=py_ok,
                details=f"Python {py_str} ({sys.executable})",
                fix_advice=None if py_ok else "Install Python >= 3.9 (e.g. `brew install python` or `uv python install 3.11`).",
            )
        )
        if not py_ok:
            report.all_critical_passed = False

        # 2. Check System Memory (RAM)
        ram_gb = self._get_system_ram_gb()
        ram_ok = ram_gb >= 12.0
        details_ram = f"{ram_gb:.1f} GB RAM / Unified Memory detected ({platform.system()} {platform.machine()})"
        advice_ram = None
        if ram_gb < 12.0:
            advice_ram = (
                f"Your machine has {ram_gb:.1f} GB RAM. Local Vibe Coding is optimal with >= 16GB. "
                "Use a smaller 7B model (qwen2.5-coder:7b or qwen2.5:7b) to prevent memory pressure."
            )
        report.items.append(
            DiagnosticItem(
                category="Hardware",
                name="System Memory",
                status=ram_ok,
                details=details_ram,
                fix_advice=advice_ram,
            )
        )

        # 3. Check Git
        git_path = shutil.which("git")
        git_ok = git_path is not None
        report.items.append(
            DiagnosticItem(
                category="Toolchain",
                name="Git CLI",
                status=git_ok,
                details=f"Found at {git_path}" if git_ok else "Git executable not found in PATH",
                fix_advice=None if git_ok else "Install git via package manager (e.g. `brew install git` or `apt install git`).",
            )
        )
        if not git_ok:
            report.all_critical_passed = False

        # 4. Check Ollama Binary
        ollama_bin = shutil.which("ollama")
        ollama_bin_ok = ollama_bin is not None
        report.items.append(
            DiagnosticItem(
                category="Inference",
                name="Ollama Binary",
                status=ollama_bin_ok,
                details=f"Found at {ollama_bin}" if ollama_bin_ok else "Ollama CLI not found in PATH",
                fix_advice=None if ollama_bin_ok else "Install Ollama from https://ollama.com/download (e.g., `brew install ollama`).",
            )
        )

        # 5. Check Ollama Daemon Status
        models, is_running = self._check_ollama_daemon()
        report.ollama_running = is_running
        report.installed_models = models
        report.items.append(
            DiagnosticItem(
                category="Inference",
                name="Ollama Daemon Service",
                status=is_running,
                details=f"Responding at {self.ollama_url} ({len(models)} model(s) installed)"
                if is_running
                else f"Cannot connect to {self.ollama_url}",
                fix_advice=None
                if is_running
                else "Start the Ollama daemon by running `ollama serve` in a terminal or launching the Ollama desktop app.",
            )
        )
        if not is_running:
            report.all_critical_passed = False

        # 6. Check for Coding Models
        if is_running:
            matching = [m for m in models if any(rec in m for rec in RECOMMENDED_MODELS)]
            has_rec = len(matching) > 0
            report.recommended_model_present = has_rec
            report.items.append(
                DiagnosticItem(
                    category="Inference",
                    name="Coding LLM Models",
                    status=has_rec,
                    details=f"Available: {matching}" if has_rec else f"No recommended coding model found among: {models}",
                    fix_advice=None
                    if has_rec
                    else (
                        "Pull a recommended coding model:\n"
                        "  → For high speed: `ollama pull qwen2.5-coder:7b`\n"
                        "  → For peak reasoning: `ollama pull qwen2.5-coder:14b`"
                    ),
                )
            )
            if not has_rec:
                report.all_critical_passed = False

        return report

    def print_report(self, report: DoctorReport) -> None:
        rule("SYSTEM PREFLIGHT DIAGNOSTICS")
        for item in report.items:
            status_badge = badge("PASS", Colors.GREEN) if item.status else badge("WARN", Colors.YELLOW)
            print(f"  {status_badge} {Colors.BOLD}{item.name}{Colors.RESET} ({item.category})")
            print(f"         {Colors.GRAY}↳ {item.details}{Colors.RESET}")
            if item.fix_advice:
                print(f"         {Colors.YELLOW}⚡ Advice: {item.fix_advice}{Colors.RESET}")

        rule()
        if report.all_critical_passed:
            success("All environment checks passed! localVibeCode is 100% ready to run offline.")
        else:
            warning("Some prerequisites need attention before running local vibe coding tasks.")

    def ensure_model_ready(self, desired_model: str) -> bool:
        """Checks if desired model is installed, prompts to pull if missing."""
        models, is_running = self._check_ollama_daemon()
        if not is_running:
            error(f"Ollama is not running at {self.ollama_url}. Please run `ollama serve` first.")
            return False

        if any(desired_model == m or desired_model in m for m in models):
            return True

        warning(f"Model '{desired_model}' is not installed in local Ollama.")
        print(f"{Colors.CYAN}Would you like localVibeCode to download '{desired_model}' via `ollama pull` now? (Y/n){Colors.RESET} ", end="", flush=True)
        try:
            choice = sys.stdin.readline().strip().lower()
        except Exception:
            choice = "n"

        if choice in ("", "y", "yes"):
            info(f"Executing: ollama pull {desired_model}")
            res = subprocess.run(["ollama", "pull", desired_model])
            return res.returncode == 0
        else:
            info(f"Skipped download. You can manually run: `ollama pull {desired_model}`.")
            return False

    def _check_ollama_daemon(self) -> Tuple[List[str], bool]:
        url = f"{self.ollama_url}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                return models, True
        except Exception:
            return [], False

    @staticmethod
    def _get_system_ram_gb() -> float:
        system = platform.system()
        if system == "Darwin":
            try:
                out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
                return int(out.strip()) / (1024**3)
            except Exception:
                return 16.0
        elif system == "Linux":
            try:
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            return kb / (1024**2)
            except Exception:
                return 16.0
        return 16.0
