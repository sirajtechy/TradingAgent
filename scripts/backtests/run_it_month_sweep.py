#!/usr/bin/env python3
"""
Parallel IT sector backtest sweep — two signal dates per month (month-start + mid-month).

Uses the same engine as ``./bin/mts sector --full-sector`` (technical-only, phoenix_recall).
Signal inputs are point-in-time at each ``--signal-date``; forward prices are outcome-only.

Example::

    set -a && source .env && set +a
    python scripts/backtests/run_it_month_sweep.py --parallel-dates 3
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_env = ROOT / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

from core.io.master_pilot import slug_sector
from core.paths import sector_run_dir
from pipelines.backtest import run_sector_pilot

SECTOR = "Information Technology"
FULL_SECTOR_TICKERS = 200  # skip re-run when manifest shows >= this count


def _weekday_or_next(d: date) -> date:
    """First trading day on or after *d* (weekends only; no holiday calendar)."""
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _mid_month_trading_day(year: int, month: int) -> date:
    d = date(year, month, 15)
    return _weekday_or_next(d)


def _month_start_trading_day(year: int, month: int) -> date:
    d = date(year, month, 1)
    # Jan 1 is often a market holiday — bump to next weekday if needed.
    if month == 1 and d.weekday() < 5:
        # Prefer Jan 2 when Jan 1 is a weekday (NYSE closed New Year's Day).
        return date(year, 1, 2) if d.weekday() == 3 else _weekday_or_next(d)  # Thu Jan 1 → Fri Jan 2
    return _weekday_or_next(d)


def signal_dates_apr2025_feb2026() -> List[str]:
    out: List[str] = []
    y, m = 2025, 4
    while (y, m) <= (2026, 2):
        for fn in (_month_start_trading_day, _mid_month_trading_day):
            out.append(fn(y, m).isoformat())
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return out


def _run_complete(signal_date: str) -> bool:
    master = sector_run_dir(slug_sector(SECTOR), signal_date) / "master_pilot.json"
    if not master.is_file():
        return False
    try:
        doc = json.loads(master.read_text(encoding="utf-8"))
        n = int((doc.get("manifest") or {}).get("tickers_requested") or 0)
        return n >= FULL_SECTOR_TICKERS
    except Exception:
        return False


def _run_one(args: Tuple[str, int, int, int, str]) -> Dict[str, Any]:
    signal_date, eval_days, workers, period_workers, profile = args
    t0 = time.time()
    if _run_complete(signal_date):
        return {
            "signal_date": signal_date,
            "status": "skipped",
            "elapsed_s": 0.0,
        }
    rc = run_sector_pilot(
        sector=SECTOR,
        signal_date=signal_date,
        eval_days=eval_days,
        workers=workers,
        period_workers=period_workers,
        backtest_signal_profile=profile,
        full_sector=True,
    )
    return {
        "signal_date": signal_date,
        "status": "ok" if rc == 0 else "failed",
        "returncode": rc,
        "elapsed_s": round(time.time() - t0, 1),
    }


def _month_key(signal_date: str) -> str:
    d = date.fromisoformat(signal_date)
    return f"{d.year}-{d.month:02d}"


def _summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_month: Dict[str, List[Dict[str, Any]]] = {}
    for sd in signal_dates_apr2025_feb2026():
        master = sector_run_dir(slug_sector(SECTOR), sd) / "master_pilot.json"
        if not master.is_file():
            continue
        doc = json.loads(master.read_text(encoding="utf-8"))
        px = (doc.get("confusion_matrix") or {}).get("cumulative", {}).get("by_agent", {}).get(
            "phoenix", {}
        )
        row = {
            "signal_date": sd,
            "tickers": int((doc.get("manifest") or {}).get("tickers_requested") or 0),
            "phoenix_tp": px.get("TP"),
            "phoenix_fp": px.get("FP"),
            "phoenix_precision_pct": px.get("precision_pct"),
            "phoenix_recall_pct": px.get("recall_pct"),
            "phoenix_f1_pct": px.get("f1_pct"),
        }
        by_month.setdefault(_month_key(sd), []).append(row)

    monthly_medians: Dict[str, Any] = {}
    for mk, rows in sorted(by_month.items()):
        if not rows:
            continue
        def med(key: str) -> Optional[float]:
            vals = [r[key] for r in rows if r.get(key) is not None]
            return round(statistics.median(vals), 2) if vals else None

        monthly_medians[mk] = {
            "runs": len(rows),
            "signal_dates": [r["signal_date"] for r in rows],
            "median_phoenix_tp": med("phoenix_tp"),
            "median_phoenix_fp": med("phoenix_fp"),
            "median_phoenix_precision_pct": med("phoenix_precision_pct"),
            "median_phoenix_recall_pct": med("phoenix_recall_pct"),
            "median_phoenix_f1_pct": med("phoenix_f1_pct"),
        }

    return {"by_month": by_month, "monthly_medians": monthly_medians}


def main() -> int:
    parser = argparse.ArgumentParser(description="IT sector month sweep (Apr 2025 – Feb 2026)")
    parser.add_argument("--eval-days", type=int, default=15)
    parser.add_argument("--workers", type=int, default=6, help="Per-date ticker parallelism")
    parser.add_argument("--period-workers", type=int, default=2)
    parser.add_argument(
        "--parallel-dates",
        type=int,
        default=3,
        help="How many signal dates to run concurrently",
    )
    parser.add_argument(
        "--backtest-signal-profile",
        default="phoenix_recall",
        choices=["enrichment_strict", "phoenix_watch_bull", "phoenix_recall", "phoenix_buy_only"],
    )
    parser.add_argument(
        "--summary-out",
        default=str(
            ROOT
            / "data"
            / "output"
            / "trading_runs"
            / "it_sweep_apr2025_feb2026_summary.json"
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dates = signal_dates_apr2025_feb2026()
    pending = [d for d in dates if not _run_complete(d)]
    print(f"Signal dates ({len(dates)}): {', '.join(dates)}", flush=True)
    print(f"Complete (skip): {len(dates) - len(pending)} | Pending: {len(pending)}", flush=True)

    if args.dry_run:
        for d in pending:
            print(f"  would run {d}", flush=True)
        return 0

    job_args = [
        (sd, int(args.eval_days), int(args.workers), int(args.period_workers), args.backtest_signal_profile)
        for sd in pending
    ]
    results: List[Dict[str, Any]] = []
    if not job_args:
        print("All dates already complete.", flush=True)
    else:
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=max(1, int(args.parallel_dates))) as pool:
            futs = {pool.submit(_run_one, ja): ja[0] for ja in job_args}
            for fut in as_completed(futs):
                sd = futs[fut]
                try:
                    row = fut.result()
                except Exception as exc:
                    row = {"signal_date": sd, "status": "error", "error": str(exc)}
                results.append(row)
                print(json.dumps(row), flush=True)
        print(f"Sweep elapsed {time.time() - t0:.0f}s", flush=True)

    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sector": SECTOR,
        "eval_days": int(args.eval_days),
        "backtest_signal_profile": args.backtest_signal_profile,
        "signal_dates": dates,
        "run_results": results,
        **_summarize(results),
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Summary → {summary_path}", flush=True)

    sync = subprocess.call([sys.executable, "-m", "cli", "backtest", "sync"], cwd=str(ROOT))
    return 0 if sync == 0 and all(r.get("status") in ("ok", "skipped") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
