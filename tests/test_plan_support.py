"""Tests for the Round 01 planning / self-healing helpers."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from localvibecode.context.graph_builder import DeterministicGraphBuilder
from localvibecode.pev.plan_support import (
    consolidate_plan,
    files_in_failure_output,
    files_mentioned,
    focused_context,
    mentions_failure,
    normalize_path,
)
from localvibecode.pev.state_machine import DeterministicPEVStateMachine

ROOT = Path(__file__).resolve().parents[1]
JAVA_FIXTURE = ROOT / "benchmarks" / "fixtures" / "java_shop"
PRODUCT = "src/main/java/com/ecommerce/model/Product.java"
SERVICE = "src/main/java/com/ecommerce/service/OrderService.java"


class NormalizeAndConsolidateTest(unittest.TestCase):
    def test_normalize_keeps_dot_directories(self) -> None:
        self.assertEqual(normalize_path("./.github/ci.yml"), ".github/ci.yml")
        self.assertEqual(normalize_path("`src/a.py`"), "src/a.py")

    def test_normalize_rejects_escapes(self) -> None:
        self.assertIsNone(normalize_path("../etc/passwd"))
        self.assertIsNone(normalize_path("a/../../x"))
        self.assertIsNone(normalize_path("/abs/path"))

    def test_consolidate_merges_steps_for_the_same_file(self) -> None:
        tasks = [
            {"step_id": 1, "target_file": "tests/test_a.py", "instruction": "test one", "verification_criteria": "x"},
            {"step_id": 2, "target_file": "./tests/test_a.py", "instruction": "test two", "verification_criteria": ""},
            {"step_id": 3, "target_file": "../evil.py", "instruction": "nope", "verification_criteria": ""},
            {"step_id": 4, "target_file": "src/b.py", "instruction": "impl", "verification_criteria": ""},
        ]
        steps, dropped = consolidate_plan(tasks, Path("."))
        self.assertEqual([s["target_file"] for s in steps], ["tests/test_a.py", "src/b.py"])
        self.assertEqual([s["step_id"] for s in steps], [1, 2])
        self.assertIn("test one", steps[0]["instruction"])
        self.assertIn("test two", steps[0]["instruction"])
        self.assertEqual(dropped, ["../evil.py"])

    def test_mentions_failure(self) -> None:
        self.assertTrue(mentions_failure("CI is failing: expected 8 but was 2"))
        self.assertFalse(mentions_failure("Add a search endpoint"))


class GraphFocusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="lvc-plan-"))
        cls.repo = cls.tmp / "repo"
        shutil.copytree(JAVA_FIXTURE, cls.repo)
        cls.graph = DeterministicGraphBuilder(cls.repo).build()

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_files_mentioned_by_type_name(self) -> None:
        found = files_mentioned("Bug in `CheckoutRequest.addItem` used by OrderService", self.graph)
        self.assertIn("src/main/java/com/ecommerce/dto/CheckoutRequest.java", found)
        self.assertIn(SERVICE, found)

    def test_failure_output_points_at_frames_and_compile_errors(self) -> None:
        out = (
            f"[ERROR] {self.repo.resolve()}/{PRODUCT}:[12,5] cannot find symbol\n"
            "\tat com.ecommerce.service.OrderService.createOrder(OrderService.java:48)\n"
        )
        self.assertEqual(files_in_failure_output(out, self.graph, self.repo), [PRODUCT, SERVICE])

    def test_focused_context_is_bounded_and_includes_neighbours(self) -> None:
        text, files = focused_context("Fix OrderService totals", self.graph, max_chars=8000)
        self.assertLessEqual(len(text), 8000)
        self.assertEqual(files[0], SERVICE)
        self.assertIn(PRODUCT, files)  # 1-hop dependency of OrderService


class OutputBudgetTest(unittest.TestCase):
    def test_budget_grows_with_file_size_and_is_capped(self) -> None:
        self.assertEqual(DeterministicPEVStateMachine._output_budget(""), 1536)
        self.assertGreater(DeterministicPEVStateMachine._output_budget("x" * 12000), 4000)
        self.assertEqual(DeterministicPEVStateMachine._output_budget("x" * 100000), 8192)


if __name__ == "__main__":
    unittest.main()
