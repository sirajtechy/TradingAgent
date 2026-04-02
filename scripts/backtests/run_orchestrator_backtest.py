#!/usr/bin/env python3
"""
Quick orchestrator backtest — runs AAPL across 5 months using both agents + CWAF fusion.
"""
import json
import sys
import time
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

TICKER = sys.argv[1] if len(sys.argv) > 1 else "AAPL"

start = time.time()
print(f"Running orchestrator backtest for {TICKER} across {len(MONTHS)} months …\n")

result = run_monthly_backtest(ticker=TICKER, months=MONTHS)
elapsed = time.time() - start

print(build_backtest_report(result))
print(f"\n⏱  Completed in {elapsed:.1f}s")

out_file = f"{TICKER}_orchestrator_backtest.json"
with open(out_file, "w") as fh:
    json.dump(result, fh, indent=2)
print(f"JSON saved to {out_file}")
