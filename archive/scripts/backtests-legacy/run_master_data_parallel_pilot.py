#!/usr/bin/env python3
"""
Load ``data/input/master_data/halal_tickers_clean.json``, run one halal-sector-month
pilot per **sector** in parallel (subprocesses), then merge ``master_pilot.json`` files
into a single dashboard-ready document.

Inputs (Phoenix + fundamentals) use **only** data on or before ``--signal-date`` (see
``agents/orchestrator/backtest_phoenix._run_period``). ``--eval-days`` is **only** the forward
calendar window for **outcome labeling** (target hit / exit reference), not for model features.

Example (staging dir outside ``trading_runs``, one merged file for the dashboard)::

    set -a && source .env && set +a
    python scripts/backtests/run_master_data_parallel_pilot.py \\
        --signal-date 2025-04-27 --eval-days 30 \\
        --output-root data/output/_staging_unified_master_2025-04-27 \\
        --merged-output data/output/trading_runs/unified_master_2025-04-27/master_pilot.json \\
        --cleanup-staging
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent
PILOT = ROOT / "scripts" / "backtests" / "run_halal_sector_month_pilot.py"
DEFAULT_MASTER = ROOT / "data" / "input" / "master_data" / "halal_tickers_clean.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.io.master_pilot import confusion_from_master_tickers


def _slug(sector: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", sector.strip()).strip("-").lower()
    return s or "unknown"


def _load_groups(path: Path) -> Dict[str, List[str]]:
    rows = json.loads(path.read_text())
    by: Dict[str, List[str]] = {}
    for r in rows:
        t = str(r.get("ticker", "")).strip().upper()
        sec = str(r.get("sector", "Unknown")).strip()
        if not t:
            continue
        by.setdefault(sec, []).append(t)
    for k in list(by.keys()):
        by[k] = sorted(set(by[k]))
    return by


def _run_one_sector(args: Tuple[str, List[str], Path, str, int, int, int]) -> Path:
    sector, tickers, out_dir, signal_date, workers, period_workers, eval_days = args
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(PILOT),
        "--tickers",
        ",".join(tickers),
        "--signal-date",
        signal_date,
        "--eval-days",
        str(max(1, int(eval_days))),
        "--single-master-json",
        "--workers",
        str(max(1, workers)),
        "--period-workers",
        str(max(1, period_workers)),
        "--output-dir",
        str(out_dir),
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"Pilot failed sector={sector!r} dir={out_dir}\n"
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )
    mp = out_dir / "master_pilot.json"
    if not mp.is_file():
        raise FileNotFoundError(f"Missing master_pilot.json under {out_dir}")
    return out_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--master-json",
        type=Path,
        default=DEFAULT_MASTER,
        help="Ticker + sector list (default: halal_tickers_clean.json)",
    )
    ap.add_argument("--signal-date", required=True, metavar="YYYY-MM-DD")
    ap.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data/output/trading_runs/master_pilot_master_data_parallel",
        help="Per-sector subdirs + merged master_pilot.json here",
    )
    ap.add_argument(
        "--sector-jobs",
        type=int,
        default=8,
        help="Max parallel sector subprocesses",
    )
    ap.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Thread workers per sector pilot (--workers)",
    )
    ap.add_argument(
        "--period-workers",
        type=int,
        default=2,
        help="Per-ticker period workers (--period-workers)",
    )
    ap.add_argument(
        "--skip-pilot",
        action="store_true",
        help="Only merge existing per-sector master_pilot.json under output-root",
    )
    ap.add_argument(
        "--eval-days",
        type=int,
        default=30,
        metavar="N",
        help="Forward calendar days after signal_date for outcome labeling (passed to pilot).",
    )
    ap.add_argument(
        "--merged-output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "If set, write the merged master_pilot.json here instead of OUTPUT_ROOT/master_pilot.json "
            "(use with a staging --output-root outside trading_runs, then --cleanup-staging)."
        ),
    )
    ap.add_argument(
        "--cleanup-staging",
        action="store_true",
        help="After a successful merge, delete the entire --output-root tree (staging).",
    )
    args = ap.parse_args()

    master_json = args.master_json.expanduser().resolve()
    groups = _load_groups(master_json)
    if not groups:
        raise SystemExit(f"No tickers in {master_json}")

    root: Path = args.output_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    if not args.skip_pilot:
        tasks: List[Tuple[str, List[str], Path, str, int, int, int]] = []
        for sector, tickers in sorted(groups.items(), key=lambda x: x[0]):
            od = root / _slug(sector)
            tasks.append(
                (
                    sector,
                    tickers,
                    od,
                    args.signal_date,
                    args.workers,
                    args.period_workers,
                    args.eval_days,
                )
            )

        nj = max(1, min(int(args.sector_jobs), len(tasks)))
        print(f"Running {len(tasks)} sector pilots with up to {nj} parallel jobs …", flush=True)
        with ThreadPoolExecutor(max_workers=nj) as ex:
            futs = {ex.submit(_run_one_sector, t): t[0] for t in tasks}
            for fut in as_completed(futs):
                sec = futs[fut]
                fut.result()
                print(f"  done: {sec}", flush=True)

    merged: Dict[str, Any] = {}
    per_manifests: List[Dict[str, Any]] = []
    total_elapsed = 0.0

    for sector in sorted(groups.keys()):
        mp = root / _slug(sector) / "master_pilot.json"
        if not mp.is_file():
            raise FileNotFoundError(f"Expected {mp}")
        doc = json.loads(mp.read_text())
        per_manifests.append(doc.get("manifest") or {})
        total_elapsed += float(doc.get("elapsed_sec") or 0)
        for sym, row in (doc.get("tickers") or {}).items():
            merged[str(sym).upper()] = row

    cm = confusion_from_master_tickers(merged)
    run_id = f"halal_pilot_{args.signal_date}_master_data_{uuid.uuid4().hex[:10]}"
    final_path = (
        args.merged_output.expanduser().resolve()
        if args.merged_output
        else (root / "master_pilot.json")
    )
    final_path.parent.mkdir(parents=True, exist_ok=True)
    out_doc: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "manifest": {
            "no_lookahead_statement": (
                "Phoenix and Fundamental analyze_ticker calls use as_of_date equal to signal_date only. "
                "OHLCV and fundamentals are restricted to data on or before that date. "
                "Prices after signal_date are used only for outcome labeling (target hit, exit reference close), "
                "never as inputs to the screening models."
            ),
            "signal_date": args.signal_date,
            "eval_days": int(args.eval_days),
            "universe_source": str(master_json.relative_to(ROOT)),
            "sectors": sorted(groups.keys()),
            "tickers_total": len(merged),
            "parallel_sector_runs": True,
            "output_root": str(final_path.parent.relative_to(ROOT)),
            "merged_artifact": final_path.name,
            "per_sector_manifests": per_manifests,
        },
        "confusion_matrix": {
            "meta": {
                "description": "Merged fusion directional vs target-hit (all sectors from master data list).",
                "elapsed_sec_sector_sum": round(total_elapsed, 2),
                "tickers": len(merged),
                "primary_artifact": "master_pilot.json",
            },
            "cumulative": {"overall": cm},
        },
        "tickers": merged,
        "elapsed_sec": round(total_elapsed, 2),
    }

    final_path.write_text(json.dumps(out_doc, indent=2, default=str), encoding="utf-8")
    if args.merged_output and (root / "master_pilot.json").is_file():
        try:
            (root / "master_pilot.json").unlink()
        except OSError:
            pass
    if args.cleanup_staging and not args.skip_pilot:
        import shutil

        shutil.rmtree(root, ignore_errors=False)
    print()
    print("=" * 72)
    print(f"Merged master_pilot.json → {final_path}")
    print(f"Tickers: {len(merged)} | Confusion overall: {cm}")
    print("=" * 72)


if __name__ == "__main__":
    main()
