#!/usr/bin/env python3
"""JSON CLI for backtest registry — used by dashboard API and `./bin/mts backtest sync`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.persistence.backtest_store import get_default_store  # noqa: E402
from core.persistence.ingest import scan_and_ingest_trading_runs  # noqa: E402


def _emit(doc: Dict[str, Any]) -> None:
    print(json.dumps(doc, default=str))


def cmd_sync(_: argparse.Namespace) -> int:
    store = get_default_store()
    result = scan_and_ingest_trading_runs(store=store)
    _emit(
        {
            "ok": True,
            "db_path": str(store.db_path.relative_to(ROOT)),
            **result,
        }
    )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    store = get_default_store()
    runs = store.list_runs(limit=int(args.limit))
    _emit({"ok": True, "db_path": str(store.db_path.relative_to(ROOT)), "runs": runs})
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    store = get_default_store()
    run_key = args.run_key
    doc = store.get_run(run_key)
    if not doc:
        _emit({"ok": False, "error": f"Run not found: {run_key}"})
        return 1
    _emit({"ok": True, "run": doc})
    return 0


def cmd_timeline(_: argparse.Namespace) -> int:
    store = get_default_store()
    timeline = store.timeline_summary()
    _emit({"ok": True, "timeline": timeline})
    return 0


def cmd_agents_heatmap(args: argparse.Namespace) -> int:
    """Aggregate by_agent metrics across all runs for heatmap matrix."""
    store = get_default_store()
    runs = store.list_runs(limit=int(args.limit))
    matrix: Dict[str, Dict[str, Any]] = {}
    for run in runs:
        detail = store.get_run(run["run_key"])
        if not detail:
            continue
        by_agent = (detail.get("confusion_matrix") or {}).get("cumulative", {}).get("by_agent") or {}
        for agent_id, met in by_agent.items():
            if agent_id not in matrix:
                matrix[agent_id] = {"runs": 0, "accuracy_sum": 0.0, "accuracy_count": 0, "latest": None}
            matrix[agent_id]["runs"] += 1
            acc = met.get("accuracy_pct")
            if acc is not None:
                matrix[agent_id]["accuracy_sum"] += float(acc)
                matrix[agent_id]["accuracy_count"] += 1
            matrix[agent_id]["latest"] = {
                "run_key": run["run_key"],
                "signal_date": run["signal_date"],
                "metrics": met,
            }
    for agent_id, agg in matrix.items():
        cnt = agg.pop("accuracy_count", 0)
        agg["avg_accuracy_pct"] = round(agg.pop("accuracy_sum", 0) / cnt, 1) if cnt else None
    _emit({"ok": True, "agents": matrix})
    return 0


def cmd_heatmap(args: argparse.Namespace) -> int:
    store = get_default_store()
    rows = store.confusion_heatmap_data(period=str(args.period), limit=int(args.limit))
    _emit({"ok": True, "period": args.period, "runs": rows})
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Backtest registry JSON CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sync", help="Scan trading_runs and upsert into SQLite")
    s.set_defaults(func=cmd_sync)

    li = sub.add_parser("list", help="List ingested runs")
    li.add_argument("--limit", type=int, default=100)
    li.set_defaults(func=cmd_list)

    g = sub.add_parser("get", help="Get one run by run_key (artifact relative path)")
    g.add_argument("run_key")
    g.set_defaults(func=cmd_get)

    t = sub.add_parser("timeline", help="Per signal_date agent rollup")
    t.set_defaults(func=cmd_timeline)

    h = sub.add_parser("agents-heatmap", help="Cross-run agent accuracy summary")
    h.add_argument("--limit", type=int, default=50)
    h.set_defaults(func=cmd_agents_heatmap)

    hm = sub.add_parser("heatmap", help="Per-run agent confusion rows for dashboard heatmap")
    hm.add_argument(
        "--period",
        default="all",
        choices=["all", "today", "yesterday", "week"],
        help="Filter by ingest day (UTC): today, yesterday, last 7 days, or all",
    )
    hm.add_argument("--limit", type=int, default=50)
    hm.set_defaults(func=cmd_heatmap)

    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
