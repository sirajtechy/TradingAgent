#!/usr/bin/env python3
"""
run_multi_timeframe_backtest.py — Run backtests across multiple monthly cutoff dates.

Iterates over every month-start in the trailing 12 months (Apr 2025 – Mar 2026)
using the full halal sector universe, then writes one Excel workbook per cutoff
date and prints a summary comparison table at the end.

The script reuses all logic from run_backtest_excel.py — it simply drives it
programmatically across multiple dates rather than calling it once.

Usage
─────
  python scripts/run_multi_timeframe_backtest.py
  python scripts/run_multi_timeframe_backtest.py --workers 4 --tickers-per-sector 5
  python scripts/run_multi_timeframe_backtest.py --months 6
  python scripts/run_multi_timeframe_backtest.py --sector "Energy" --workers 3
  python scripts/run_multi_timeframe_backtest.py --dates 2025-01-01 2025-07-01 2026-01-01

Parameters
──────────
  --months            How many trailing months to generate (default: 12).
  --dates             Explicit list of YYYY-MM-DD cutoff dates (overrides --months).
  --workers           Thread pool size per run (default: 4).
  --target-days       Max trade window in trading days (default: 20).
  --tickers-per-sector  Max tickers per sector (default: 5 → ~55 tickers, reasonable speed).
  --sector            Optional sector filter (e.g. "Energy").

Output
──────
  data/output/backtests/multi/<run-date>/
      summary.txt       — win-rate / trade-count comparison across all cutoff dates
      <YYYY-MM-DD>/
          <YYYY-MM-DD>.xlsx
          run_log.txt
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── project root on path ─────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Import helpers directly from run_backtest_excel so we don't duplicate logic
from scripts.run_backtest_excel import (
    _predict_one,
    _select_tickers,
    OUTPUT_BASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Date helpers
# ─────────────────────────────────────────────────────────────────────────────

def _last_weekday(d: date) -> date:
    """Roll back to the previous weekday if d falls on a weekend."""
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _trailing_month_starts(n: int) -> List[date]:
    """
    Return the last n month-start dates (1st of each month), rolling back to
    the nearest weekday, ending with the most recent completed month.

    Example (today = 2026-04-25, n=12):
      2025-04-01, 2025-05-01, ..., 2026-03-03 (Mon, since Mar 1 = Sun)
    """
    today = date.today()
    # Start from the 1st of last month and go backwards
    first_of_this_month = today.replace(day=1)
    first_of_last_month = (first_of_this_month - timedelta(days=1)).replace(day=1)

    dates: List[date] = []
    cursor = first_of_last_month
    for _ in range(n):
        dates.append(_last_weekday(cursor))
        # Go back one month
        cursor = (cursor - timedelta(days=1)).replace(day=1)

    return list(reversed(dates))  # oldest → newest


# ─────────────────────────────────────────────────────────────────────────────
# Single cutoff date runner
# ─────────────────────────────────────────────────────────────────────────────

def _run_single_cutoff(
    cutoff: date,
    tickers: List[Tuple[str, str]],
    target_days: int,
    workers: int,
    out_base: Path,
) -> Dict[str, Any]:
    """
    Run predict_trade for all tickers at a single cutoff date.
    Returns a summary dict: {cutoff, total, trades, no_trade, errors, outcomes}.
    """
    cutoff_str = cutoff.isoformat()
    out_dir = out_base / cutoff_str
    out_dir.mkdir(parents=True, exist_ok=True)

    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from scripts.run_backtest_excel import (
        _ensure_workbook, _write_row, HEADERS, _OUTCOME_FILL,
    )

    excel_path = out_dir / f"{cutoff_str}.xlsx"
    log_path   = out_dir / "run_log.txt"

    print(f"\n{'─'*60}")
    print(f"  Cutoff: {cutoff_str}  |  {len(tickers)} tickers  |  {workers} workers")
    print(f"{'─'*60}")

    with open(log_path, "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Cutoff: {cutoff_str}  |  Started: {datetime.now().isoformat()}\n")
        f.write(f"{'='*60}\n")

    outcomes: Dict[str, int] = {}
    errors = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _predict_one,
                ticker, sector, cutoff_str,
                target_days, excel_path, log_path,
            ): (ticker, sector)
            for ticker, sector in tickers
        }

        for i, fut in enumerate(as_completed(futures), start=1):
            status = fut.result()
            print(f"  [{i:>3}/{len(tickers)}] {status}")

            # Tally outcome from status string
            for outcome_key in ("HIT_TARGET", "HIT_STOP", "EXPIRED", "OPEN", "SKIP", "ERROR"):
                if outcome_key in status:
                    outcomes[outcome_key] = outcomes.get(outcome_key, 0) + 1
                    if outcome_key == "ERROR":
                        errors += 1
                    break

    elapsed = time.time() - t0
    trades = sum(outcomes.get(k, 0) for k in ("HIT_TARGET", "HIT_STOP", "EXPIRED", "OPEN"))
    hits   = outcomes.get("HIT_TARGET", 0)
    win_rate = round(hits / trades * 100, 1) if trades else None

    print(f"\n  Done in {elapsed:.0f}s — trades={trades}  hits={hits}  "
          f"win_rate={win_rate}%  skipped={outcomes.get('SKIP',0)}  "
          f"errors={errors}")

    return {
        "cutoff":    cutoff_str,
        "total":     len(tickers),
        "trades":    trades,
        "hits":      hits,
        "win_rate":  win_rate,
        "skipped":   outcomes.get("SKIP", 0),
        "errors":    errors,
        "outcomes":  outcomes,
        "elapsed_s": round(elapsed),
        "excel":     str(excel_path),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Summary printer
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(results: List[Dict[str, Any]], summary_path: Path) -> None:
    header = (
        f"\n{'='*72}\n"
        f"  MULTI-TIMEFRAME BACKTEST SUMMARY\n"
        f"{'='*72}\n"
        f"  {'Cutoff':<13} {'Tickers':>7} {'Trades':>7} {'Hits':>5} "
        f"{'Win%':>6} {'Skipped':>8} {'Errors':>7} {'Time(s)':>8}\n"
        f"  {'-'*70}\n"
    )
    rows = []
    for r in results:
        row = (
            f"  {r['cutoff']:<13} "
            f"{r['total']:>7} "
            f"{r['trades']:>7} "
            f"{r['hits']:>5} "
            f"{str(r['win_rate']) + '%' if r['win_rate'] is not None else 'N/A':>6} "
            f"{r['skipped']:>8} "
            f"{r['errors']:>7} "
            f"{r['elapsed_s']:>8}"
        )
        rows.append(row)

    # Aggregate totals
    total_trades  = sum(r["trades"]   for r in results)
    total_hits    = sum(r["hits"]     for r in results)
    total_skipped = sum(r["skipped"]  for r in results)
    total_errors  = sum(r["errors"]   for r in results)
    overall_wr    = round(total_hits / total_trades * 100, 1) if total_trades else None

    footer = (
        f"  {'-'*70}\n"
        f"  {'TOTAL':<13} "
        f"{'':>7} "
        f"{total_trades:>7} "
        f"{total_hits:>5} "
        f"{str(overall_wr) + '%' if overall_wr is not None else 'N/A':>6} "
        f"{total_skipped:>8} "
        f"{total_errors:>7}\n"
        f"{'='*72}\n"
    )

    text = header + "\n".join(rows) + "\n" + footer
    print(text)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(text)
    print(f"  Summary saved → {summary_path}")

    # Also write JSON for dashboard consumption
    json_path = summary_path.with_suffix(".json")
    json_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"  JSON saved    → {json_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-timeframe backtest — runs one Excel per monthly cutoff date",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: 12 months trailing, 5 tickers/sector (~55 tickers), 4 workers
  python scripts/run_multi_timeframe_backtest.py

  # Only last 6 months
  python scripts/run_multi_timeframe_backtest.py --months 6

  # Explicit dates
  python scripts/run_multi_timeframe_backtest.py --dates 2025-01-01 2025-07-01 2026-01-01

  # Single sector, more tickers
  python scripts/run_multi_timeframe_backtest.py --sector "Energy" --tickers-per-sector 10

  # More workers (faster, higher API rate risk)
  python scripts/run_multi_timeframe_backtest.py --workers 6 --tickers-per-sector 5
        """,
    )
    parser.add_argument(
        "--months", type=int, default=12,
        help="Number of trailing monthly cutoff dates to run (default: 12).",
    )
    parser.add_argument(
        "--dates", nargs="+", default=None,
        help="Explicit YYYY-MM-DD cutoff dates (overrides --months).",
    )
    parser.add_argument(
        "--workers", type=int, default=4,
        help="Thread pool size per cutoff date run (default: 4).",
    )
    parser.add_argument(
        "--target-days", type=int, default=20,
        help="Max trade window in trading days (default: 20).",
    )
    parser.add_argument(
        "--tickers-per-sector", type=int, default=5,
        help="Max tickers per sector (default: 5 → ~55 tickers).",
    )
    parser.add_argument(
        "--sector", default=None,
        help="Optional sector filter, e.g. 'Energy'.",
    )
    args = parser.parse_args()

    # Resolve cutoff dates
    if args.dates:
        cutoff_dates = [
            _last_weekday(datetime.strptime(d, "%Y-%m-%d").date())
            for d in args.dates
        ]
    else:
        cutoff_dates = _trailing_month_starts(args.months)

    # Ticker list (same for all cutoffs)
    tickers = _select_tickers(args.tickers_per_sector, args.sector)

    run_label = date.today().isoformat()
    out_base  = OUTPUT_BASE / "multi" / run_label

    print("=" * 72)
    print("  MULTI-TIMEFRAME BACKTEST RUNNER")
    print(f"  Cutoff dates : {len(cutoff_dates)}")
    for d in cutoff_dates:
        print(f"    • {d.isoformat()}")
    print(f"  Tickers/run  : {len(tickers)} ({args.tickers_per_sector}/sector"
          f"{' — ' + args.sector if args.sector else ''})")
    print(f"  Target days  : {args.target_days}")
    print(f"  Workers      : {args.workers}")
    print(f"  Output base  : {out_base}")
    total_calls = len(cutoff_dates) * len(tickers)
    print(f"  Total API calls (approx): {total_calls}")
    print("=" * 72)

    # Run all cutoff dates sequentially (parallelising within each run)
    all_results: List[Dict[str, Any]] = []
    grand_t0 = time.time()

    for cutoff in cutoff_dates:
        result = _run_single_cutoff(
            cutoff=cutoff,
            tickers=tickers,
            target_days=args.target_days,
            workers=args.workers,
            out_base=out_base,
        )
        all_results.append(result)

    grand_elapsed = time.time() - grand_t0
    print(f"\n  Total wall time: {grand_elapsed/60:.1f} min")

    # Print and save summary
    summary_path = out_base / "summary.txt"
    _print_summary(all_results, summary_path)


if __name__ == "__main__":
    main()
