"""Command Line Interface for localVibeCode (`localvibecode` / `lvc`)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from localvibecode.config import LocalVibeCodeConfig
from localvibecode.context.graph_builder import DeterministicGraphBuilder
from localvibecode.context.slicer import BlastRadiusSlicer
from localvibecode.doctor import PreflightDoctor
from localvibecode.pev.state_machine import DeterministicPEVStateMachine
from localvibecode.ui import (
    BANNER,
    Colors,
    badge,
    error,
    info,
    rule,
    step,
    success,
    warning,
)
from localvibecode.verifier.runner import ZeroTokenVerifier


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="localvibecode",
        description="localVibeCode: Enterprise Local Vibe Coding Engine (100% Offline • Graphify AST • PEV Loop)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check environment, Ollama service, and coding models:
  localvibecode doctor

  # Onboard an existing codebase to localVibeCode (OpenCode & VS Code ready):
  localvibecode init /path/to/my-project

  # Execute a feature/refactor task offline with 1 local pinned model:
  localvibecode pev "Add 20% discount for ENTERPRISE tier in order service and add test"

  # Inspect Graphify AST architectural God Nodes:
  localvibecode graph

  # View surgical 1-hop context (< 4K tokens) for a specific file:
  localvibecode slice services/order_service.py

  # Run zero-token local verification (AST check + SAST security + Unit tests):
  localvibecode verify
        """,
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Target repository path (defaults to target_repo_path in localvibecode.json)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override Ollama base model name (e.g. qwen2.5-coder:7b, qwen2.5:7b, gemma4:latest)",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress ASCII banner",
    )

    subparsers = parser.add_subparsers(dest="command")

    # 1. `doctor`
    subparsers.add_parser("doctor", help="Run preflight diagnostic checks (Python, RAM, Ollama, Models)")

    # 2. `init <path>`
    init_parser = subparsers.add_parser(
        "init",
        help="Onboard an existing project into localVibeCode (creates configs for OpenCode & VS Code)",
    )
    init_parser.add_argument("project_path", type=str, help="Path to project to onboard")

    # 3. `pev "<req>"`
    pev_parser = subparsers.add_parser(
        "pev",
        help="Run end-to-end Plan -> Execute -> Verify pipeline using 1 Local Base Model",
    )
    pev_parser.add_argument("requirement", type=str, help="Feature or refactoring requirement")

    # 4. `graph`
    subparsers.add_parser(
        "graph",
        help="Build Graphify AST Knowledge Graph (0 LLM tokens) and display God Nodes",
    )

    # 5. `slice <target_file>`
    slice_parser = subparsers.add_parser(
        "slice",
        help="Extract <4K token 1-hop Blast-Radius Surgical Context for a specific file",
    )
    slice_parser.add_argument("target_file", type=str, help="Relative path inside target repo")

    # 6. `verify`
    subparsers.add_parser(
        "verify",
        help="Run Zero-Token Verification (AST syntax + SAST security + Unit Tests)",
    )

    # 7. `mcp`
    subparsers.add_parser(
        "mcp",
        help="Launch stdio MCP server for IDE agents (OpenCode, VS Code, Cursor, Claude Code)",
    )

    # 8. `benchmark`
    bench_parser = subparsers.add_parser(
        "benchmark",
        help="Run automated enterprise acceptance benchmark suite (5 isolated use cases)",
    )
    bench_parser.add_argument(
        "--case",
        type=int,
        default=None,
        help="Run specific benchmark case ID (1 to 5, defaults to all)",
    )

    args = parser.parse_args()

    if not args.no_banner and args.command != "mcp":
        print(BANNER)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    factory_root = Path(__file__).resolve().parents[2]
    repo_hint = Path(args.repo).resolve() if getattr(args, "repo", None) else Path.cwd()
    config = LocalVibeCodeConfig.load(repo_hint if (repo_hint / "localvibecode.json").exists() else Path.cwd())
    if args.model:
        config.primary_model = args.model

    # Command: doctor
    if args.command == "doctor":
        doc = PreflightDoctor(config.ollama_base_url)
        report = doc.run_diagnostics()
        doc.print_report(report)
        sys.exit(0 if report.all_critical_passed else 1)

    # Command: init
    if args.command == "init":
        target_proj = Path(args.project_path).expanduser().resolve()
        if not target_proj.exists():
            error(f"Target directory does not exist: {target_proj}")
            sys.exit(1)
        _onboard_project(factory_root, target_proj, config)
        return

    # Command: mcp
    if args.command == "mcp":
        from localvibecode.mcp_server import LocalVibeCodeStdioMCPServer

        server = LocalVibeCodeStdioMCPServer()
        server.serve_forever()
        return

    # Command: benchmark
    if args.command == "benchmark":
        from localvibecode.benchmark.runner import BenchmarkRunner

        doc = PreflightDoctor(config.ollama_base_url)
        active_model = args.model or config.primary_model
        if not doc.ensure_model_ready(active_model):
            error(f"Cannot execute benchmark suite without model '{active_model}'. Aborting.")
            sys.exit(1)

        runner = BenchmarkRunner(config, workspace_root=factory_root)
        results = runner.run_suite(case_id=args.case)
        all_passed = all(r.passed for r in results) if results else False
        sys.exit(0 if all_passed else 1)

    repo_path = config.resolve_repo_path(args.repo)

    # Command: graph
    if args.command == "graph":
        info(f"Scanning codebase with Graphify AST: {repo_path}")
        builder = DeterministicGraphBuilder(repo_path, config.graph_output_dir)
        graph = builder.build()
        print()
        rule("ARCHITECTURAL GOD NODES & SKELETON")
        print(builder.render_markdown_report(graph))
        rule()
        success(f"Artifacts saved in: {repo_path / config.graph_output_dir}")
        return

    # Command: slice
    if args.command == "slice":
        builder = DeterministicGraphBuilder(repo_path, config.graph_output_dir)
        graph = builder.build()
        slicer = BlastRadiusSlicer(repo_path, graph, max_chars=config.max_surgical_context_chars)
        sl = slicer.slice_for_file(args.target_file)
        rule(f"SURGICAL CONTEXT SLICE (~{sl.approx_tokens} TOKENS)")
        print(f"{Colors.BOLD}Target File    :{Colors.RESET} {sl.target_file}")
        print(f"{Colors.BOLD}1-Hop Outbound :{Colors.RESET} {sl.outbound_files}")
        print(f"{Colors.BOLD}1-Hop Inbound  :{Colors.RESET} {sl.inbound_files}\n")
        print(sl.rendered_context)
        rule()
        return

    # Command: verify
    if args.command == "verify":
        info(f"Running Zero-Token Verification on: {repo_path}")
        verifier = ZeroTokenVerifier(repo_path, config.test_command)
        res = verifier.verify_workspace()
        rule("VERIFICATION REPORT")
        print(f"  {badge('PASS' if res.syntax_ok else 'FAIL', Colors.GREEN if res.syntax_ok else Colors.RED)} Syntax AST Check")
        print(f"  {badge('PASS' if res.security_ok else 'FAIL', Colors.GREEN if res.security_ok else Colors.RED)} Offline SAST Security Check")
        print(f"  {badge('PASS' if res.tests_ok else 'FAIL', Colors.GREEN if res.tests_ok else Colors.RED)} Automated Unit Test Suite")
        if res.error_summary:
            print(f"\n{Colors.RED}{Colors.BOLD}Error Trace:{Colors.RESET}\n{res.error_summary}")
        if res.test_output:
            print(f"\n{Colors.GRAY}{res.test_output}{Colors.RESET}")
        rule()
        if res.passed:
            success("Workspace verification passed (0 errors)!")
        else:
            error("Workspace verification failed!")
        sys.exit(0 if res.passed else 1)

    # Command: pev
    if args.command == "pev":
        # Run fast preflight check before calling local model
        doc = PreflightDoctor(config.ollama_base_url)
        active_model = args.model or config.primary_model
        if not doc.ensure_model_ready(active_model):
            error(f"Cannot execute PEV loop without model '{active_model}'. Aborting.")
            sys.exit(1)

        info(f"Target Repository : {Colors.BOLD}{repo_path}{Colors.RESET}")
        info(f"Pinned Local Model: {Colors.BOLD}{active_model}{Colors.RESET}")
        info(f"User Requirement  : {Colors.CYAN}\"{args.requirement}\"{Colors.RESET}")

        def log_progress(msg: str) -> None:
            if "Phase 0" in msg:
                step("0 (CPU, 0-Token)", "Graphify AST Codebase Indexing")
                info("Parsing AST structures, God Nodes, and dependencies...")
            elif "Phase 1: PLAN" in msg:
                step("1 (PLAN)", f"Generating Minimal Atomic Execution Plan with {active_model}")
            elif "Phase 2: EXECUTE" in msg:
                print(f"\n  {Colors.CYAN}{Colors.BOLD}•{Colors.RESET} {msg}")
            elif "Phase 3A" in msg:
                step("3A (VERIFY)", "Zero-Token AST, Security SAST, and Test Suite Validation")
            elif "Phase 3B" in msg:
                step("3B (CRITIC)", f"LLM Spec Critic evaluating Unified Diff with {active_model}")
            elif "Self-Healing" in msg:
                warning(msg)
            else:
                info(msg)

        pev = DeterministicPEVStateMachine(config, repo_path=repo_path, progress_callback=log_progress)
        report = pev.run(args.requirement)

        rule("PEV PIPELINE SUMMARY")
        verdict = report.critic_verdict.get("verdict", "UNKNOWN")
        score = report.critic_verdict.get("compliance_score", 0)
        status_color = Colors.GREEN if report.success else Colors.RED

        print(f"  Status        : {badge('SUCCESS' if report.success else 'FAILED', status_color)}")
        print(f"  Base Model    : {Colors.BOLD}{report.model_used}{Colors.RESET} (Pinned in VRAM)")
        print(f"  Token Overhead: {report.total_prompt_tokens} prompt / {report.total_completion_tokens} completion (Across fresh contexts)")
        print(f"  Architecture  : {report.plan_data.get('architectural_summary')}")
        print(f"  QA Scorecard  : {verdict} ({score}/100 points)")

        if report.task_records:
            rule("SURGICAL DIFFS APPLIED")
            for rec in report.task_records:
                print(f"{Colors.BOLD}File: {rec.target_file}{Colors.RESET} (Context: ~{rec.surgical_context_tokens} tokens, Attempts: {rec.attempts}, Verified: {rec.verified})")
                if rec.diff_text.strip():
                    for dline in rec.diff_text.splitlines():
                        if dline.startswith("+"):
                            print(f"{Colors.GREEN}{dline}{Colors.RESET}")
                        elif dline.startswith("-"):
                            print(f"{Colors.RED}{dline}{Colors.RESET}")
                        elif dline.startswith("@@"):
                            print(f"{Colors.CYAN}{dline}{Colors.RESET}")
                        else:
                            print(f"{Colors.GRAY}{dline}{Colors.RESET}")
                else:
                    print(f"  {Colors.GRAY}(No changes needed){Colors.RESET}")
                print()

        rule()
        if report.success:
            success("Feature successfully implemented, tested, and verified 100% offline!")
            sys.exit(0)
        else:
            error("Pipeline did not pass all verification checks. See logs above.")
            sys.exit(1)


def _onboard_project(factory_root: Path, target_proj: Path, base_config: LocalVibeCodeConfig) -> None:
    src_dir = (factory_root / "src").as_posix()

    rule("ONBOARDING PROJECT TO LOCALVIBECODE")
    info(f"Target Directory: {target_proj}")

    # Detect test command
    if (target_proj / "pom.xml").exists():
        test_cmd = ["mvn", "test"]
    elif (target_proj / "package.json").exists():
        test_cmd = ["npm", "test", "--", "--watchAll=false"]
    elif (target_proj / "pytest.ini").exists() or (target_proj / "pyproject.toml").exists():
        test_cmd = ["python3", "-m", "unittest", "discover"]
    elif (target_proj / "go.mod").exists():
        test_cmd = ["go", "test", "./..."]
    else:
        test_cmd = base_config.test_command

    # 1. Config file
    proj_cfg = {
        "ollama_base_url": base_config.ollama_base_url,
        "primary_model": base_config.primary_model,
        "fallback_model": base_config.fallback_model,
        "keep_alive": "-1m",
        "num_ctx": 8192,
        "temperature_plan": 0.1,
        "temperature_execute": 0.0,
        "temperature_verify": 0.1,
        "max_surgical_context_chars": 14000,
        "max_self_healing_retries": 3,
        "target_repo_path": ".",
        "graph_output_dir": "graphify-out",
        "enterprise_rules_dir": "enterprise_rules",
        "test_command": test_cmd,
    }
    (target_proj / "localvibecode.json").write_text(json.dumps(proj_cfg, indent=2) + "\n", encoding="utf-8")
    info("Created `localvibecode.json` configuration.")

    # 2. OpenCode config
    opencode_cfg = {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Ollama (Local Pinned Base Model)",
                "options": {"baseURL": "http://localhost:11434/v1"},
                "models": {
                    base_config.primary_model: {"name": f"Primary ({base_config.primary_model})"},
                    base_config.fallback_model: {"name": f"Fallback ({base_config.fallback_model})"},
                },
            }
        },
        "model": f"ollama/{base_config.primary_model}",
        "mcp": {
            "localvibecode": {
                "type": "local",
                "command": ["python3", "-m", "localvibecode.mcp_server"],
                "environment": {"PYTHONPATH": src_dir},
                "enabled": True,
            }
        },
        "command": {
            "pev": {
                "description": "Run offline Enterprise Local Vibe Coding (Graphify AST + PEV)",
                "template": "Call MCP tool `localvibecode_pev_run` with requirement: $ARGUMENTS",
            },
            "impact": {
                "description": "Analyze Blast-Radius 1-hop context (< 4K tokens) for a file",
                "template": "Call MCP tool `localvibecode_blast_radius` for file: $ARGUMENTS",
            },
            "graph": {
                "description": "Scan project AST and display architectural God Nodes",
                "template": "Call MCP tool `localvibecode_build_graph` and display GRAPH_REPORT.md",
            },
        },
    }
    (target_proj / "opencode.json").write_text(json.dumps(opencode_cfg, indent=2) + "\n", encoding="utf-8")
    info("Created `opencode.json` with `/pev`, `/impact`, and `/graph` commands.")

    # 3. VS Code MCP config
    vscode_dir = target_proj / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    vscode_mcp = {
        "servers": {
            "localvibecode": {
                "type": "stdio",
                "command": "python3",
                "args": ["-m", "localvibecode.mcp_server"],
                "env": {"PYTHONPATH": src_dir},
            }
        }
    }
    (vscode_dir / "mcp.json").write_text(json.dumps(vscode_mcp, indent=2) + "\n", encoding="utf-8")
    info("Created `.vscode/mcp.json` for VS Code MCP integration.")

    # 4. Enterprise rules
    rules_dst = target_proj / "enterprise_rules"
    if not rules_dst.exists():
        rules_dst.mkdir(parents=True, exist_ok=True)
        src_rules = factory_root / "enterprise_rules"
        if src_rules.exists():
            for md in src_rules.glob("*.md"):
                (rules_dst / md.name).write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
        info("Created `enterprise_rules/` folder with starter Clean Architecture guardrails.")

    # 5. Build initial Graphify AST
    builder = DeterministicGraphBuilder(target_proj, "graphify-out")
    graph = builder.build()
    info(f"Built initial Graphify AST Map: {len(graph.file_imports)} files indexed.")

    rule()
    success("Project successfully onboarded to localVibeCode!")
    print("\nNext steps:")
    print(f"  • OpenCode : Run `cd {target_proj} && opencode` -> use `/pev <req>` or `/graph`")
    print(f"  • VS Code  : Open folder in VS Code -> MCP server `localvibecode` is active")
    print(f"  • CLI      : Run `localvibecode --repo {target_proj} pev \"<req>\"`\n")


if __name__ == "__main__":
    main()
