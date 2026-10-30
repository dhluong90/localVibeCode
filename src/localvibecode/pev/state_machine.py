"""Deterministic PEV (Plan - Execute - Verify) State Machine.

Coordinates the Single Local Base Model across 3 strictly isolated context windows:
- Phase 0 (CPU, 0 Token): Build Graphify AST Knowledge Graph & Structural Skeleton.
- Phase 1 (PLAN - Fresh Context #1): Constrained JSON Schema generation of Atomic Tasks.
- Phase 2 (EXECUTE - Fresh Context #2 per file): Blast-Radius Surgical Context (< 4K tokens)
  + Constrained JSON Code Patching + Zero-Token AST/Contract/Security/Test Verification
  with Self-Healing Retry.
- Phase 3 (VERIFY - Fresh Context #3): QA Critic evaluates unified git/file diffs against
  the original requirement and Enterprise Guardrails.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from localvibecode.config import LocalVibeCodeConfig
from localvibecode.context.graph_builder import DeterministicGraphBuilder
from localvibecode.context.slicer import BlastRadiusSlicer
from localvibecode.llm_client import SingleModelOllamaClient
from localvibecode.pev.patcher import SurgicalPatcher
from localvibecode.pev.schemas import EXECUTE_JSON_SCHEMA, PLAN_JSON_SCHEMA, VERIFY_JSON_SCHEMA
from localvibecode.verifier.runner import VerificationResult, ZeroTokenVerifier


@dataclass
class TaskExecutionRecord:
    step_id: int
    target_file: str
    instruction: str
    attempts: int
    surgical_context_tokens: int
    patch_mode: str
    verified: bool
    diff_text: str


@dataclass
class PEVPipelineReport:
    requirement: str
    model_used: str
    plan_data: Dict[str, Any]
    task_records: List[TaskExecutionRecord] = field(default_factory=list)
    test_verification: Optional[VerificationResult] = None
    critic_verdict: Dict[str, Any] = field(default_factory=dict)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    success: bool = False


class DeterministicPEVStateMachine:
    """Runs the Plan -> Execute -> Verify workflow with Fresh Context per step."""

    def __init__(
        self,
        config: LocalVibeCodeConfig,
        repo_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.config = config
        self.repo_root = config.resolve_repo_path(repo_path)
        self.llm = SingleModelOllamaClient(config)
        self.graph_builder = DeterministicGraphBuilder(self.repo_root, config.graph_output_dir)
        self.verifier = ZeroTokenVerifier(self.repo_root, config.test_command)
        self.log = progress_callback or (lambda msg: None)

    def run(self, requirement: str) -> PEVPipelineReport:
        enterprise_rules = self.config.load_enterprise_rules()
        active_model = self.llm.get_active_model()

        # --- STEP 0: Deterministic Graphify AST Scan (0 LLM Tokens) ---
        self.log("[Phase 0] Scanning codebase with Graphify Deterministic AST Builder (0 tokens)...")
        graph = self.graph_builder.build()
        graph_report = self.graph_builder.render_markdown_report(graph)

        total_in_tokens = 0
        total_out_tokens = 0

        # --- STEP 1: PLAN (Fresh Context #1 + Constrained JSON Schema) ---
        self.log(f"[Phase 1: PLAN] Generating atomic execution plan with `{active_model}`...")
        plan_system = (
            "You are the Lead Enterprise Software Architect in an AISDLC Factory.\n"
            "Analyze the Repository Knowledge Graph (GRAPH_REPORT.md) and Enterprise Guardrails.\n"
            "Break the user requirement down into the MINIMAL set of `atomic_tasks`.\n"
            "CRITICAL PLANNING RULES:\n"
            "1. ONLY include files that genuinely need code changes to satisfy the requirement. "
            "Do NOT modify `models.py` or `validators.py` unless the user explicitly asks to change them.\n"
            "2. Order tasks logically: business service file first -> unit test file last.\n"
            "3. Each atomic_task MUST target a single relative file path from the repository.\n"
            "4. Output strictly valid JSON matching the requested schema."
        )
        plan_user = (
            f"=== ENTERPRISE GUARDRAILS ===\n{enterprise_rules}\n\n"
            f"=== REPOSITORY KNOWLEDGE GRAPH (GRAPH_REPORT.md) ===\n{graph_report}\n\n"
            f"=== USER REQUIREMENT ===\n{requirement}\n"
        )
        plan_resp = self.llm.generate_fresh(
            system_prompt=plan_system,
            user_prompt=plan_user,
            temperature=self.config.temperature_plan,
            json_schema=PLAN_JSON_SCHEMA,
        )
        total_in_tokens += plan_resp.prompt_tokens
        total_out_tokens += plan_resp.completion_tokens

        plan_data = json.loads(plan_resp.content)
        plan_path = self.repo_root / self.config.graph_output_dir / "last_plan.json"
        plan_path.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")

        report = PEVPipelineReport(
            requirement=requirement,
            model_used=active_model,
            plan_data=plan_data,
        )

        # --- STEP 2: EXECUTE (Fresh Context #2 per Atomic Task + Self-Healing Loop) ---
        atomic_tasks = plan_data.get("atomic_tasks", [])
        for task in atomic_tasks:
            step_id = int(task["step_id"])
            target_file = task["target_file"].strip().lstrip("./")
            instruction = task["instruction"]

            # Rebuild AST graph before each file so newly added signatures propagate immediately
            graph = self.graph_builder.build()
            slicer = BlastRadiusSlicer(
                self.repo_root, graph, max_chars=self.config.max_surgical_context_chars
            )
            context_slice = slicer.slice_for_file(target_file)

            self.log(
                f"[Phase 2: EXECUTE Step #{step_id}] File `{target_file}` "
                f"(Surgical Context: ~{context_slice.approx_tokens} tokens, "
                f"Inbound Callers: {len(context_slice.inbound_files)}, Outbound Deps: {len(context_slice.outbound_files)})"
            )

            file_path = self.repo_root / target_file
            before_text = file_path.read_text(encoding="utf-8") if file_path.exists() else ""

            error_feedback = ""
            verified_file = False
            patch_mode = "failed"
            attempts = 0

            for attempt in range(1, self.config.max_self_healing_retries + 1):
                attempts = attempt
                exec_system = (
                    "You are an Expert Surgical Coder in an Enterprise AISDLC Factory.\n"
                    f"You are editing ONLY the file `{target_file}`.\n"
                    "RULES:\n"
                    "1. Keep ALL existing imports, classes, methods, and unit tests in `{target_file}` intact.\n"
                    "2. Apply ONLY the requested change in `Instruction`.\n"
                    "3. Respect all 1-Hop Outbound Signatures and DO NOT break 1-Hop Inbound Callers.\n"
                    "4. Output strictly JSON with `reasoning` and `updated_code` containing the full Python source code for `{target_file}`."
                )
                exec_user_parts = [
                    f"=== ENTERPRISE GUARDRAILS ===\n{enterprise_rules}",
                    f"=== OVERALL REQUIREMENT ===\n{requirement}",
                    f"=== CURRENT ATOMIC TASK (Step #{step_id} on `{target_file}`) ===\n"
                    f"Instruction: {instruction}\n"
                    f"Verification Criteria: {task.get('verification_criteria', '')}",
                    context_slice.rendered_context,
                ]
                if error_feedback:
                    exec_user_parts.append(
                        f"=== PREVIOUS ATTEMPT FAILED VERIFICATION (FIX THIS IMMEDIATELY) ===\n{error_feedback}"
                    )

                exec_resp = self.llm.generate_fresh(
                    system_prompt=exec_system,
                    user_prompt="\n\n".join(exec_user_parts),
                    temperature=self.config.temperature_execute,
                    json_schema=EXECUTE_JSON_SCHEMA,
                )
                total_in_tokens += exec_resp.prompt_tokens
                total_out_tokens += exec_resp.completion_tokens

                outcome = SurgicalPatcher.apply_llm_output(file_path, exec_resp.content)
                patch_mode = outcome.mode
                if not outcome.applied:
                    error_feedback = outcome.message
                    continue

                # Immediate Zero-Token Syntax, Symbol Preservation & Security Check on the modified file
                file_check = self.verifier.verify_file_syntax_and_security(
                    target_file, previous_source=before_text
                )
                if file_check.passed:
                    verified_file = True
                    break
                else:
                    self.log(
                        f"  -> [Self-Healing Retry {attempt}] Verification issue in `{target_file}`: "
                        f"{file_check.error_summary}"
                    )
                    file_path.write_text(before_text, encoding="utf-8")
                    error_feedback = file_check.error_summary

            after_text = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
            diff_lines = list(
                difflib.unified_diff(
                    before_text.splitlines(),
                    after_text.splitlines(),
                    fromfile=f"a/{target_file}",
                    tofile=f"b/{target_file}",
                    lineterm="",
                )
            )
            report.task_records.append(
                TaskExecutionRecord(
                    step_id=step_id,
                    target_file=target_file,
                    instruction=instruction,
                    attempts=attempts,
                    surgical_context_tokens=context_slice.approx_tokens,
                    patch_mode=patch_mode,
                    verified=verified_file,
                    diff_text="\n".join(diff_lines),
                )
            )

        # --- STEP 2B: Workspace-wide Unit Test Verification + Test Self-Healing ---
        self.log("[Phase 3A: ZERO-TOKEN VERIFIER] Running AST, Security SAST, and Unit Test Suite...")
        ws_check = self.verifier.verify_workspace()
        if not ws_check.passed and report.task_records:
            last_record = report.task_records[-1]
            self.log(
                f"  -> [Test Self-Healing] Unit tests failed. Triggering targeted fix on `{last_record.target_file}`..."
            )
            graph = self.graph_builder.build()
            slicer = BlastRadiusSlicer(
                self.repo_root, graph, max_chars=self.config.max_surgical_context_chars
            )
            heal_slice = slicer.slice_for_file(last_record.target_file)
            heal_resp = self.llm.generate_fresh(
                system_prompt=(
                    "You are an Expert Surgical Debugger. Fix the target file so that all unit tests pass.\n"
                    "Preserve all existing classes and test methods. Output JSON with `reasoning` and `updated_code`."
                ),
                user_prompt=(
                    f"=== REQUIREMENT ===\n{requirement}\n\n"
                    f"=== UNIT TEST FAILURE TRACEBACK ===\n{ws_check.error_summary}\n\n"
                    f"{heal_slice.rendered_context}"
                ),
                temperature=0.0,
                json_schema=EXECUTE_JSON_SCHEMA,
            )
            total_in_tokens += heal_resp.prompt_tokens
            total_out_tokens += heal_resp.completion_tokens
            target_fp = self.repo_root / last_record.target_file
            SurgicalPatcher.apply_llm_output(target_fp, heal_resp.content)
            ws_check = self.verifier.verify_workspace()

        report.test_verification = ws_check

        # --- STEP 3: VERIFY (Fresh Context #3 — LLM QA Critic) ---
        self.log("[Phase 3B: LLM SPEC CRITIC] Auditing diffs against requirement & Enterprise Rules...")
        combined_diffs = "\n\n".join(
            r.diff_text for r in report.task_records if r.diff_text.strip()
        )
        critic_system = (
            "You are the Principal QA & Architecture Critic in an Enterprise AISDLC Factory.\n"
            "Evaluate the unified git diff and automated test results against the original requirement.\n"
            "If the unit test suite PASSED and the requested feature is implemented in the diff, return verdict 'PASS'.\n"
            "Return JSON matching the verification schema."
        )
        critic_user = (
            f"=== ORIGINAL REQUIREMENT ===\n{requirement}\n\n"
            f"=== ENTERPRISE GUARDRAILS ===\n{enterprise_rules}\n\n"
            f"=== ZERO-TOKEN TEST SUITE RESULT ===\n"
            f"Passed: {ws_check.passed}\nOutput:\n{ws_check.test_output or ws_check.error_summary}\n\n"
            f"=== UNIFIED GIT DIFF ===\n{combined_diffs or '(No changes)'}\n"
        )
        critic_resp = self.llm.generate_fresh(
            system_prompt=critic_system,
            user_prompt=critic_user,
            temperature=self.config.temperature_verify,
            json_schema=VERIFY_JSON_SCHEMA,
        )
        total_in_tokens += critic_resp.prompt_tokens
        total_out_tokens += critic_resp.completion_tokens

        report.critic_verdict = json.loads(critic_resp.content)
        report.total_prompt_tokens = total_in_tokens
        report.total_completion_tokens = total_out_tokens
        report.success = bool(
            ws_check.passed and report.critic_verdict.get("verdict") == "PASS"
        )

        # Refresh Graphify artifacts after changes
        self.graph_builder.build()
        return report
