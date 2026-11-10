"""Characterisation tests for the harness core (A14).

Tests marked `expectedFailure` pin known defects found in the Round 00 review; they should start
passing (and the marker be removed) when the corresponding action is implemented.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from localvibecode.bench.report import wilson
from localvibecode.bench.tasks import apply_edits
from localvibecode.context.graph_builder import DeterministicGraphBuilder
from localvibecode.context.slicer import BlastRadiusSlicer
from localvibecode.pev.patcher import SurgicalPatcher
from localvibecode.verifier.runner import ZeroTokenVerifier

ROOT = Path(__file__).resolve().parents[1]
PY_FIXTURE = ROOT / "benchmarks" / "fixtures" / "py_orders"
JAVA_FIXTURE = ROOT / "benchmarks" / "fixtures" / "java_shop"


class TempDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="lvc-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def copy_fixture(self, fixture: Path) -> Path:
        dest = self.tmp / fixture.name
        shutil.copytree(fixture, dest)
        return dest


class SurgicalPatcherTest(TempDirCase):
    def test_json_updated_code_replaces_file(self) -> None:
        target = self.tmp / "a.py"
        target.write_text("x = 1\n")
        out = SurgicalPatcher.apply_llm_output(target, json.dumps({"reasoning": "r", "updated_code": "x = 2"}))
        self.assertTrue(out.applied)
        self.assertEqual(out.mode, "json_constrained")
        self.assertEqual(target.read_text(), "x = 2\n")

    def test_search_replace_block(self) -> None:
        target = self.tmp / "a.py"
        target.write_text("a = 1\nb = 2\n")
        text = "<<<<<<< SEARCH\nb = 2\n=======\nb = 3\n>>>>>>> REPLACE"
        out = SurgicalPatcher.apply_llm_output(target, text)
        self.assertEqual(out.mode, "search_replace")
        self.assertEqual(target.read_text(), "a = 1\nb = 3\n")

    def test_unparseable_output_is_rejected(self) -> None:
        target = self.tmp / "a.py"
        target.write_text("a = 1\n")
        out = SurgicalPatcher.apply_llm_output(target, "I cannot do that.")
        self.assertFalse(out.applied)
        self.assertEqual(target.read_text(), "a = 1\n")


class ZeroTokenVerifierTest(TempDirCase):
    def check(self, name: str, source: str, previous: str = ""):
        (self.tmp / name).write_text(source)
        return ZeroTokenVerifier(self.tmp).verify_file_syntax_and_security(name, previous_source=previous)

    def test_python_syntax_error(self) -> None:
        self.assertFalse(self.check("a.py", "def f(:\n  pass\n").syntax_ok)

    def test_removed_symbol_is_blocked(self) -> None:
        res = self.check("a.py", "def f():\n    return 1\n", previous="def f():\n    return 1\n\ndef g():\n    return 2\n")
        self.assertFalse(res.passed)
        self.assertIn("g", res.error_summary)

    def test_eval_is_blocked(self) -> None:
        self.assertFalse(self.check("a.py", "def f(x):\n    return eval(x)\n").security_ok)

    @unittest.expectedFailure  # A9: substring matching flags ast.literal_eval (false positive)
    def test_literal_eval_is_allowed(self) -> None:
        self.assertTrue(self.check("a.py", "import ast\n\ndef f(x):\n    return ast.literal_eval(x)\n").security_ok)

    @unittest.expectedFailure  # A3: Java "syntax check" only counts braces
    def test_non_compiling_java_is_rejected(self) -> None:
        src = "public class A {\n  public int f() {\n    return undefinedSymbol + ;\n  }\n}\n"
        self.assertFalse(self.check("A.java", src).passed)


class GraphAndSlicerTest(TempDirCase):
    def test_python_import_edges(self) -> None:
        repo = self.copy_fixture(PY_FIXTURE)
        graph = DeterministicGraphBuilder(repo).build()
        self.assertEqual(
            sorted(graph.file_imports["services/order_service.py"]),
            ["gateways/payment_gateway.py", "models.py", "validators.py"],
        )
        self.assertIn("services/order_service.py", graph.inbound_files["models.py"])

    def test_slice_contains_target_and_neighbours(self) -> None:
        repo = self.copy_fixture(PY_FIXTURE)
        graph = DeterministicGraphBuilder(repo).build()
        sl = BlastRadiusSlicer(repo, graph).slice_for_file("services/order_service.py")
        self.assertIn("class OrderService", sl.rendered_context)
        self.assertIn("validators.py", sl.outbound_files)

    @unittest.expectedFailure  # A5: the target file itself can be cut by the character cap
    def test_target_file_is_never_truncated(self) -> None:
        repo = self.copy_fixture(PY_FIXTURE)
        graph = DeterministicGraphBuilder(repo).build()
        target = (repo / "services/order_service.py").read_text()
        sl = BlastRadiusSlicer(repo, graph, max_chars=400).slice_for_file("services/order_service.py")
        self.assertIn(target.strip(), sl.rendered_context)

    @unittest.expectedFailure  # A5: Java targets are presented to the model in a ```python fence
    def test_java_target_uses_java_fence(self) -> None:
        repo = self.copy_fixture(JAVA_FIXTURE)
        graph = DeterministicGraphBuilder(repo).build()
        rel = "src/main/java/com/ecommerce/model/Product.java"
        sl = BlastRadiusSlicer(repo, graph).slice_for_file(rel)
        self.assertIn("```java", sl.rendered_context)


class BenchUtilitiesTest(TempDirCase):
    def test_apply_edits_requires_unique_match(self) -> None:
        (self.tmp / "f.txt").write_text("a a")
        with self.assertRaises(ValueError):
            apply_edits(self.tmp, [{"file": "f.txt", "find": "a", "replace": "b"}])

    def test_wilson_interval(self) -> None:
        low, high = wilson(5, 10)
        self.assertLess(low, 0.5)
        self.assertGreater(high, 0.5)
        self.assertEqual(wilson(0, 0), [None, None])


if __name__ == "__main__":
    unittest.main()
