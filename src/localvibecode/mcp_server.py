"""Standard MCP (Model Context Protocol) Server over stdio for localVibeCode.

Exposes deterministic AST tools to any MCP-compatible IDE/Agent (OpenCode, VS Code,
Cursor, Roo Code, Continue, Claude Code):
1. `localvibecode_build_graph` (alias `aisdlc_build_graph`): AST Knowledge Graph & God Nodes (0 tokens).
2. `localvibecode_blast_radius` (alias `aisdlc_blast_radius`): Surgical 1-hop context (< 4K tokens).
3. `localvibecode_verify` (alias `aisdlc_verify`): Zero-Token syntax, SAST, and test verifier.
4. `localvibecode_pev_run` (alias `aisdlc_pev_run`): Full PEV loop on 1 local pinned model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

from localvibecode.config import LocalVibeCodeConfig
from localvibecode.context.graph_builder import DeterministicGraphBuilder
from localvibecode.context.slicer import BlastRadiusSlicer
from localvibecode.pev.state_machine import DeterministicPEVStateMachine
from localvibecode.verifier.runner import ZeroTokenVerifier

TOOLS_MANIFEST = [
    {
        "name": "localvibecode_build_graph",
        "description": (
            "Build/refresh the deterministic AST Code Knowledge Graph (Graphify) with 0 LLM tokens. "
            "Returns Architectural God Nodes, import/call dependencies, and public signatures."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Optional relative or absolute path to target repository.",
                }
            },
        },
    },
    {
        "name": "localvibecode_blast_radius",
        "description": (
            "Extract the Surgical Context (< 4,000 tokens) for a target file: "
            "includes target code, 1-hop outbound signatures (bodies stripped), and 1-hop inbound callers."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_file": {
                    "type": "string",
                    "description": "Relative file path inside repository (e.g. 'services/order_service.py').",
                },
                "repo_path": {"type": "string"},
            },
            "required": ["target_file"],
        },
    },
    {
        "name": "localvibecode_verify",
        "description": (
            "Run Zero-Token Deterministic Verification (AST syntax check, Enterprise Security SAST, and Unit Tests)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
            },
        },
    },
    {
        "name": "localvibecode_pev_run",
        "description": (
            "Execute an Enterprise Local Vibe Coding task using the Deterministic PEV "
            "(Plan -> Execute -> Verify) pipeline with Fresh Context isolation on 1 Local Ollama Model."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "requirement": {
                    "type": "string",
                    "description": "Natural language requirement or feature specification.",
                },
                "repo_path": {"type": "string"},
            },
            "required": ["requirement"],
        },
    },
    # Backward compatibility aliases
    {
        "name": "aisdlc_pev_run",
        "description": "Legacy alias for localvibecode_pev_run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "requirement": {"type": "string"},
                "repo_path": {"type": "string"},
            },
            "required": ["requirement"],
        },
    },
    {
        "name": "aisdlc_blast_radius",
        "description": "Legacy alias for localvibecode_blast_radius.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_file": {"type": "string"},
                "repo_path": {"type": "string"},
            },
            "required": ["target_file"],
        },
    },
    {
        "name": "aisdlc_build_graph",
        "description": "Legacy alias for localvibecode_build_graph.",
        "inputSchema": {
            "type": "object",
            "properties": {"repo_path": {"type": "string"}},
        },
    },
    {
        "name": "aisdlc_verify",
        "description": "Legacy alias for localvibecode_verify.",
        "inputSchema": {
            "type": "object",
            "properties": {"repo_path": {"type": "string"}},
        },
    },
]


class LocalVibeCodeStdioMCPServer:
    """Zero-dependency JSON-RPC 2.0 MCP Server communicating over stdin/stdout."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.config = LocalVibeCodeConfig.load(workspace_root)

    def handle_request(self, msg: Dict[str, Any]) -> Dict[str, Any] | None:
        method = msg.get("method", "")
        req_id = msg.get("id")
        params = msg.get("params") or {}

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "localvibecode", "version": "0.2.0"},
                },
            }

        if method.startswith("notifications/"):
            return None

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS_MANIFEST},
            }

        if method == "tools/call":
            tool_name = params.get("name", "")
            args = params.get("arguments") or {}
            try:
                text_result = self._dispatch_tool(tool_name, args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text_result}],
                        "isError": False,
                    },
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error executing {tool_name}: {exc}"}],
                        "isError": True,
                    },
                }

        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        return None

    def _dispatch_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        repo_path = self.config.resolve_repo_path(args.get("repo_path"))

        if tool_name in ("localvibecode_build_graph", "aisdlc_build_graph"):
            builder = DeterministicGraphBuilder(repo_path, self.config.graph_output_dir)
            graph = builder.build()
            return builder.render_markdown_report(graph)

        if tool_name in ("localvibecode_blast_radius", "aisdlc_blast_radius"):
            target_file = args["target_file"]
            builder = DeterministicGraphBuilder(repo_path, self.config.graph_output_dir)
            graph = builder.build()
            slicer = BlastRadiusSlicer(
                repo_path, graph, max_chars=self.config.max_surgical_context_chars
            )
            sl = slicer.slice_for_file(target_file)
            header = (
                f"# Blast-Radius Surgical Slice for `{sl.target_file}`\n"
                f"- **Estimated Context Size:** ~`{sl.approx_tokens}` tokens\n"
                f"- **1-Hop Outbound Imports:** `{sl.outbound_files}`\n"
                f"- **1-Hop Inbound Callers (Impact Zone):** `{sl.inbound_files}`\n\n"
            )
            return header + sl.rendered_context

        if tool_name in ("localvibecode_verify", "aisdlc_verify"):
            verifier = ZeroTokenVerifier(repo_path, self.config.test_command)
            res = verifier.verify_workspace()
            return json.dumps(
                {
                    "passed": res.passed,
                    "syntax_ok": res.syntax_ok,
                    "security_ok": res.security_ok,
                    "tests_ok": res.tests_ok,
                    "error_summary": res.error_summary,
                    "test_output": res.test_output,
                },
                indent=2,
            )

        if tool_name in ("localvibecode_pev_run", "aisdlc_pev_run"):
            requirement = args["requirement"]
            pev = DeterministicPEVStateMachine(self.config, repo_path=repo_path)
            report = pev.run(requirement)
            summary = [
                f"# localVibeCode Execution Report (Success: `{report.success}`)",
                f"- **Single Base Model:** `{report.model_used}`",
                f"- **Total Tokens (Across Fresh Contexts):** `{report.total_prompt_tokens}` prompt / `{report.total_completion_tokens}` completion",
                f"- **Architectural Summary:** {report.plan_data.get('architectural_summary', '')}",
                "\n## Atomic Tasks Executed:",
            ]
            for rec in report.task_records:
                summary.append(
                    f"- **Step {rec.step_id} (`{rec.target_file}`):** "
                    f"Context `~{rec.surgical_context_tokens}` tokens | Attempts: `{rec.attempts}` | Verified: `{rec.verified}`\n"
                    f"```diff\n{rec.diff_text}\n```"
                )
            if report.test_verification:
                summary.append(
                    f"\n## Zero-Token Test Suite Result: `{'PASS' if report.test_verification.passed else 'FAIL'}`\n"
                    f"```text\n{report.test_verification.test_output or report.test_verification.error_summary}\n```"
                )
            summary.append(
                f"\n## QA Critic Verdict: `{report.critic_verdict.get('verdict')}` "
                f"(Compliance: `{report.critic_verdict.get('compliance_score')}/100`)\n"
                f"{report.critic_verdict.get('review_notes', '')}"
            )
            return "\n".join(summary)

        raise ValueError(f"Unknown tool: {tool_name}")

    def serve_forever(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            resp = self.handle_request(msg)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()


def main() -> None:
    server = LocalVibeCodeStdioMCPServer()
    server.serve_forever()


if __name__ == "__main__":
    main()
