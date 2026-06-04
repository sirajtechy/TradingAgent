#!/usr/bin/env python3
"""
run_workstreams.py — Combined runner for Workstream A and Workstream B.

Usage:
  python run_workstreams.py               # runs both
  python run_workstreams.py --workstream a  # Orchestrator Reassessment only
  python run_workstreams.py --workstream b  # Prediction Engine only
  python run_workstreams.py --ticker AAPL   # Predict for a single ticker
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from dateutil.relativedelta import relativedelta


# ─────────────────────────────────────────────────────────────────────────────
# Tickers (same 50 used in sector backtest)
# ─────────────────────────────────────────────────────────────────────────────

SECTOR_TICKERS = [
    "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","AMD","INTC","CRM",
    "JPM","BAC","GS","MS","C","BLK","AXP","WFC","COF","USB",
    "JNJ","UNH","PFE","ABT","BMY","MRK","CVS","CI","HUM","ANTM",
    "XOM","CVX","COP","EOG","DVN","SLB","HAL","BKR","OXY","MPC",
    "WMT","COST","TGT","HD","LOW","AMZN","DG","DLTR","CL","GIS",
]
SECTOR_TICKERS = list(dict.fromkeys(SECTOR_TICKERS))[:50]


def _build_monthly_windows(n_months: int = 12) -> list:
    windows = []
    today = date.today()
    for i in range(n_months, 0, -1):
        first = (today - relativedelta(months=i)).replace(day=1)
        last  = (first + relativedelta(months=1)) - __import__("datetime").timedelta(days=1)
        windows.append((first, last))
    return windows


# ─────────────────────────────────────────────────────────────────────────────
# Workstream A
# ─────────────────────────────────────────────────────────────────────────────

def run_workstream_a() -> None:
    print("\n" + "█" * 70)
    print("█  WORKSTREAM A — ORCHESTRATOR REASSESSMENT")
    print("█" * 70)

    from workstream_a_rca import load_all_signals, run_step1, run_step2, save_rca
    from workstream_a_corrected_backtest import main as run_corrected_backtest

    # Steps 1 & 2 — Load + RCA
    signals = load_all_signals()
    misses  = run_step1(signals)
    rca     = run_step2(signals, misses)
    save_rca(misses, rca)

    # Steps 3 & 4 — Course corrections + re-run
    print("\n" + "─" * 70)
    print("STEP 3 — Course Correction Rules Applied:")
    print("  Rule 1: Dynamic Weight Adjustment (ADX-based)")
    print("  Rule 2: Conflict Override Logic (raise abstain to gap<0.10)")
    print("  Rule 3: Trailing Stop Refinement (3% floor → confidence discount)")
    print("  Rule 4: Regime Detection Filter (vol>25% + 3m_chg<-5% → neutral)")
    print("─" * 70)
    run_corrected_backtest()


# ─────────────────────────────────────────────────────────────────────────────
# Workstream B
# ─────────────────────────────────────────────────────────────────────────────

def run_workstream_b(tickers: list = None, n_months: int = 6) -> None:
    print("\n" + "█" * 70)
    print("█  WORKSTREAM B — TICKER + DATE PREDICTION ENGINE")
    print("█" * 70)

    from agents.prediction.backtester import run_prediction_backtest, print_summary

    use_tickers = tickers or SECTOR_TICKERS[:20]  # default: first 20 for speed
    windows = _build_monthly_windows(n_months)

    print(f"Running prediction backtest: {len(use_tickers)} tickers × {len(windows)} months")
    print("Strategies: EMA Crossover, MACD+RSI, Bollinger Squeeze, Supertrend,")
    print("            OBV Divergence, S/R Breakout, RSI Divergence, Mean Reversion,")
    print("            Ichimoku Cloud, ML Meta-Learner\n")

    summary = run_prediction_backtest(use_tickers, windows)
    print_summary(summary)


def run_single_prediction(ticker: str) -> None:
    """Quick prediction for a single ticker (no backtest)."""
    import pandas as pd
    from datetime import date, timedelta
    from agents.polygon_data import PolygonClient, PolygonDataError
    from agents.prediction.strategies import run_all_strategies
    from agents.prediction.formatter import build_prediction, print_prediction_report

    print(f"\n▶ Fetching data for {ticker.upper()}...")

    df = None
    _polygon = PolygonClient()

    # Polygon primary
    if _polygon.is_available():
        try:
            df = _polygon.fetch_daily_bars(ticker, date.today(), lookback_days=180)
        except PolygonDataError:
            df = None

    # yfinance fallback
    if df is None or df.empty:
        try:
            import yfinance as yf
            df = yf.download(ticker, period="6mo", auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
        except Exception:
            df = None

    if df is None or df.empty:
        print(f"ERROR: No data found for {ticker}")
        return

    print(f"  Got {len(df)} bars. Running 10 strategies...")
    signals  = run_all_strategies(df)
    pred     = build_prediction(ticker, df, signals, entry_date=date.today())
    print_prediction_report(pred)

    # Save
    fname = f"{ticker.upper()}_prediction.json"
    with open(fname, "w") as f:
        json.dump(pred, f, indent=2, default=str)
    print(f"\n✓ Prediction saved → {fname}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Run Workstream A and/or B")
    parser.add_argument("--workstream", choices=["a", "b", "both"], default="both")
    parser.add_argument("--ticker", type=str, default=None,
                        help="Single ticker prediction (skips full backtest)")
    parser.add_argument("--months", type=int, default=6,
                        help="Number of months for Workstream B backtest")
    parser.add_argument("--tickers", type=str, default=None,
                        help="Comma-separated tickers for Workstream B")
    args = parser.parse_args()

    if args.ticker:
        run_single_prediction(args.ticker)
        return

    tickers = args.tickers.split(",") if args.tickers else None

    if args.workstream in ("a", "both"):
        run_workstream_a()

    if args.workstream in ("b", "both"):
        run_workstream_b(tickers=tickers, n_months=args.months)

    print("\n✓ All workstreams complete.")


if __name__ == "__main__":
    main()
