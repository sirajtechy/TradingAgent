"""
polygon_trade_scanner.py — Trade Setup Scanner using Polygon API + Deep Pattern Engine.

Scans tickers for actionable trade setups with:
  - Entry/exit dates, target price, stop-loss, expected profit %
  - Confidence scores from deep pattern analysis
  - Holding period > 2 days
  - Persists all Polygon data to Excel for future ML training

Usage:
    python -m scripts.polygon.polygon_trade_scanner
    # or directly:
    python scripts/polygon/polygon_trade_scanner.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Ensure project root is on path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import paths
from scripts.polygon.polygon_data_client import PolygonDataClient
from scripts.polygon.deep_pattern_engine import run_deep_analysis, _atr, _rsi, _sma, _ema


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

TECH_TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "ORCL", "ANET", "CRM"]
AS_OF_DATE = "2026-03-03"  # 1 month ago
OUTPUT_DIR = paths.TRADE_SETUPS_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Candlestick patterns (reuse from kgc_patterns — inlined for independence)
# ─────────────────────────────────────────────────────────────────────────────

def _body(o, c): return abs(c - o)
def _rng(h, l): return h - l
def _upper_shad(o, h, c): return h - max(o, c)
def _lower_shad(o, l, c): return min(o, c) - l
def _is_bull(o, c): return c > o
def _is_bear(o, c): return c < o


def detect_candlestick_patterns(df: pd.DataFrame, window: int = 10) -> List[Dict[str, Any]]:
    """Scan last N candles for key candlestick patterns."""
    hits = []
    n = len(df)
    start = max(3, n - window)
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values

    for i in range(start, n):
        dt = str(df["date"].iloc[i])
        bd = _body(o[i], c[i])
        rn = _rng(h[i], l[i])
        if rn == 0:
            continue

        # Doji
        if bd / rn <= 0.05:
            hits.append({"date": dt, "pattern": "Doji", "signal": "neutral", "confidence": 0.50})

        # Hammer
        us = _upper_shad(o[i], h[i], c[i])
        ls = _lower_shad(o[i], l[i], c[i])
        if bd > 0 and ls >= 2 * bd and us <= bd * 0.5 and c[max(0,i-5)] > c[i]:
            hits.append({"date": dt, "pattern": "Hammer", "signal": "bullish", "confidence": 0.65})

        # Shooting Star
        if bd > 0 and us >= 2 * bd and ls <= bd * 0.5 and c[max(0,i-5)] < c[i]:
            hits.append({"date": dt, "pattern": "Shooting Star", "signal": "bearish", "confidence": 0.65})

        # Engulfing (2-bar)
        if i >= 1:
            if _is_bear(o[i-1], c[i-1]) and _is_bull(o[i], c[i]) and o[i] <= c[i-1] and c[i] >= o[i-1]:
                hits.append({"date": dt, "pattern": "Bullish Engulfing", "signal": "bullish", "confidence": 0.70})
            if _is_bull(o[i-1], c[i-1]) and _is_bear(o[i], c[i]) and o[i] >= c[i-1] and c[i] <= o[i-1]:
                hits.append({"date": dt, "pattern": "Bearish Engulfing", "signal": "bearish", "confidence": 0.70})

        # Morning Star / Evening Star (3-bar)
        if i >= 2:
            rn_prev = _rng(h[i-1], l[i-1])
            bd_prev = _body(o[i-1], c[i-1])
            if _is_bear(o[i-2], c[i-2]) and rn_prev > 0 and bd_prev/rn_prev <= 0.30 and _is_bull(o[i], c[i]) and c[i] > (o[i-2]+c[i-2])/2:
                hits.append({"date": dt, "pattern": "Morning Star", "signal": "bullish", "confidence": 0.72})
            if _is_bull(o[i-2], c[i-2]) and rn_prev > 0 and bd_prev/rn_prev <= 0.30 and _is_bear(o[i], c[i]) and c[i] < (o[i-2]+c[i-2])/2:
                hits.append({"date": dt, "pattern": "Evening Star", "signal": "bearish", "confidence": 0.72})

        # Three White Soldiers / Three Black Crows
        if i >= 2:
            if all(_is_bull(o[j], c[j]) for j in [i-2,i-1,i]) and c[i-1]>c[i-2] and c[i]>c[i-1]:
                hits.append({"date": dt, "pattern": "Three White Soldiers", "signal": "bullish", "confidence": 0.75})
            if all(_is_bear(o[j], c[j]) for j in [i-2,i-1,i]) and c[i-1]<c[i-2] and c[i]<c[i-1]:
                hits.append({"date": dt, "pattern": "Three Black Crows", "signal": "bearish", "confidence": 0.75})

    return hits


# ─────────────────────────────────────────────────────────────────────────────
# Trade Setup Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_trade_setup(
    ticker: str,
    daily_df: pd.DataFrame,
    weekly_df: Optional[pd.DataFrame],
    deep_daily: Dict,
    deep_weekly: Optional[Dict],
    candle_signals: List[Dict],
) -> Optional[Dict[str, Any]]:
    """Generate a trade setup with entry, exit, target, stop, and confidence."""

    c = daily_df["close"].values
    h = daily_df["high"].values
    l = daily_df["low"].values
    last_price = c[-1]
    last_date = str(daily_df["date"].iloc[-1])

    # ATR for position sizing
    atr_series = _atr(daily_df, 14)
    atr = atr_series.values[-1]
    rsi_series = _rsi(daily_df["close"], 14)
    rsi = rsi_series.values[-1]

    # Combine all signals
    all_signals = deep_daily["signals"] + candle_signals
    if deep_weekly:
        all_signals += deep_weekly["signals"]

    bull_signals = [s for s in all_signals if s["signal"] == "bullish"]
    bear_signals = [s for s in all_signals if s["signal"] == "bearish"]

    bull_conf = sum(s.get("confidence", 0.5) for s in bull_signals)
    bear_conf = sum(s.get("confidence", 0.5) for s in bear_signals)
    total_conf = bull_conf + bear_conf

    if total_conf == 0:
        return None

    bias_pct = bull_conf / total_conf * 100

    # Determine direction
    if bias_pct >= 58:
        direction = "LONG"
    elif bias_pct <= 42:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"

    if direction == "NEUTRAL":
        return None  # no actionable setup

    # Compute confidence (0-100)
    signal_count = len(bull_signals) + len(bear_signals)
    raw_confidence = bias_pct if direction == "LONG" else (100 - bias_pct)

    # Boost for multi-timeframe agreement
    if deep_weekly and deep_daily["bias"] == deep_weekly["bias"]:
        raw_confidence = min(95, raw_confidence + 5)

    # Penalize for low signal count
    if signal_count < 3:
        raw_confidence *= 0.85

    confidence = round(raw_confidence, 1)

    # Entry, target, stop using ATR
    if direction == "LONG":
        entry_price = last_price
        stop_loss = round(last_price - 2.0 * atr, 2)
        target_price = round(last_price + 3.0 * atr, 2)  # 1.5:1 R:R
        expected_return = round((target_price - entry_price) / entry_price * 100, 2)
        risk_pct = round((entry_price - stop_loss) / entry_price * 100, 2)
    else:  # SHORT
        entry_price = last_price
        stop_loss = round(last_price + 2.0 * atr, 2)
        target_price = round(last_price - 3.0 * atr, 2)
        expected_return = round((entry_price - target_price) / entry_price * 100, 2)
        risk_pct = round((stop_loss - entry_price) / entry_price * 100, 2)

    # Estimate holding period from ATR (target / daily_range)
    avg_daily_range = np.mean(h[-20:] - l[-20:])
    if avg_daily_range > 0:
        holding_days = max(3, int(round(abs(target_price - entry_price) / avg_daily_range)))
    else:
        holding_days = 5

    holding_days = min(holding_days, 20)  # cap at 20 days

    # Exit date estimate
    try:
        entry_dt = date.fromisoformat(last_date)
    except (ValueError, TypeError):
        entry_dt = date.today()
    exit_dt = entry_dt + timedelta(days=int(holding_days * 1.4))  # account for weekends

    # Key patterns driving the signal
    if direction == "LONG":
        key_patterns = [s["pattern"] for s in bull_signals[:5]]
    else:
        key_patterns = [s["pattern"] for s in bear_signals[:5]]

    return {
        "ticker": ticker,
        "direction": direction,
        "entry_date": last_date,
        "entry_price": round(entry_price, 2),
        "target_price": target_price,
        "stop_loss": stop_loss,
        "exit_date_est": exit_dt.isoformat(),
        "expected_return_pct": expected_return,
        "risk_pct": risk_pct,
        "reward_risk_ratio": round(expected_return / risk_pct, 2) if risk_pct > 0 else 0,
        "confidence": confidence,
        "holding_days_est": holding_days,
        "rsi": round(rsi, 1),
        "atr": round(atr, 2),
        "daily_bias": deep_daily["bias"],
        "daily_bias_pct": deep_daily["bias_pct"],
        "weekly_bias": deep_weekly["bias"] if deep_weekly else "N/A",
        "weekly_bias_pct": deep_weekly["bias_pct"] if deep_weekly else None,
        "total_signals": len(all_signals),
        "bullish_signals": len(bull_signals),
        "bearish_signals": len(bear_signals),
        "key_patterns": key_patterns,
        "all_signals": [
            {"pattern": s["pattern"], "signal": s["signal"],
             "confidence": s.get("confidence", 0.5),
             "desc": s.get("desc", ""),
             "category": s.get("category", "candlestick")}
            for s in all_signals
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Scan a single ticker (runs in thread)
# ─────────────────────────────────────────────────────────────────────────────

def scan_ticker(client: PolygonDataClient, ticker: str) -> Dict[str, Any]:
    """Full scan for one ticker: fetch data → patterns → trade setup."""
    t0 = time.time()
    result = {"ticker": ticker, "status": "error", "setup": None, "error": None}

    try:
        # Fetch daily + weekly data
        daily_df, weekly_df = client.fetch_daily_weekly(ticker, to_date=AS_OF_DATE, lookback_days=730)
        if daily_df is None or daily_df.empty:
            result["error"] = "No daily data from Polygon"
            return result

        # Persist to Excel for ML training
        client.save_to_excel(ticker, daily_df, weekly_df)

        # Run deep pattern analysis
        deep_daily = run_deep_analysis(daily_df, "daily")
        deep_weekly = run_deep_analysis(weekly_df, "weekly") if weekly_df is not None and not weekly_df.empty else None

        # Run candlestick pattern detection
        candle_signals = detect_candlestick_patterns(daily_df, window=10)

        # Generate trade setup
        setup = generate_trade_setup(ticker, daily_df, weekly_df, deep_daily, deep_weekly, candle_signals)

        elapsed = round(time.time() - t0, 1)
        result["status"] = "ok"
        result["setup"] = setup
        result["data_bars_daily"] = len(daily_df)
        result["data_bars_weekly"] = len(weekly_df) if weekly_df is not None else 0
        result["deep_daily"] = {k: v for k, v in deep_daily.items() if k != "signals"}
        result["deep_weekly"] = {k: v for k, v in deep_weekly.items() if k != "signals"} if deep_weekly else None
        result["elapsed_sec"] = elapsed

    except Exception as e:
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main scanner
# ─────────────────────────────────────────────────────────────────────────────

def run_scanner(tickers: List[str] = None, max_workers: int = 5) -> List[Dict]:
    """Scan all tickers in parallel and produce trade setups."""
    tickers = tickers or TECH_TICKERS
    client = PolygonDataClient()

    print(f"\n{'='*70}")
    print(f"  POLYGON TRADE SCANNER — {len(tickers)} tickers as of {AS_OF_DATE}")
    print(f"{'='*70}\n")

    results = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(scan_ticker, client, t): t for t in tickers}
        for fut in as_completed(futures):
            ticker = futures[fut]
            try:
                res = fut.result()
                results.append(res)
                status = "✓" if res["status"] == "ok" else "✗"
                setup_str = ""
                if res.get("setup"):
                    s = res["setup"]
                    setup_str = f" → {s['direction']} | conf={s['confidence']:.0f}% | target=${s['target_price']} | R:R={s['reward_risk_ratio']}"
                elif res["status"] == "ok":
                    setup_str = " → NO SETUP (neutral)"
                print(f"  {status} {ticker:<6} ({res.get('elapsed_sec', 0):.1f}s){setup_str}")
            except Exception as e:
                print(f"  ✗ {ticker:<6} FAILED: {e}")
                results.append({"ticker": ticker, "status": "error", "error": str(e)})

    elapsed = round(time.time() - t0, 1)

    # Separate setups from no-setups
    setups = [r for r in results if r.get("setup")]
    no_setups = [r for r in results if r["status"] == "ok" and not r.get("setup")]
    errors = [r for r in results if r["status"] == "error"]

    print(f"\n{'─'*70}")
    print(f"  Completed in {elapsed}s | {len(setups)} setups | {len(no_setups)} neutral | {len(errors)} errors")
    print(f"{'─'*70}\n")

    # Print trade setup summary table
    if setups:
        print(f"  {'TICKER':<7} {'DIR':<6} {'ENTRY':>9} {'TARGET':>9} {'STOP':>9} {'RET%':>7} {'CONF':>6} {'HOLD':>5} {'R:R':>5}")
        print(f"  {'─'*7} {'─'*6} {'─'*9} {'─'*9} {'─'*9} {'─'*7} {'─'*6} {'─'*5} {'─'*5}")
        for r in sorted(setups, key=lambda x: -x["setup"]["confidence"]):
            s = r["setup"]
            print(f"  {s['ticker']:<7} {s['direction']:<6} ${s['entry_price']:>7.2f} ${s['target_price']:>7.2f} ${s['stop_loss']:>7.2f} {s['expected_return_pct']:>6.1f}% {s['confidence']:>5.0f}% {s['holding_days_est']:>4}d {s['reward_risk_ratio']:>4.1f}")

    # Save results
    # 1. Per-ticker JSONs
    for r in results:
        ticker = r["ticker"]
        out_path = OUTPUT_DIR / f"{ticker}_trade_setup_{AS_OF_DATE}.json"
        with open(out_path, "w") as f:
            json.dump(r, f, indent=2, default=str)

    # 2. Consolidated JSON
    consolidated = {
        "scan_date": AS_OF_DATE,
        "run_timestamp": date.today().isoformat(),
        "tickers_scanned": len(tickers),
        "setups_found": len(setups),
        "neutral": len(no_setups),
        "errors": len(errors),
        "elapsed_sec": elapsed,
        "setups": [r["setup"] for r in setups if r.get("setup")],
        "summary": [
            {
                "ticker": r["ticker"],
                "status": r["status"],
                "direction": r["setup"]["direction"] if r.get("setup") else None,
                "confidence": r["setup"]["confidence"] if r.get("setup") else None,
                "expected_return_pct": r["setup"]["expected_return_pct"] if r.get("setup") else None,
            }
            for r in results
        ],
    }
    with open(OUTPUT_DIR / f"scan_results_{AS_OF_DATE}.json", "w") as f:
        json.dump(consolidated, f, indent=2, default=str)

    # 3. Excel output
    if setups:
        rows = []
        for r in setups:
            s = r["setup"]
            rows.append({
                "ticker": s["ticker"],
                "direction": s["direction"],
                "entry_date": s["entry_date"],
                "entry_price": s["entry_price"],
                "target_price": s["target_price"],
                "stop_loss": s["stop_loss"],
                "exit_date_est": s["exit_date_est"],
                "expected_return_pct": s["expected_return_pct"],
                "risk_pct": s["risk_pct"],
                "reward_risk_ratio": s["reward_risk_ratio"],
                "confidence": s["confidence"],
                "holding_days_est": s["holding_days_est"],
                "rsi": s["rsi"],
                "atr": s["atr"],
                "daily_bias": s["daily_bias"],
                "weekly_bias": s["weekly_bias"],
                "key_patterns": ", ".join(s["key_patterns"]),
                "total_signals": s["total_signals"],
                "bullish_signals": s["bullish_signals"],
                "bearish_signals": s["bearish_signals"],
            })
        excel_df = pd.DataFrame(rows)
        excel_path = OUTPUT_DIR / f"trade_setups_{AS_OF_DATE}.xlsx"
        excel_df.to_excel(excel_path, index=False, engine="openpyxl")
        print(f"\n  📊 Excel saved: {excel_path}")

    print(f"  📁 All results saved to: {OUTPUT_DIR}/")
    print()

    return results


if __name__ == "__main__":
    run_scanner()
