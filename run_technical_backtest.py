#!/usr/bin/env python3
"""
Single-ticker 5-month technical backtest — Oct 2025 to Feb 2026.

Signal date = 1st of each month (technical analysis run as-of that date).
Result date = last calendar day of the month (price fetched from nearest
              trading day).

Usage:
    python run_technical_backtest.py
    python run_technical_backtest.py --json
    python run_technical_backtest.py --ticker MSFT
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from technical_agent.backtest import build_backtest_report, run_monthly_backtest

MONTHS = [
    (date(2025, 10, 1), date(2025, 10, 31)),
    (date(2025, 11, 1), date(2025, 11, 30)),
    (date(2025, 12, 1), date(2025, 12, 31)),
    (date(2026,  1, 1), date(2026,  1, 31)),
    (date(2026,  2, 1), date(2026,  2, 28)),
]


def main() -> None:
    """Run a 5-month technical backtest for a single ticker."""
    parser = argparse.ArgumentParser(
        description="Run a monthly technical analysis backtest."
    )
    parser.add_argument(
        "--ticker", default="AAPL", help="Ticker symbol (default: AAPL)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print full JSON result instead of text report",
    )
    args = parser.parse_args()

    ticker = args.ticker.upper()
    print(f"Running technical backtest for {ticker} across {len(MONTHS)} months …")
    print("This makes several live API calls — please wait.\n")

    result = run_monthly_backtest(ticker=ticker, months=MONTHS)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(build_backtest_report(result))

    out_file = f"{ticker}_technical_backtest_results.json"
    with open(out_file, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nFull JSON saved to {out_file}")


if __name__ == "__main__":
    main()
