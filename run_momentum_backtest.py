#!/usr/bin/env python3
"""
Orchestrator backtest — mid-cap / under-the-radar momentum stocks.

Picks stocks that aren't mega-cap household names but have shown
strong recent momentum. Runs all in parallel via ThreadPoolExecutor.
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from orchestrator_agent.backtest import run_monthly_backtest, build_backtest_report

MONTHS = [
    (date(2025, 10, 1), date(2025, 10, 31)),
    (date(2025, 11, 1), date(2025, 11, 30)),
    (date(2025, 12, 1), date(2025, 12, 31)),
    (date(2026,  1, 1), date(2026,  1, 31)),
    (date(2026,  2, 1), date(2026,  2, 28)),
]

# Under-the-radar momentum picks — not mega-cap FAANG/MAG7
TICKERS = [
    "ANET",   # Arista Networks — data center networking, strong AI infra play
    "TOST",   # Toast — restaurant tech, growing fast
    "DUOL",   # Duolingo — edtech momentum, strong user growth
    "AXON",   # Axon Enterprise — law enforcement tech, consistent beats
    "DECK",   # Deckers Outdoor — HOKA shoes, under-appreciated growth
    "GEV",    # GE Vernova — energy spin-off, clean energy momentum
]


def _run_one(ticker):
    """Run backtest for a single ticker, return (ticker, result)."""
    try:
        result = run_monthly_backtest(ticker=ticker, months=MONTHS)
        return ticker, result, None
    except Exception as e:
        return ticker, None, str(e)


def main():
    start = time.time()
    print(f"Running orchestrator backtest for {len(TICKERS)} momentum stocks …")
    print(f"Tickers: {', '.join(TICKERS)}")
    print(f"Period : Oct 2025 – Feb 2026  (5 months)\n")

    all_results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_run_one, t): t for t in TICKERS}
        for future in as_completed(futures):
            ticker, result, error = future.result()
            if error:
                print(f"✗ {ticker}: FAILED — {error}\n")
            else:
                all_results[ticker] = result
                s = result["summary"]
                acc = f"{s['accuracy_pct']}%" if s["accuracy_pct"] is not None else "N/A"
                print(f"✓ {ticker}: {s['directional_signals']}/{s['total_periods']} directional, accuracy={acc}")

    elapsed = time.time() - start
    print(f"\n{'=' * 64}")
    print(f"⏱  All done in {elapsed:.1f}s\n")

    # Print detailed reports
    for ticker in TICKERS:
        if ticker in all_results:
            print(build_backtest_report(all_results[ticker]))
            print("\n")

    # Summary table
    print("=" * 70)
    print(f"{'Ticker':<8} {'Dir Signals':>12} {'Correct':>8} {'Accuracy':>10} {'Abstain':>10}")
    print("-" * 70)
    for ticker in TICKERS:
        if ticker in all_results:
            s = all_results[ticker]["summary"]
            acc = f"{s['accuracy_pct']}%" if s["accuracy_pct"] is not None else "N/A"
            abstain = s["total_periods"] - s["directional_signals"]
            print(f"{ticker:<8} {s['directional_signals']:>12} {s['correct_signals']:>8} {acc:>10} {abstain:>10}")
    print("=" * 70)

    # Save all results
    out_file = "momentum_orchestrator_backtest.json"
    with open(out_file, "w") as fh:
        json.dump(all_results, fh, indent=2)
    print(f"\nJSON saved to {out_file}")


if __name__ == "__main__":
    main()
