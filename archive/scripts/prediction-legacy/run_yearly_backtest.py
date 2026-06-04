#!/usr/bin/env python3
"""
run_yearly_backtest.py — Multi-period backtest runner

Runs backtests for multiple cutoff dates (e.g., weekly over a full year)
and consolidates results into a single JSON/Excel output.

Design
──────
• Generates weekly (or custom interval) cutoff dates for a given year
• Runs backtest for each cutoff date independently (no forward-looking data)
• Consolidates all results into one master JSON file
• Each row has its own cutoff date, ensuring temporal integrity

Usage
─────
  python scripts/run_yearly_backtest.py --year 2025 --interval weekly
  python scripts/run_yearly_backtest.py --start 2025-01-01 --end 2025-12-31 --interval weekly
  python scripts/run_yearly_backtest.py --start 2024-06-01 --end 2025-05-31 --interval monthly

Parameters
──────────
  --year          Run backtests for entire year (e.g., 2025)
  --start         Start date (YYYY-MM-DD)
  --end           End date (YYYY-MM-DD)
  --interval      Date interval: weekly, biweekly, monthly (default: weekly)
  --workers       Thread pool size per backtest. Default: 4
  --target-days   Max trade window in trading days. Default: 20
  --tickers-per-sector  Max tickers per sector. Default: 9

Output
──────
  data/output/backtests/yearly_<YEAR>/
      all_results.json         — consolidated JSON with all cutoff dates
      all_results.xlsx         — consolidated Excel workbook
      run_summary.txt          — summary statistics
      by_date/
          2025-01-05.json
          2025-01-12.json
          ...
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUTPUT_BASE = ROOT / "data" / "output" / "backtests"
BACKTEST_SCRIPT = ROOT / "scripts" / "run_backtest_excel.py"


def _last_weekday(d: date) -> date:
    """Get last weekday (Mon-Fri) from a given date."""
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d -= timedelta(days=1)
    return d


def generate_cutoff_dates(
    start_date: date,
    end_date: date,
    interval: str
) -> List[date]:
    """Generate list of cutoff dates based on interval."""
    dates = []
    current = start_date
    
    if interval == "weekly":
        delta = timedelta(days=7)
    elif interval == "biweekly":
        delta = timedelta(days=14)
    elif interval == "monthly":
        delta = timedelta(days=30)  # Approximate
    else:
        raise ValueError(f"Unknown interval: {interval}")
    
    while current <= end_date:
        # Ensure it's a weekday
        weekday = _last_weekday(current)
        if weekday not in dates:
            dates.append(weekday)
        current += delta
    
    return sorted(dates)


def run_single_backtest(
    cutoff_date: date,
    workers: int,
    target_days: int,
    tickers_per_sector: int,
    fmp_api_key: str
) -> dict:
    """Run backtest for a single cutoff date."""
    
    cutoff_str = cutoff_date.isoformat()
    print(f"\n{'='*70}")
    print(f"Running backtest for cutoff date: {cutoff_str}")
    print(f"{'='*70}")
    
    # Run the backtest script
    cmd = [
        sys.executable,
        str(BACKTEST_SCRIPT),
        "--date", cutoff_str,
        "--workers", str(workers),
        "--target-days", str(target_days),
        "--tickers-per-sector", str(tickers_per_sector),
    ]
    
    env = {
        "FMP_API_KEY": fmp_api_key,
        "PATH": subprocess.os.environ.get("PATH", "")
    }
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT)
    )
    
    if result.returncode != 0:
        print(f"ERROR running backtest for {cutoff_str}:")
        print(result.stderr)
        return {"error": result.stderr, "cutoff_date": cutoff_str}
    
    print(result.stdout)
    return {"success": True, "cutoff_date": cutoff_str}


def consolidate_results(
    cutoff_dates: List[date],
    output_dir: Path
) -> dict:
    """Consolidate results from all cutoff dates into single JSON."""
    
    # The daily Excel runner writes to data/output/backtests/<today>/
    # We need to read from the JSON we generated
    today_str = date.today().isoformat()
    source_dir = OUTPUT_BASE / today_str
    source_json = source_dir / f"{today_str}.json"
    
    if not source_json.exists():
        print(f"WARNING: Source JSON not found: {source_json}")
        return {}
    
    # Read the consolidated JSON (has all cutoff dates)
    with open(source_json) as f:
        all_results = json.load(f)
    
    # Save consolidated output
    output_json = output_dir / "all_results.json"
    with open(output_json, "w") as f:
        json.dump(all_results, f, indent=2)
    
    # Generate summary statistics
    summary = {
        "total_records": len(all_results),
        "cutoff_dates": sorted(list(set(r.get("Cutoff Date") for r in all_results if r.get("Cutoff Date")))),
        "total_buy_signals": len([r for r in all_results if r.get("Signal") == "BUY"]),
        "total_avoid_signals": len([r for r in all_results if r.get("Signal") == "AVOID"]),
        "total_hold_signals": len([r for r in all_results if r.get("Signal") == "HOLD"]),
        "total_errors": len([r for r in all_results if r.get("Outcome") == "ERROR"]),
        "outcomes": {}
    }
    
    # Count outcomes
    for r in all_results:
        outcome = r.get("Outcome", "Unknown")
        summary["outcomes"][outcome] = summary["outcomes"].get(outcome, 0) + 1
    
    # Save summary
    summary_path = output_dir / "run_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Multi-period backtest runner with consolidated output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--year", type=int, help="Year to backtest (e.g., 2025)")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    parser.add_argument(
        "--interval",
        choices=["weekly", "biweekly", "monthly"],
        default="weekly",
        help="Cutoff date interval (default: weekly)"
    )
    parser.add_argument("--workers", type=int, default=4, help="Thread pool size (default: 4)")
    parser.add_argument("--target-days", type=int, default=20, help="Trade window in days (default: 20)")
    parser.add_argument("--tickers-per-sector", type=int, default=9, help="Tickers per sector (default: 9)")
    parser.add_argument("--fmp-api-key", required=True, help="Financial Modeling Prep API key")
    
    args = parser.parse_args()
    
    # Determine date range
    if args.year:
        start_date = date(args.year, 1, 1)
        end_date = date(args.year, 12, 31)
        label = f"yearly_{args.year}"
    elif args.start and args.end:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
        label = f"{args.start}_to_{args.end}"
    else:
        print("ERROR: Must specify either --year OR --start and --end")
        sys.exit(1)
    
    # Generate cutoff dates
    cutoff_dates = generate_cutoff_dates(start_date, end_date, args.interval)
    
    print(f"\n{'='*70}")
    print(f"  Multi-Period Backtest Runner")
    print(f"  Period: {start_date} to {end_date}")
    print(f"  Interval: {args.interval}")
    print(f"  Cutoff dates: {len(cutoff_dates)}")
    print(f"  Workers per run: {args.workers}")
    print(f"  Target days: {args.target_days}")
    print(f"{'='*70}\n")
    
    # Show cutoff dates
    print("Cutoff dates to process:")
    for i, d in enumerate(cutoff_dates, 1):
        print(f"  {i:2}. {d.isoformat()}")
    
    print(f"\n{'='*70}")
    confirmation = input("Proceed with backtest? (yes/no): ")
    if confirmation.lower() not in ["yes", "y"]:
        print("Cancelled.")
        sys.exit(0)
    
    # Create output directory
    output_dir = OUTPUT_BASE / label
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run backtests for each cutoff date
    results = []
    for i, cutoff_date in enumerate(cutoff_dates, 1):
        print(f"\n[{i}/{len(cutoff_dates)}] Processing {cutoff_date.isoformat()}...")
        
        result = run_single_backtest(
            cutoff_date=cutoff_date,
            workers=args.workers,
            target_days=args.target_days,
            tickers_per_sector=args.tickers_per_sector,
            fmp_api_key=args.fmp_api_key
        )
        results.append(result)
    
    # Consolidate results
    print(f"\n{'='*70}")
    print("Consolidating results...")
    print(f"{'='*70}")
    
    summary = consolidate_results(cutoff_dates, output_dir)
    
    # Print summary
    print(f"\n{'='*70}")
    print("  BACKTEST COMPLETE")
    print(f"{'='*70}")
    print(f"  Total records: {summary.get('total_records', 0)}")
    print(f"  Cutoff dates: {len(summary.get('cutoff_dates', []))}")
    print(f"  BUY signals: {summary.get('total_buy_signals', 0)}")
    print(f"  AVOID signals: {summary.get('total_avoid_signals', 0)}")
    print(f"  HOLD signals: {summary.get('total_hold_signals', 0)}")
    print(f"  Errors: {summary.get('total_errors', 0)}")
    print(f"\n  Output: {output_dir / 'all_results.json'}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
