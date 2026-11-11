"""Sets a module-scoped, agent-visible `test_cmd` on mined multi-module tasks.

Running the whole Apollo suite takes ~3 min; agents only need the tests of the modules they touch.
Usage: python3 benchmarks/tools/scope_task_tests.py <repo> <task-id-prefix>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]


def module_test_packages(repo: Path, module: str) -> list:
    root = repo / module / "src" / "test" / "java"
    pkgs = set()
    for f in root.rglob("*Test.java"):
        parts = f.relative_to(root).parent.parts
        pkgs.add(".".join(parts[:5]))  # e.g. com.ctrip.framework.apollo.biz
    return sorted(pkgs)


def main() -> None:
    repo, prefix = Path(sys.argv[1]).resolve(), sys.argv[2]
    for task_json in sorted((BENCH / "tasks").glob(f"{prefix}-*/task.json")):
        task = json.loads(task_json.read_text(encoding="utf-8"))
        mods = task["test_modules"]
        patterns = sorted({p + ".**" for m in mods for p in module_test_packages(repo, m)})
        task["test_cmd"] = ["mvn", "-o", "-q", "test", "-pl", ",".join(mods), "-am", "-Dspotless.check.skip=true",
                            "-Dsurefire.failIfNoSpecifiedTests=false", "-Dtest=" + ",".join(patterns)]
        task_json.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(task["id"], " ".join(task["test_cmd"][4:]))


if __name__ == "__main__":
    main()
