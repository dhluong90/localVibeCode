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
from typing import Any, Callable, Dict, List, Optional, Tuple

from localvibecode.config import LocalVibeCodeConfig
from localvibecode.context.graph_builder import DeterministicGraphBuilder
from localvibecode.context.slicer import BlastRadiusSlicer
from localvibecode.llm_client import SingleModelOllamaClient
from localvibecode.pev.patcher import SurgicalPatcher
from localvibecode.pev.plan_support import (
    consolidate_plan,
    files_in_failure_output,
    focused_context,
    is_test_path,
    mentions_failure,
    unique,
)
from localvibecode.pev.schemas import PLAN_JSON_SCHEMA, VERIFY_JSON_SCHEMA
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
        self.verifier = ZeroTokenVerifier(self.repo_root, config.test_command, config.test_timeout_sec)
        self.log = progress_callback or (lambda msg: None)

    def run(self, requirement: str) -> PEVPipelineReport:
        enterprise_rules = self.config.load_enterprise_rules()
        active_model = self.llm.get_active_model()

        # --- STEP 0: Deterministic AST scan (0 LLM tokens) ---
        self.log("[Phase 0] Scanning codebase with Graphify Deterministic AST Builder (0 tokens)...")
        graph = self.graph_builder.build()
        large_repo = len(graph.file_imports) > self.config.large_repo_files

        total_in_tokens = 0
        total_out_tokens = 0

        # --- STEP 0B: Reproduce the failure when the requirement reports one (0 tokens) ---
        failure_output = ""
        if mentions_failure(requirement):
            pre_check = self.verifier.verify_workspace()
            if not pre_check.passed:
                failure_output = (pre_check.error_summary or "") + "\n" + (pre_check.test_output or "")[-3000:]
                self.log("[Phase 0B] Existing tests fail; failure output is given to the planner.")

        # --- STEP 1: PLAN on a requirement-focused view of the code graph ---
        focused, focus_files = focused_context(
            requirement, graph, failure_output, self.repo_root, max_chars=self.config.max_plan_context_chars
        )
        self.log(f"[Phase 1: PLAN] Generating atomic execution plan with `{active_model}` "
                 f"({len(focus_files)} focused files)...")
        plan_system = (
            "You are the Lead Enterprise Software Architect in an AISDLC Factory.\n"
            "Break the user requirement down into the MINIMAL set of `atomic_tasks`.\n"
            "CRITICAL PLANNING RULES:\n"
            "1. ONLY include files that genuinely need code changes to satisfy the requirement.\n"
            "2. Exactly ONE atomic task per file: put every change for a file into a single instruction.\n"
            "3. If the requirement describes a failure, fix the ROOT CAUSE: the file where the faulty logic "
            "lives, which may differ from the file where the symptom shows (follow the call path in the code view).\n"
            "4. Use the exact relative paths shown in the code view; only invent a path for a genuinely new file.\n"
            "5. Do not edit existing tests to make them pass. Add or update a test only if the requirement asks for it.\n"
            "6. Order tasks so that dependencies come first (model -> service -> controller -> tests).\n"
            "7. Output strictly valid JSON matching the requested schema."
        )
        plan_user_parts = [
            f"=== ENTERPRISE GUARDRAILS ===\n{enterprise_rules}",
            f"=== RELEVANT CODE (public signatures; files named in the requirement and their 1-hop neighbours) ===\n"
            f"{focused}",
        ]
        if failure_output:
            plan_user_parts.append(f"=== CURRENT TEST FAILURES ===\n{failure_output[-3000:]}")
        plan_user_parts.append(f"=== USER REQUIREMENT ===\n{requirement}")
        plan_data, plan_in, plan_out = self._plan(plan_system, "\n\n".join(plan_user_parts))
        total_in_tokens += plan_in
        total_out_tokens += plan_out

        steps, dropped = consolidate_plan(plan_data.get("atomic_tasks", []), self.repo_root)
        if dropped:
            self.log(f"[Phase 1: PLAN] Dropped unsafe target paths: {dropped}")
        plan_data["atomic_tasks"] = steps
        plan_path = self.repo_root / self.config.graph_output_dir / "last_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")

        report = PEVPipelineReport(requirement=requirement, model_used=active_model, plan_data=plan_data)

        # --- STEP 2: EXECUTE (fresh context per file + file-level self-healing) ---
        for task in steps:
            step_id = int(task["step_id"])
            target_file = task["target_file"]
            instruction = task["instruction"]
            if not large_repo:
                graph = self.graph_builder.build()  # small repos: propagate new signatures immediately
            context_slice = BlastRadiusSlicer(
                self.repo_root, graph, max_chars=self.config.max_surgical_context_chars
            ).slice_for_file(target_file)
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
                    system_prompt=self._coder_system(target_file),
                    user_prompt="\n\n".join(exec_user_parts),
                    temperature=self.config.temperature_execute,
                    num_predict=self._output_budget(before_text),
                )
                total_in_tokens += exec_resp.prompt_tokens
                total_out_tokens += exec_resp.completion_tokens

                outcome = SurgicalPatcher.apply_llm_output(file_path, exec_resp.content)
                patch_mode = outcome.mode
                if not outcome.applied:
                    error_feedback = outcome.message
                    continue
                file_check = self.verifier.verify_file_syntax_and_security(target_file, previous_source=before_text)
                if file_check.passed:
                    verified_file = True
                    break
                self.log(f"  -> [Self-Healing Retry {attempt}] Verification issue in `{target_file}`: "
                         f"{file_check.error_summary}")
                file_path.write_text(before_text, encoding="utf-8")
                error_feedback = file_check.error_summary

            after_text = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
            diff_lines = list(difflib.unified_diff(
                before_text.splitlines(), after_text.splitlines(),
                fromfile=f"a/{target_file}", tofile=f"b/{target_file}", lineterm=""))
            report.task_records.append(TaskExecutionRecord(
                step_id=step_id, target_file=target_file, instruction=instruction, attempts=attempts,
                surgical_context_tokens=context_slice.approx_tokens, patch_mode=patch_mode,
                verified=verified_file, diff_text="\n".join(diff_lines)))

        # --- STEP 3A: Workspace verification + self-healing on the files the failure points at ---
        self.log("[Phase 3A: ZERO-TOKEN VERIFIER] Running AST, Security SAST, and Unit Test Suite...")
        ws_check = self.verifier.verify_workspace()
        for heal_round in range(1, self.config.max_heal_rounds + 1):
            if ws_check.passed or not report.task_records:
                break
            failure_text = (ws_check.error_summary or "") + "\n" + (ws_check.test_output or "")
            pointed = files_in_failure_output(failure_text, graph, self.repo_root)
            touched = [r.target_file for r in report.task_records]
            # Prefer production files the failure points at; fall back to the files we changed.
            targets = [f for f in pointed if not is_test_path(f)] or [f for f in touched if not is_test_path(f)] \
                or touched
            targets = unique(targets)[:2]
            self.log(f"  -> [Test Self-Healing round {heal_round}] Unit tests failed. Targeted fix on {targets}...")
            for heal_target in targets:
                heal_slice = BlastRadiusSlicer(
                    self.repo_root, graph, max_chars=self.config.max_surgical_context_chars
                ).slice_for_file(heal_target)
                heal_path = self.repo_root / heal_target
                heal_before = heal_path.read_text(encoding="utf-8") if heal_path.exists() else ""
                heal_resp = self.llm.generate_fresh(
                    system_prompt=self._coder_system(heal_target, debugging=True),
                    user_prompt=(
                        f"=== REQUIREMENT ===\n{requirement}\n\n"
                        f"=== TEST / COMPILE FAILURE ===\n{failure_text[-4000:]}\n\n"
                        f"{heal_slice.rendered_context}"
                    ),
                    temperature=0.0,
                    num_predict=self._output_budget(heal_before),
                )
                total_in_tokens += heal_resp.prompt_tokens
                total_out_tokens += heal_resp.completion_tokens
                outcome = SurgicalPatcher.apply_llm_output(heal_path, heal_resp.content)
                if outcome.applied and not self.verifier.verify_file_syntax_and_security(
                        heal_target, previous_source=heal_before).passed:
                    heal_path.write_text(heal_before, encoding="utf-8")  # never keep a heal that breaks syntax
            ws_check = self.verifier.verify_workspace()

        report.test_verification = ws_check

        # --- STEP 3B: LLM critic (advisory only; success is decided by the tests) ---
        self.log("[Phase 3B: LLM SPEC CRITIC] Auditing diffs against requirement & Enterprise Rules...")
        combined_diffs = "\n\n".join(r.diff_text for r in report.task_records if r.diff_text.strip())
        critic_system = (
            "You are the Principal QA & Architecture Critic in an Enterprise AISDLC Factory.\n"
            "Evaluate the unified git diff and automated test results against the original requirement.\n"
            "Check every part of the requirement explicitly; return 'REPLAN' if any part is missing or wrong.\n"
            "Return JSON matching the verification schema."
        )
        critic_user = (
            f"=== ORIGINAL REQUIREMENT ===\n{requirement}\n\n"
            f"=== ENTERPRISE GUARDRAILS ===\n{enterprise_rules}\n\n"
            f"=== ZERO-TOKEN TEST SUITE RESULT ===\n"
            f"Passed: {ws_check.passed}\nOutput:\n{(ws_check.test_output or ws_check.error_summary)[-3000:]}\n\n"
            f"=== UNIFIED GIT DIFF ===\n{combined_diffs or '(No changes)'}\n"
        )
        try:
            critic_resp = self.llm.generate_fresh(
                system_prompt=critic_system, user_prompt=critic_user,
                temperature=self.config.temperature_verify, json_schema=VERIFY_JSON_SCHEMA)
            total_in_tokens += critic_resp.prompt_tokens
            total_out_tokens += critic_resp.completion_tokens
            report.critic_verdict = json.loads(critic_resp.content)
        except (ValueError, RuntimeError) as exc:
            report.critic_verdict = {"verdict": "UNAVAILABLE", "compliance_score": 0, "review_notes": str(exc)}
        report.total_prompt_tokens = total_in_tokens
        report.total_completion_tokens = total_out_tokens
        report.success = bool(ws_check.passed)

        if not large_repo:
            self.graph_builder.build()  # refresh Graphify artifacts after changes
        return report

    # ------------------------------------------------------------------------- helpers

    def _plan(self, system: str, user: str) -> Tuple[Dict[str, Any], int, int]:
        """Plans with constrained JSON; retries once at temperature 0 if the JSON does not parse."""
        tokens_in = tokens_out = 0
        last_error: Optional[Exception] = None
        for temperature in (self.config.temperature_plan, 0.0):
            resp = self.llm.generate_fresh(system_prompt=system, user_prompt=user, temperature=temperature,
                                           json_schema=PLAN_JSON_SCHEMA)
            tokens_in += resp.prompt_tokens
            tokens_out += resp.completion_tokens
            try:
                data = json.loads(resp.content)
                if isinstance(data, dict):
                    return data, tokens_in, tokens_out
            except ValueError as exc:
                last_error = exc
        raise ValueError(f"Planner did not return valid JSON: {last_error}")

    @staticmethod
    def _coder_system(target_file: str, debugging: bool = False) -> str:
        lang = {".java": "java", ".py": "python", ".ts": "typescript", ".tsx": "tsx", ".js": "javascript",
                ".jsx": "jsx", ".go": "go"}.get(Path(target_file).suffix, "")
        role = ("You are an Expert Surgical Debugger. Fix the target file so that the failing tests pass.\n"
                if debugging else "You are an Expert Surgical Coder in an Enterprise AISDLC Factory.\n")
        return (
            role
            + f"You are editing ONLY the file `{target_file}`.\n"
            "RULES:\n"
            f"1. Keep ALL existing imports, classes, methods and tests in `{target_file}` that the task does not change.\n"
            "2. Apply ONLY the requested change.\n"
            "3. Respect the 1-hop outbound signatures and DO NOT break the 1-hop inbound callers.\n"
            f"4. Respond with the COMPLETE updated content of `{target_file}` in ONE ```{lang} code block, "
            "and nothing else."
        )

    @staticmethod
    def _output_budget(current_source: str) -> int:
        """Output tokens for a full-file answer: ~1.3x the current file plus headroom (1536 truncated big files)."""
        estimated = int(len(current_source) / 3.2 * 1.3) + 768
        return max(1536, min(8192, estimated))
