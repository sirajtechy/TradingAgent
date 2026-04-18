"""
prediction_engine/backtester.py — Backtester for the prediction engine.

Runs all 10 strategies over historical monthly windows across 50 tickers,
tracks directional accuracy per strategy and overall, and produces a
summary proving >60% directional accuracy target.

Data source: Polygon.io (primary), yfinance (fallback).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import paths

import pandas as pd

from agents.polygon_data import PolygonClient, PolygonDataError

from .strategies import run_all_strategies
from .formatter import build_prediction

logger = logging.getLogger(__name__)
_polygon = PolygonClient()


# ─────────────────────────────────────────────────────────────────────────────
# Data loading — Polygon primary, yfinance fallback
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_price_data(ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data — Polygon primary, yfinance fallback."""
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    lookback = (end_d - start_d).days + 30

    # Polygon primary
    if _polygon.is_available():
        try:
            df = _polygon.fetch_daily_bars(ticker, end_d, lookback_days=lookback)
            if df is not None and not df.empty and len(df) >= 30:
                return df.sort_index()
        except PolygonDataError:
            pass

    # yfinance fallback
    try:
        import yfinance as yf
        df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if df.empty or len(df) < 30:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df.sort_index()
    except Exception:
        return None


def _fetch_outcome_prices(
    ticker: str, signal_date: date, result_date: date
) -> Optional[Tuple[float, float]]:
    """Fetch start + end price for outcome measurement. Returns (start_price, end_price) or None."""

    # Polygon primary
    if _polygon.is_available():
        try:
            start_result = _polygon.get_close_price(ticker, signal_date)
            end_result = _polygon.get_close_price(ticker, result_date)
            if start_result and end_result:
                return start_result[0], end_result[0]
        except PolygonDataError:
            pass

    # yfinance fallback
    try:
        import yfinance as yf
        outcome_df = yf.download(
            ticker,
            start=signal_date.isoformat(),
            end=(result_date + timedelta(days=5)).isoformat(),
            auto_adjust=True,
            progress=False,
        )
        if isinstance(outcome_df.columns, pd.MultiIndex):
            outcome_df.columns = outcome_df.columns.droplevel(1)
        if outcome_df.empty or len(outcome_df) < 2:
            return None
        return float(outcome_df["Close"].iloc[0]), float(outcome_df["Close"].iloc[-1])
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Single-period evaluation
# ─────────────────────────────────────────────────────────────────────────────

def _evaluate_period(
    ticker: str,
    signal_date: date,
    result_date: date,
    horizon_days: int = 30,
) -> Optional[Dict[str, Any]]:
    """
    Evaluate all strategies for a single (signal_date → result_date) window.

    Args:
        ticker:       Ticker symbol.
        signal_date:  Date strategies are evaluated on.
        result_date:  Date actual outcome is measured.  Derived from
                      signal_date + horizon_days by the caller.
        horizon_days: Holding period in days used for the prediction
                      engine  (passed through to build_prediction).

    Returns None if data is unavailable.
    """
    # Fetch 6 months prior to signal_date for indicator warmup
    hist_start = (signal_date - timedelta(days=180)).isoformat()
    hist_end   = signal_date.isoformat()

    df = _fetch_price_data(ticker, hist_start, hist_end)
    if df is None:
        return None

    # Run all 10 strategies
    try:
        signals = run_all_strategies(df)
    except Exception as e:
        return None

    # Build prediction
    try:
        pred = build_prediction(
            ticker=ticker,
            df=df,
            strategy_signals=signals,
            entry_date=signal_date,
            holding_period_days=horizon_days,
        )
    except Exception:
        return None

    # Fetch actual outcome
    try:
        prices = _fetch_outcome_prices(ticker, signal_date, result_date)
        if prices is None:
            return None
        start_price, end_price = prices
        ret_pct     = (end_price - start_price) / start_price * 100.0
        actual_dir  = "BUY" if ret_pct >= 0 else "SELL"
    except Exception:
        return None

    # Evaluate correctness per strategy
    strategy_results = []
    for s in signals:
        sig = s["signal"]
        if sig == "HOLD":
            correct = None
        elif sig == actual_dir:
            correct = True
        else:
            correct = False
        strategy_results.append({
            "strategy": s["strategy"],
            "signal": sig,
            "strength": s["strength"],
            "correct": correct,
        })

    # Overall correctness
    overall_dir = pred["direction"]
    if overall_dir == "HOLD":
        overall_correct = None
    else:
        overall_correct = (overall_dir == actual_dir)

    return {
        "ticker": ticker,
        "signal_date": signal_date.isoformat(),
        "result_date": result_date.isoformat(),
        "entry_price": pred["entry_price"],
        "end_price": round(end_price, 2),
        "return_pct": round(ret_pct, 2),
        "actual_direction": actual_dir,
        "predicted_direction": overall_dir,
        "correct": overall_correct,
        "confluence_score": pred["confluence"]["confluence_score"],
        "confluence_grade": pred["confluence"]["grade"],
        "strategy_results": strategy_results,
        "target_price": pred["target_price"],
        "stop_loss": pred["stop_loss"],
        "risk_reward": pred["risk_reward"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Full backtest
# ─────────────────────────────────────────────────────────────────────────────

def run_prediction_backtest(
    tickers: List[str],
    months: List[Tuple[date, date]],
    output_dir: str = str(paths.PRED_BACKTEST),
    horizon_days: int = 30,
) -> Dict[str, Any]:
    """
    Run the full prediction backtest across all tickers and months.

    Args:
        tickers:     List of ticker symbols to backtest.
        months:      List of (signal_date, result_date) tuples.  Each
                     result_date should be signal_date + horizon_days.
        output_dir:  Directory to write per-ticker and summary JSON files.
        horizon_days: Holding-period horizon in calendar days.  Controls
                     both the outcome measurement window and the prediction
                     engine's internal holding-period estimate.
                     Default 30 (original behaviour preserved).
    """
    os.makedirs(output_dir, exist_ok=True)

    all_results = []
    strategy_correct: Dict[str, List[bool]] = defaultdict(list)

    total = len(tickers) * len(months)
    done  = 0

    for ticker in tickers:
        ticker_results = []
        for signal_date, result_date in months:
            done += 1
            print(f"  [{done}/{total}] {ticker} {signal_date.isoformat()}", end="\r", flush=True)

            period = _evaluate_period(ticker, signal_date, result_date, horizon_days)
            if period is None:
                continue

            ticker_results.append(period)
            all_results.append(period)

            # Track per-strategy accuracy
            for sr in period["strategy_results"]:
                if sr["correct"] is not None:
                    strategy_correct[sr["strategy"]].append(sr["correct"])

        # Save per-ticker results
        if ticker_results:
            with open(os.path.join(output_dir, f"{ticker}_prediction_backtest.json"), "w") as f:
                json.dump({"ticker": ticker, "periods": ticker_results}, f, indent=2, default=str)

    print()  # newline after progress

    # Compute overall metrics
    directional = [r for r in all_results if r["correct"] is not None]
    correct      = [r for r in directional if r["correct"]]
    accuracy     = len(correct) / len(directional) * 100.0 if directional else 0.0

    # Per-strategy accuracy
    strategy_summary = {}
    for strat, outcomes in strategy_correct.items():
        acc = sum(outcomes) / len(outcomes) * 100.0 if outcomes else 0.0
        strategy_summary[strat] = {
            "total_directional": len(outcomes),
            "correct": sum(outcomes),
            "accuracy_pct": round(acc, 1),
        }

    # Sort by accuracy
    strategy_summary = dict(
        sorted(strategy_summary.items(), key=lambda x: -x[1]["accuracy_pct"])
    )

    summary = {
        "horizon_days": horizon_days,
        "total_evaluated": len(all_results),
        "directional_signals": len(directional),
        "correct_signals": len(correct),
        "overall_accuracy_pct": round(accuracy, 1),
        "target_met": accuracy >= 60.0,
        "strategy_accuracy": strategy_summary,
    }

    # Save full summary
    with open(os.path.join(output_dir, "prediction_backtest_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)

    return summary


# ─────────────────────────────────────────────────────────────────────────────
# CLI runner
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(summary: Dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    print("WORKSTREAM B — PREDICTION ENGINE BACKTEST SUMMARY")
    print("=" * 70)
    print(f"  Total evaluated    : {summary['total_evaluated']}")
    print(f"  Directional signals: {summary['directional_signals']}")
    print(f"  Correct signals    : {summary['correct_signals']}")
    print(f"  Overall Accuracy   : {summary['overall_accuracy_pct']}%  "
          f"{'✓ TARGET MET (≥60%)' if summary['target_met'] else '✗ BELOW 60% TARGET'}")

    print(f"\n{'Strategy':<35} {'Accuracy':>10} {'n':>6}")
    print("-" * 55)
    for strat, data in summary["strategy_accuracy"].items():
        marker = "✓" if data["accuracy_pct"] >= 60 else " "
        print(f"{marker} {strat:<34} {data['accuracy_pct']:>9.1f}% {data['total_directional']:>6}")
