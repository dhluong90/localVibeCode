"""CLI: python -m localvibecode.bench {validate,run,run-one,sast,report}"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from localvibecode.bench.runner import CONFIGS, BenchContext, find_task, run_matrix, run_one, validate_tasks
from localvibecode.bench.tasks import load_tasks


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m localvibecode.bench")
    parser.add_argument("--project-root", default=".", help="localVibeCode repository root")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--round", required=True, help="e.g. benchmarks/rounds/round_00")
        p.add_argument("--tasks", default="", help="comma-separated task ids (default: all)")
        p.add_argument("--split", default="dev")

    p_val = sub.add_parser("validate", help="check every task: fails at base, reference resolves it")
    add_common(p_val)

    p_run = sub.add_parser("run", help="run the model x k x task x config matrix (resumable)")
    add_common(p_run)
    p_run.add_argument("--models", required=True)
    p_run.add_argument("--configs", default=",".join(CONFIGS))
    p_run.add_argument("--k", type=int, default=5)

    p_one = sub.add_parser("run-one")
    p_one.add_argument("--round", required=True)
    p_one.add_argument("--task", required=True)
    p_one.add_argument("--config", required=True, choices=CONFIGS)
    p_one.add_argument("--model", required=True)
    p_one.add_argument("--k", type=int, required=True)
    p_one.add_argument("--keep-ws", action="store_true")

    p_sast = sub.add_parser("sast", help="Q2 deterministic SAST suite")
    p_sast.add_argument("--round", required=True)

    p_reg = sub.add_parser("regrade", help="re-grade finished runs from their saved diffs")
    p_reg.add_argument("--round", required=True)
    p_reg.add_argument("--task-prefix", default="", help="only tasks whose id starts with this")
    p_reg.add_argument("--before", type=float, default=None, help="only results written before this epoch")

    p_rep = sub.add_parser("report", help="write summary.json and print Markdown tables")
    p_rep.add_argument("--round", required=True)
    p_rep.add_argument("--k", type=int, default=5)

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    ctx = BenchContext(project_root, Path(args.round))
    ids = [t for t in getattr(args, "tasks", "").split(",") if t] or None

    if args.cmd == "validate":
        def show(r) -> None:
            flag = "OK  " if r["valid"] else "FAIL"
            extra = f" mutation={r['reference_mutation_score']}" if "reference_mutation_score" in r else ""
            print(f"{flag} {r['task']}: base_resolved={r['base_resolved']} ref_resolved={r['reference_resolved']} "
                  f"ref_regression={r['reference_regression']} p2p={len(r['pass_to_pass'])}{extra}", flush=True)
            if not r["valid"]:
                print("     " + r.get("detail", "").replace("\n", "\n     ")[-1200:], flush=True)

        rows = validate_tasks(ctx, load_tasks(ctx.bench_root, ids=ids, split=args.split), log=show)
        sys.exit(0 if all(r["valid"] for r in rows) else 1)

    if args.cmd == "run":
        tasks = load_tasks(ctx.bench_root, ids=ids, split=args.split)
        run_matrix(ctx, tasks, args.models.split(","), args.configs.split(","), args.k,
                   log=lambda m: print(m, flush=True))
        return

    if args.cmd == "run-one":
        task = find_task(ctx, args.task)
        if task is None:
            sys.exit(f"unknown task {args.task}")
        result = run_one(ctx, task, args.config, args.model, args.k, keep_ws=args.keep_ws)
        print(json.dumps({k: result[k] for k in ("task", "config", "resolved", "primary_tag", "agent_sec")}))
        return

    if args.cmd == "sast":
        from localvibecode.bench.sast import run_sast_suite

        res = run_sast_suite(ctx.bench_root)
        ctx.round_dir.mkdir(parents=True, exist_ok=True)
        (ctx.round_dir / "sast.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        for c in res["cases"]:
            print(f"{'VULN' if c['vulnerable'] else 'SAFE'} flagged={c['flagged']!s:5} {c['file']}  ({c['note']})")
        print(f"recall={res['recall']} fp_rate={res['fp_rate']}")
        return

    if args.cmd == "regrade":
        from localvibecode.bench.runner import regrade_run

        files = sorted(ctx.round_dir.glob("runs/*/*/*/k*/result.json"))
        files = [f for f in files if f.parent.parent.name.startswith(args.task_prefix)
                 and (args.before is None or f.stat().st_mtime < args.before)]
        changed = 0
        for i, f in enumerate(files, 1):
            r = regrade_run(ctx, f)
            same = (r["before"], r["regression_before"]) == (r["after"], r["regression_after"])
            changed += not same
            print(f"[{i}/{len(files)}] {'same' if same else 'CHANGED'} {r['model']} {r['config']} {r['task']} "
                  f"k{r['k']}: resolved {r['before']}->{r['after']} "
                  f"regression {r['regression_before']}->{r['regression_after']}", flush=True)
        print(f"regraded {len(files)} runs, {changed} changed")
        return

    if args.cmd == "report":
        from localvibecode.bench.report import build_summary, render_markdown

        sast_file = ctx.round_dir / "sast.json"
        sast = json.loads(sast_file.read_text()) if sast_file.exists() else None
        if sast:
            sast = {k: v for k, v in sast.items() if k != "cases"}
        summary = build_summary(ctx.round_dir, ctx.bench_root / "tasks", args.k, sast)
        (ctx.round_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(render_markdown(summary))


if __name__ == "__main__":
    main()
