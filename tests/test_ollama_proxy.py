"""Tests for the tool-call repair proxy (local-ai/ollama_proxy.py)."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "ollama_proxy", Path(__file__).resolve().parents[1] / "local-ai" / "ollama_proxy.py")
proxy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(proxy)  # type: ignore[union-attr]


class RepairStringTest(unittest.TestCase):
    def test_fully_escaped_code(self) -> None:
        fixed, changed = proxy.repair_string("def a():\\n    return 1\\n")
        self.assertTrue(changed)
        self.assertEqual(fixed, "def a():\n    return 1\n")

    def test_mixed_real_and_literal_newlines(self) -> None:
        fixed, _ = proxy.repair_string("def sub(a, b):\n    return a - b\\ndef add(a, b):\n    return a + b")
        self.assertEqual(fixed, "def sub(a, b):\n    return a - b\ndef add(a, b):\n    return a + b")

    def test_escape_inside_string_literal_is_kept(self) -> None:
        src = 'System.out.println("a\\nb");\nint x = 1;'
        self.assertEqual(proxy.repair_string(src), (src, False))
        fixed, _ = proxy.repair_string('log("x\\ny");\\nreturn;')
        self.assertEqual(fixed, 'log("x\\ny");\nreturn;')

    def test_single_quotes(self) -> None:
        fixed, _ = proxy.repair_string("s = 'a\\tb'\\nprint(s)")
        self.assertEqual(fixed, "s = 'a\\tb'\nprint(s)")

    def test_plain_code_untouched(self) -> None:
        self.assertEqual(proxy.repair_string("x = 1\ny = 2\n"), ("x = 1\ny = 2\n", False))


class RepairArgumentsTest(unittest.TestCase):
    def test_only_code_arguments_are_repaired(self) -> None:
        args = json.dumps({"filePath": "a\\nb.py", "oldString": "a\\nb", "description": "x\\ny"})
        fixed, n = proxy.repair_arguments(args)
        data = json.loads(fixed)
        self.assertEqual(n, 1)
        self.assertEqual(data["oldString"], "a\nb")
        self.assertEqual(data["filePath"], "a\\nb.py")
        self.assertEqual(data["description"], "x\\ny")

    def test_invalid_json_passthrough(self) -> None:
        self.assertEqual(proxy.repair_arguments("{not json"), ("{not json", 0))


class AnchorEditTest(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self.dir = tempfile.mkdtemp()
        self.path = str(Path(self.dir) / "A.java")
        Path(self.path).write_text(
            "class A {\n    void f() {\n        int x = 1;\n        int y = 2;\n    }\n\n    void g() {\n        int x = 1;\n    }\n}\n")

    def edit(self, old: str, new: str):
        data = {"filePath": self.path, "oldString": old, "newString": new}
        return proxy.anchor_edit(data), data

    def test_exact_match_untouched(self) -> None:
        self.assertFalse(self.edit("        int y = 2;", "        int y = 3;")[0])

    def test_indentation_drift_is_anchored_and_reindented(self) -> None:
        ok, data = self.edit("    int x = 1;\n    int y = 2;", "    int x = 1;\n    int y = 3;")
        self.assertTrue(ok)
        self.assertEqual(data["oldString"], "        int x = 1;\n        int y = 2;")
        self.assertEqual(data["newString"], "        int x = 1;\n        int y = 3;")

    def test_wrapped_statement_is_anchored(self) -> None:
        Path(self.path).write_text(
            "class A {\n  void f() {\n    service.update(appId, clusterName,\n        branchName, rules);\n  }\n}\n")
        ok, data = self.edit("    service.update(appId, clusterName, branchName, rules);", "    service.update(x);")
        self.assertEqual(data["newString"], "service.update(x);")
        self.assertTrue(ok)
        self.assertEqual(data["oldString"], "service.update(appId, clusterName,\n        branchName, rules);")

    def test_ambiguous_match_is_left_alone(self) -> None:
        self.assertFalse(self.edit("int x = 1;", "int x = 5;")[0])  # appears in f() and g()

    def test_missing_file_or_no_match(self) -> None:
        self.assertFalse(proxy.anchor_edit({"filePath": "/nope", "oldString": "a", "newString": "b"}))
        self.assertFalse(self.edit("int z = 9;", "int z = 0;")[0])


class SseTest(unittest.TestCase):
    def test_tool_calls_are_replayed_with_indices(self) -> None:
        response = {"id": "c1", "model": "m", "choices": [{"message": {"role": "assistant", "tool_calls": [
            {"id": "t1", "type": "function", "function": {"name": "edit", "arguments": "{}"}}]},
            "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": 1, "completion_tokens": 2}}
        chunks = list(proxy.sse_chunks(response))
        self.assertEqual(chunks[0]["choices"][0]["delta"]["tool_calls"][0]["index"], 0)
        self.assertEqual(chunks[-1]["choices"][0]["finish_reason"], "tool_calls")


if __name__ == "__main__":
    unittest.main()
