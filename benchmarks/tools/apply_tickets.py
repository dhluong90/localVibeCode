"""Applies written tickets (prompt, category, oracle plan, human baseline) to mined task.json files.

Usage: python3 benchmarks/tools/apply_tickets.py <tickets.json> [--split-map <id>=<split> ...]
Tasks without a ticket are left untouched (they stay split=draft).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]


def main() -> None:
    tickets = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    persona = tickets.get("_baseline_persona", "")
    splits = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    for task_id, ticket in tickets.items():
        if task_id.startswith("_"):
            continue
        path = BENCH / "tasks" / task_id / "task.json"
        task = json.loads(path.read_text(encoding="utf-8"))
        plan = ticket["plan"]
        missing = [g for g in task["gold_files"] if g not in plan]
        extra = [f for f in plan if f not in task["gold_files"]]
        if extra:
            raise SystemExit(f"{task_id}: plan names files that are not gold files: {extra}")
        task.update({
            "category": ticket["category"],
            "difficulty": ticket["difficulty"],
            "prompt": ticket["prompt"],
            "oracle_plan": [{"file": g, "instruction": plan.get(g, "Apply the changes this file needs for the task.")}
                            for g in task["gold_files"]],
            "human_baseline": {
                "minutes": sum(ticket["baseline"].values()),
                "source": "proxy:claude-mid-dev",
                "breakdown": ticket["baseline"],
                "persona": persona,
            },
        })
        if task_id in splits:
            task["split"] = splits[task_id]
        path.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        note = f" (generic instruction for {len(missing)} gold file(s))" if missing else ""
        print(f"{task_id}: {task['category']}/{task['difficulty']} split={task['split']} "
              f"baseline={task['human_baseline']['minutes']}min{note}")


if __name__ == "__main__":
    main()
