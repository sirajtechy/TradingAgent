#!/usr/bin/env python3
"""
AAPL 5-month fundamental backtest — Oct 2025 to Feb 2026.

Signal date = 1st of each month (fundamental analysis run as-of that date).
Result date = last calendar day of the month (price fetched from nearest trading day).

Usage:
    python run_backtest.py
    python run_backtest.py --json          # full JSON output
    python run_backtest.py --ticker MSFT   # different ticker
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.fundamental.backtest import build_backtest_report, run_monthly_backtest

MONTHS = [
    (date(2025, 10, 1), date(2025, 10, 31)),
    (date(2025, 11, 1), date(2025, 11, 30)),
    (date(2025, 12, 1), date(2025, 12, 31)),
    (date(2026, 1,  1), date(2026, 1,  31)),
    (date(2026, 2,  1), date(2026, 2,  28)),
]


def main():
    parser = argparse.ArgumentParser(description="Run a monthly fundamental backtest.")
    parser.add_argument("--ticker", default="AAPL", help="Ticker symbol (default: AAPL)")
    parser.add_argument("--json", action="store_true", help="Print full JSON result instead of text report")
    parser.add_argument(
        "--shariah-standard",
        default="aaoifi",
        choices=["aaoifi", "djim", "sc_malaysia"],
    )
    parser.add_argument(
        "--data-source",
        default="fmp",
        choices=["fmp", "yfinance"],
        help="Data provider: fmp (default) or yfinance (free, any ticker)",
    )
    args = parser.parse_args()

    print(f"Running backtest for {args.ticker.upper()} across {len(MONTHS)} months …")
    print("This makes several live API calls — please wait.\n")

    result = run_monthly_backtest(
        ticker=args.ticker,
        months=MONTHS,
        shariah_standard=args.shariah_standard,
        data_source=args.data_source,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(build_backtest_report(result))

    out_file = f"{args.ticker.upper()}_backtest_results.json"
    with open(out_file, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nFull JSON saved to {out_file}")


if __name__ == "__main__":
    main()
