#!/usr/bin/env python3
"""
run_swing_backtest_jan2026.py
==============================
Swing-trade backtest against the Halal universe with cutoff 1 Jan 2026.

Design
------
  • TRAINING  DATA : All Polygon history up to (but not past) each signal_date.
  • SIGNAL  DATES  : 2026-01-02, 2026-02-03, 2026-03-03  (historical, outcomes
                      can be measured from Polygon because today > exit_date).
  • CURRENT  SIGNAL: 2026-04-08 (most recent trading day) — live forward picks.
  • DATA SOURCE    : Polygon.io *only*.  If Polygon is unreachable, the ticker
                      is skipped with a clear warning; yfinance is never used.
  • TIMEFRAMES     : Daily (primary) + Weekly (conviction overlay).
  • SWING FILTER   : 3 ≤ trade_duration_days ≤ 19  (strict).
  • PATTERNS       : All 8 chart-pattern detectors run on each signal date.
                      Pattern triggers are listed per trade, and pattern
                      presence boosts conviction when direction aligns.
  • EVALUATION     : 2×2 confusion matrix (BULLISH/BEARISH vs ACTUAL UP/DOWN)
                      with breakdowns by confidence band and timeframe alignment.

Ticker selection (default: 10 tickers)
---------------------------------------
  4 large-cap + 3 mid-cap + 3 small-cap drawn in order from
  data/input/master_data/halal_top5_per_sector.json.
  Override with --tickers AAPL,MSFT,NVDA.

Outputs
-------
  data/output/backtests/swing_2026/swing_backtest_YYYYMMDD_HHMMSS.json
  data/output/backtests/swing_2026/swing_backtest_latest.json  (always updated)

Usage
-----
  # Default 10-ticker run:
  python scripts/backtests/run_swing_backtest_jan2026.py

  # Custom ticker list:
  python scripts/backtests/run_swing_backtest_jan2026.py --tickers AAPL,MSFT,NVDA,XOM

  # Skip confusion matrix (faster):
  python scripts/backtests/run_swing_backtest_jan2026.py --no-matrix

  # Verbose (shows each period as it runs):
  python scripts/backtests/run_swing_backtest_jan2026.py --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── project root ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import paths
from agents.polygon_data import PolygonClient, PolygonDataError
from agents.technical.exceptions import DataUnavailableError, InsufficientDataError
from agents.technical.indicators import compute_all_indicators
from agents.technical.low_volume_validator import (
    apply_reliability_adjustments,
    validate_stock_reliability,
)
from agents.technical.models import OHLCVBar, RawTechnicalSnapshot, TechnicalRequest
from agents.technical.patterns import detect_all_patterns
from agents.technical.rules import evaluate_snapshot
from agents.technical.service import analyze_ticker

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("swing_backtest")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

CUTOFF_DATE         = date(2025, 12, 31)   # last date used for training context
TODAY               = date(2026, 4, 9)     # hard-coded so script is reproducible

# Monthly historical signal dates (first (approx) trading day of each month)
HISTORICAL_WINDOWS: List[Tuple[date, date]] = [
    (date(2026, 1,  2), date(2026, 1, 31)),
    (date(2026, 2,  3), date(2026, 2, 28)),
    (date(2026, 3,  3), date(2026, 3, 31)),
]

# Current / live signal — latest completed trading day
CURRENT_SIGNAL_DATE = date(2026, 4, 8)   # most recent trading day before today
CURRENT_RESULT_DATE = date(2026, 4, 30)  # open-ended; no actuals yet

# Swing trade criteria
SWING_MIN_DAYS = 3
SWING_MAX_DAYS = 19

# ATR multipliers
ATR_TARGET_MULT = 2.0
ATR_STOP_MULT   = 1.5

# Polygon weekly lookback (calendar days going back from signal_date)
WEEKLY_LOOKBACK_DAYS = 1825   # ~5 years maximum

# Max parallel workers (keep below Polygon rate limit headroom)
MAX_WORKERS = 3

# Output directory
OUTPUT_DIR = paths.BACKTEST_DIR / "swing_2026"

# ─────────────────────────────────────────────────────────────────────────────
# Polygon client (module-level singleton)
# ─────────────────────────────────────────────────────────────────────────────
_polygon = PolygonClient()


def _abort_if_no_polygon() -> None:
    """Exit immediately if POLYGON_API_KEY is not configured."""
    if not _polygon.is_available():
        print(
            "\n[ERROR]  POLYGON_API_KEY is not set in your environment or .env file.\n"
            "         This script is Polygon-only (no yfinance fallback).\n"
            "         Set POLYGON_API_KEY and re-run.\n"
        )
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Ticker selection
# ─────────────────────────────────────────────────────────────────────────────

def _load_default_tickers(n_large: int = 4, n_mid: int = 3, n_small: int = 3) -> List[Dict]:
    """
    Load the first n_large/n_mid/n_small tickers from halal_top5_per_sector.json.

    Returns a list of dicts: [{"ticker": str, "cap_tier": str, "sector": str}]
    """
    master_path = paths.TOP5_PER_SECTOR
    if not master_path.exists():
        print(f"[WARN]  Master data not found: {master_path}  — using hardcoded fallback.")
        return [
            {"ticker": t, "cap_tier": "large", "sector": "Unknown"}
            for t in ["CSCO", "ANET", "MSI", "TSLA", "CARG", "DDS", "ALV", "DGII", "STRA", "FDP"]
        ]

    raw = json.loads(master_path.read_text())

    # raw is either {sector: [ticker_dicts]} or {sector: {tickers: [...]}}
    all_tickers: List[Dict] = []
    for sector_name, sector_data in raw.items():
        if isinstance(sector_data, list):
            items = sector_data
        elif isinstance(sector_data, dict):
            items = sector_data.get("tickers", [])
        else:
            continue
        for item in items:
            if isinstance(item, dict) and "ticker" in item:
                all_tickers.append({
                    "ticker":   item["ticker"],
                    "cap_tier": item.get("cap_tier", "unknown"),
                    "sector":   sector_name,
                })

    large  = [t for t in all_tickers if t["cap_tier"] == "large"]
    mid    = [t for t in all_tickers if t["cap_tier"] == "mid"]
    small  = [t for t in all_tickers if t["cap_tier"] in ("small", "micro", "nano")]

    selected = (
        large[:n_large]
        + mid[:n_mid]
        + small[:n_small]
    )
    return selected


# ─────────────────────────────────────────────────────────────────────────────
# Weekly analysis pipeline (Polygon-only, manual)
# ─────────────────────────────────────────────────────────────────────────────

def _df_to_bars(df) -> List[OHLCVBar]:
    """Convert a Polygon DataFrame to a list of OHLCVBar, oldest-first."""
    bars: List[OHLCVBar] = []
    for idx, row in df.iterrows():
        try:
            bar_date = idx.date() if hasattr(idx, "date") else idx
            bars.append(OHLCVBar(
                bar_date=bar_date,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row.get("Volume", 0.0)),
            ))
        except Exception:
            continue
    bars.sort(key=lambda b: b.bar_date)
    return bars


def _run_weekly_analysis(
    ticker: str,
    signal_date: date,
    company_name: str = "",
    sector: str = "Unknown",
) -> Optional[Dict[str, Any]]:
    """
    Fetch weekly bars from Polygon and run the full technical engine.

    Returns the evaluate_snapshot result dict, or None if data unavailable.
    This is deliberately Polygon-only: returns None (no yfinance fallback).
    """
    df = _polygon.fetch_weekly_bars(
        ticker,
        as_of=signal_date,
        lookback_days=WEEKLY_LOOKBACK_DAYS,
    )
    if df is None or df.empty:
        return None

    bars = _df_to_bars(df)
    if len(bars) < 52:  # need at least 1 year of weekly bars
        return None

    closes  = [b.close  for b in bars]
    highs   = [b.high   for b in bars]
    lows    = [b.low    for b in bars]
    volumes = [b.volume for b in bars]

    indicators = compute_all_indicators(closes, highs, lows, volumes)

    pattern_signals, _ = detect_all_patterns(bars)

    request  = TechnicalRequest(ticker=ticker.upper(), as_of_date=signal_date)
    snapshot = RawTechnicalSnapshot(
        request=request,
        company_name=company_name or ticker,
        sector=sector,
        industry="Unknown",
        bars=bars,
        as_of_price=bars[-1].close,
        as_of_price_date=bars[-1].bar_date,
        warnings=[],
    )

    evaluation = evaluate_snapshot(snapshot, indicators, pattern_signals)

    # Apply low-volume reliability adjustments (same as the daily pipeline)
    reliability = validate_stock_reliability(closes, volumes, ticker)
    evaluation  = apply_reliability_adjustments(evaluation, reliability)

    return evaluation


# ─────────────────────────────────────────────────────────────────────────────
# Trade setup computation
# ─────────────────────────────────────────────────────────────────────────────

_BAND_TO_SIGNAL = {
    "strong":         "BULLISH",
    "good":           "BULLISH",
    "mixed_positive": "BULLISH",
    "mixed":          "NEUTRAL",
    "weak":           "BEARISH",
}


def _holding_days_from_adx_score(adx: Optional[float], score: float) -> int:
    """
    Derive a swing holding-day estimate from ADX and composite score.

    ADX ≥ 30 → fast trend  → 3–5 days
    ADX 20–30 → moderate   → 5–8 days
    ADX 15–20 → slow trend → 8–14 days
    ADX < 15 or None        → choppy  → 14–19 days (often filtered out)
    """
    if adx is not None and adx >= 30:
        return max(SWING_MIN_DAYS, round(score / 20))
    elif adx is not None and adx >= 20:
        return max(5, round(score / 12))
    elif adx is not None and adx >= 15:
        return max(8, round(score / 9))
    else:
        return max(12, round(score / 6))


def _pattern_triggers(daily_result: Dict, min_confidence: float = 0.35) -> List[Dict]:
    """
    Extract confirmed / high-confidence patterns from the daily analysis.

    Returns a simplified list of the patterns relevant to the trade direction.
    The serialized key from graph.py is 'name'; 'pattern_name' is the dataclass field.
    """
    raw_patterns = daily_result.get("patterns", []) or []
    out: List[Dict] = []
    for p in raw_patterns:
        conf = p.get("confidence", 0.0)
        if conf >= min_confidence:
            # graph.py serializes as 'name'; dataclass field is 'pattern_name'
            pat_name = p.get("name") or p.get("pattern_name") or "Unknown"
            out.append({
                "name":                pat_name,
                "direction":           p.get("direction"),
                "confidence":          round(conf, 3),
                "breakout_confirmed":  p.get("breakout_confirmed", False),
                "volume_confirmed":    p.get("volume_confirmation", False),
                "breakout_price":      p.get("breakout_price"),
                "pattern_target":      p.get("pattern_target"),
                "start_date":          p.get("start_date"),
                "end_date":            p.get("end_date"),
                "description":         p.get("description", ""),
            })
    return out


def _timeframe_alignment(daily_signal: str, weekly_signal: Optional[str]) -> str:
    """Classify agreement between daily (primary) and weekly (overlay) signals."""
    if weekly_signal is None:
        return "daily_only"
    if daily_signal == "NEUTRAL":
        return "daily_neutral"
    if weekly_signal == "NEUTRAL":
        return "weekly_neutral"
    if daily_signal == weekly_signal:
        return "aligned"       # strongest conviction
    return "conflict"          # caution — opposing signals


def _compute_trade_setup(
    daily_result: Dict[str, Any],
    weekly_result: Optional[Dict[str, Any]],
    signal_date: date,
    result_date: date,
    ticker_meta: Dict,
) -> Optional[Dict[str, Any]]:
    """
    Derive an ATR-based swing trade setup from daily + weekly analysis.

    Returns None when:
      - daily signal is NEUTRAL
      - holding_days_est is outside [SWING_MIN_DAYS, SWING_MAX_DAYS]
      - entry price or ATR is unavailable
    """
    # ── Entry price ───────────────────────────────────────────────────
    entry_price: Optional[float] = (
        daily_result.get("as_of_price", {}).get("price")
        or daily_result.get("as_of_price")
    )
    if isinstance(entry_price, dict):
        entry_price = entry_price.get("price")
    if not entry_price or entry_price <= 0:
        return None

    # ── Daily score & band ────────────────────────────────────────────
    exp   = daily_result.get("experimental_score", {})
    score: Optional[float] = None
    band:  Optional[str]   = None
    if isinstance(exp, dict) and exp.get("available"):
        score = exp.get("score")
        band  = exp.get("band")
        daily_confidence     = exp.get("confidence", "medium")
        daily_confidence_pct = exp.get("confidence_pct", 50.0)
        adx_gate_applied     = exp.get("adx_gate_applied", False)
    else:
        return None

    if score is None or band is None:
        return None

    daily_signal = _BAND_TO_SIGNAL.get(band, "NEUTRAL")
    if daily_signal == "NEUTRAL":
        return None

    # ── Indicators ────────────────────────────────────────────────────
    key_ind: Dict = daily_result.get("key_indicators", {}) or {}
    atr: float = key_ind.get("atr_14") or (entry_price * 0.02)
    adx: Optional[float] = key_ind.get("adx")
    rsi: Optional[float] = key_ind.get("rsi_14")
    volume_avg: Optional[float] = key_ind.get("volume_20d_avg")

    # ── Holding days estimate (swing filter) ──────────────────────────
    holding_days = _holding_days_from_adx_score(adx, score)

    if not (SWING_MIN_DAYS <= holding_days <= SWING_MAX_DAYS):
        return None

    # ── Prices ───────────────────────────────────────────────────────
    if daily_signal == "BULLISH":
        target_price = round(entry_price + ATR_TARGET_MULT * atr, 2)
        stop_loss    = round(entry_price - ATR_STOP_MULT  * atr, 2)
    else:  # BEARISH
        target_price = round(entry_price - ATR_TARGET_MULT * atr, 2)
        stop_loss    = round(entry_price + ATR_STOP_MULT  * atr, 2)

    expected_profit_pct = round(abs(target_price - entry_price) / entry_price * 100.0, 2)
    risk_pct            = round(abs(stop_loss    - entry_price) / entry_price * 100.0, 2)
    rr_ratio            = round(expected_profit_pct / risk_pct, 2) if risk_pct > 0 else None

    # ── Exit date estimate ────────────────────────────────────────────
    exit_date_est = signal_date + timedelta(days=int(holding_days * 1.4))
    if exit_date_est > result_date:
        exit_date_est = result_date

    # ── Profit probability ────────────────────────────────────────────
    if daily_signal == "BULLISH":
        profit_prob = round(min(85.0, max(40.0, score * 0.5 + 20.0)), 1)
    else:
        profit_prob = round(min(85.0, max(40.0, (100.0 - score) * 0.5 + 20.0)), 1)

    # ── Weekly overlay ────────────────────────────────────────────────
    weekly_signal: Optional[str] = None
    weekly_score:  Optional[float] = None
    weekly_band:   Optional[str]   = None
    weekly_patterns: List[Dict] = []

    if weekly_result:
        w_exp = weekly_result.get("experimental_score", {})
        if isinstance(w_exp, dict) and w_exp.get("available"):
            weekly_band   = w_exp.get("band")
            weekly_score  = w_exp.get("score")
            weekly_signal = _BAND_TO_SIGNAL.get(weekly_band or "", "NEUTRAL")
            weekly_patterns = _pattern_triggers(weekly_result)

    # ── Timeframe alignment ───────────────────────────────────────────
    tf_alignment = _timeframe_alignment(daily_signal, weekly_signal)

    # ── Conviction boost from aligned patterns ────────────────────────
    pattern_triggers = _pattern_triggers(daily_result)
    aligned_pattern_count = sum(
        1 for p in pattern_triggers
        if (daily_signal == "BULLISH" and p["direction"] == "bullish")
        or (daily_signal == "BEARISH" and p["direction"] == "bearish")
    )
    # Boost confidence_pct slightly if patterns confirm direction
    boosted_confidence_pct = min(
        99.0,
        daily_confidence_pct + (aligned_pattern_count * 4.0),
    )

    # ── Confidence band ───────────────────────────────────────────────
    if boosted_confidence_pct >= 70:
        confidence_band = "high"
    elif boosted_confidence_pct >= 40:
        confidence_band = "medium"
    else:
        confidence_band = "low"

    # Weekly alignment adds extra weight to confidence for scoring purposes
    if tf_alignment == "aligned":
        confidence_band_final = confidence_band
    elif tf_alignment == "conflict":
        # Downgrade one tier when timeframes disagree
        if confidence_band == "high":
            confidence_band_final = "medium"
        else:
            confidence_band_final = "low"
    else:
        confidence_band_final = confidence_band

    return {
        "direction":             daily_signal,
        "entry_price":           round(entry_price, 2),
        "target_price":          target_price,
        "stop_loss":             stop_loss,
        "expected_profit_pct":   expected_profit_pct,
        "risk_pct":              risk_pct,
        "reward_risk_ratio":     rr_ratio,
        "holding_days_est":      holding_days,
        "entry_date":            signal_date.isoformat(),
        "exit_date_est":         exit_date_est.isoformat(),
        "result_date":           result_date.isoformat(),
        # Score & confidence
        "daily_score":           round(score, 1),
        "daily_band":            band,
        "daily_signal":          daily_signal,
        "daily_confidence":      daily_confidence,
        "daily_confidence_pct":  round(daily_confidence_pct, 1),
        "adx_gate_applied":      adx_gate_applied,
        "confidence_band":       confidence_band_final,
        "boosted_confidence_pct": round(boosted_confidence_pct, 1),
        "profit_probability":    profit_prob,
        # Indicators
        "atr_at_entry":          round(atr, 2),
        "adx_at_entry":          adx,
        "rsi_at_entry":          rsi,
        "volume_20d_avg":        volume_avg,
        # Patterns
        "pattern_triggers":      pattern_triggers,
        "aligned_pattern_count": aligned_pattern_count,
        # Weekly overlay
        "weekly_signal":         weekly_signal,
        "weekly_score":          weekly_score,
        "weekly_band":           weekly_band,
        "weekly_pattern_triggers": weekly_patterns,
        "timeframe_alignment":   tf_alignment,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Actual outcome lookup
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_actual_outcome(
    ticker: str,
    trade_setup: Dict,
    start_price: float,
) -> Optional[Dict[str, Any]]:
    """
    Fetch the actual price at exit_date_est from Polygon.

    Returns None if the window hasn't closed yet (result_date > today).
    """
    exit_date = date.fromisoformat(trade_setup["exit_date_est"])
    if exit_date > TODAY:
        return None   # trade still open

    # Use the result/exit date to get the closing price
    result = _polygon.get_close_price(ticker, exit_date)
    if result is None:
        return {"error": f"No price data for {ticker} at {exit_date.isoformat()}"}

    end_price, actual_bar_date = result
    price_return_pct = round((end_price - start_price) / start_price * 100.0, 2)
    actual_direction = "UP" if price_return_pct >= 0 else "DOWN"

    predicted = trade_setup["direction"]
    if predicted == "BULLISH":
        signal_correct = (actual_direction == "UP")
    elif predicted == "BEARISH":
        signal_correct = (actual_direction == "DOWN")
    else:
        signal_correct = None

    return {
        "end_price":           round(end_price, 2),
        "actual_date":         actual_bar_date.isoformat(),
        "price_return_pct":    price_return_pct,
        "actual_direction":    actual_direction,
        "predicted_direction": predicted,
        "signal_correct":      signal_correct,
        # Convenience aliases matching the dashboard's expected field names
        "actual_exit_price":   round(end_price, 2),
        "actual_exit_date":    actual_bar_date.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Single-period evaluator
# ─────────────────────────────────────────────────────────────────────────────

def _run_period(
    ticker: str,
    cap_tier: str,
    sector: str,
    signal_date: date,
    result_date: date,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run daily + weekly analysis for one ticker on one signal_date.

    Always returns a dict (never raises externally visible exceptions).
    """
    period_label = signal_date.strftime("%B %Y")
    if verbose:
        print(f"  [{ticker}]  {period_label}  …", end="", flush=True)

    base_record: Dict[str, Any] = {
        "period":           period_label,
        "signal_date":      signal_date.isoformat(),
        "result_date":      result_date.isoformat(),
        "is_current":       signal_date >= CURRENT_SIGNAL_DATE,
        "trade_setup":      None,
        "actual_outcome":   None,
        "error":            None,
    }

    # ── Step 1: daily analysis via analyze_ticker ───────────────────
    try:
        daily_result = analyze_ticker(ticker=ticker, as_of_date=signal_date.isoformat())
    except (DataUnavailableError, InsufficientDataError) as exc:
        base_record["error"] = f"Polygon data unavailable: {exc}"
        if verbose:
            print(f"  [SKIP — no Polygon data: {exc}]")
        return base_record
    except Exception as exc:
        base_record["error"] = str(exc)
        if verbose:
            print(f"  [ERROR: {exc}]")
        return base_record

    # Polygon-only guard: if data came from yfinance, skip the ticker
    daily_warnings = daily_result.get("warnings", []) or []
    if any("Yahoo Finance" in w for w in daily_warnings):
        base_record["error"] = "Skipped: Polygon unavailable for this ticker; yfinance disabled."
        if verbose:
            print("  [SKIP — Polygon unavailable, yfinance disabled]")
        return base_record

    # ── Step 2: weekly analysis (manual Polygon pipeline) ──────────
    company_name = daily_result.get("company_name", ticker)
    try:
        weekly_result = _run_weekly_analysis(
            ticker, signal_date, company_name=company_name, sector=sector
        )
    except Exception:
        weekly_result = None   # weekly is advisory; never fatal

    # ── Step 3: compute trade setup with swing filter ───────────────
    trade_setup = _compute_trade_setup(
        daily_result, weekly_result, signal_date, result_date,
        ticker_meta={"ticker": ticker, "cap_tier": cap_tier, "sector": sector},
    )

    base_record["daily_analysis_summary"] = {
        "band":           (daily_result.get("experimental_score") or {}).get("band"),
        "score":          (daily_result.get("experimental_score") or {}).get("score"),
        "signal":         _BAND_TO_SIGNAL.get(
                              (daily_result.get("experimental_score") or {}).get("band", ""), "NEUTRAL"
                          ),
        "confidence_pct": (daily_result.get("experimental_score") or {}).get("confidence_pct"),
    }

    if trade_setup is None:
        # Explain *why* there's no trade
        daily_band = (daily_result.get("experimental_score") or {}).get("band", "unknown")
        daily_signal = _BAND_TO_SIGNAL.get(daily_band, "NEUTRAL")
        if daily_signal == "NEUTRAL":
            base_record["no_trade_reason"] = "NEUTRAL signal — no directional conviction"
        else:
            key_ind = daily_result.get("key_indicators") or {}
            adx_val = key_ind.get("adx")
            raw_days = _holding_days_from_adx_score(
                adx_val, (daily_result.get("experimental_score") or {}).get("score") or 50.0
            )
            base_record["no_trade_reason"] = (
                f"{daily_signal} signal but holding_days_est={raw_days} "
                f"outside [{SWING_MIN_DAYS}–{SWING_MAX_DAYS}] swing window"
            )
        if verbose:
            print(f"  no trade ({base_record['no_trade_reason']})")
        return base_record

    base_record["trade_setup"] = trade_setup

    # ── Step 4: actual outcome (only for completed windows) ─────────
    entry_price = trade_setup["entry_price"]
    if entry_price and entry_price > 0:
        actual = _fetch_actual_outcome(ticker, trade_setup, start_price=entry_price)
        base_record["actual_outcome"] = actual

    if verbose:
        ts = trade_setup
        ao = base_record.get("actual_outcome")
        outcome_str = ""
        exit_info = ""
        if ao and "signal_correct" in ao:
            outcome_str = "  ✓" if ao["signal_correct"] else "  ✗"
            exit_info = (
                f"  exit={ao['actual_exit_date']}@{ao['actual_exit_price']}"
                f"  ({ao['price_return_pct']:+.2f}%)"
            )
        pats_names = [p2['name'] for p2 in (ts.get('pattern_triggers') or [])]
        pat_str = f"  patterns={pats_names}" if pats_names else ""
        print(
            f"  {ts['direction']}  entry={ts['entry_date']}@{ts['entry_price']}"
            f"→target={ts['target_price']}  stop={ts['stop_loss']}"
            f"  hold={ts['holding_days_est']}d  exit_est={ts['exit_date_est']}"
            f"  tf={ts['timeframe_alignment']}{exit_info}{pat_str}{outcome_str}"
        )

    return base_record


# ─────────────────────────────────────────────────────────────────────────────
# Confusion matrix
# ─────────────────────────────────────────────────────────────────────────────

def _matrix_metrics(TP: int, FP: int, FN: int, TN: int) -> Dict[str, Any]:
    tp, fp, fn, tn = TP, FP, FN, TN
    total = tp + fp + fn + tn
    accuracy  = round((tp + tn) / total * 100.0, 2) if total else None
    precision = round(tp / (tp + fp) * 100.0, 2) if (tp + fp) > 0 else None
    recall    = round(tp / (tp + fn) * 100.0, 2) if (tp + fn) > 0 else None
    f1 = (
        round(2 * precision * recall / (precision + recall), 2)
        if precision and recall else None
    )
    # Matthews Correlation Coefficient — robust for imbalanced sets
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc   = round((tp * tn - fp * fn) / denom, 4) if denom > 0 else None

    return {
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "total_evaluated": total,
        "accuracy_pct":    accuracy,
        "precision_pct":   precision,   # "when BULL predicted, how often correct"
        "recall_pct":      recall,       # "of all actual UPs, how many caught"
        "f1_score":        f1,
        "MCC":             mcc,
    }


def _build_confusion_matrix(all_periods: List[Dict]) -> Dict[str, Any]:
    """
    Build a 2×2 confusion matrix across all completed trades.

    Rows    = predicted direction (BULLISH / BEARISH)
    Columns = actual   direction  (UP     / DOWN)

    Additional breakdowns:
      - by confidence_band (high / medium / low)
      - by timeframe_alignment (aligned / conflict / partial)
    """

    def _empty_counts() -> Dict:
        return {"TP": 0, "FP": 0, "FN": 0, "TN": 0,
                "neutral_count": 0, "no_data_count": 0}

    overall = _empty_counts()
    by_confidence: Dict[str, Dict] = {
        "high":   _empty_counts(),
        "medium": _empty_counts(),
        "low":    _empty_counts(),
    }
    by_alignment: Dict[str, Dict] = {
        "aligned":        _empty_counts(),
        "conflict":       _empty_counts(),
        "weekly_neutral": _empty_counts(),
        "daily_only":     _empty_counts(),
    }
    by_timeframe: Dict[str, Dict] = {
        "daily":  _empty_counts(),
        "weekly": _empty_counts(),
    }

    n_no_trade = 0
    n_neutral  = 0
    n_pending  = 0

    for period in all_periods:
        ts = period.get("trade_setup")
        if ts is None:
            n_no_trade += 1
            continue

        ao = period.get("actual_outcome")
        if ao is None or "signal_correct" not in ao:
            n_pending += 1
            continue   # outcome not yet available

        predicted  = ts["direction"]   # BULLISH | BEARISH
        actual_dir = ao["actual_direction"]  # UP | DOWN
        correct    = ao["signal_correct"]    # bool

        conf_band  = ts.get("confidence_band", "medium")
        tf_align   = ts.get("timeframe_alignment", "daily_only")

        # ──── categorise into TP / FP / FN / TN ─────────────────────
        # BULLISH → UP  = TP  (correctly called rise)
        # BULLISH → DOWN= FP  (called rise, went down)
        # BEARISH → DOWN= TN  (correctly called fall)
        # BEARISH → UP  = FN  (called fall, went up)
        def _tally(bucket: Dict) -> None:
            if predicted == "BULLISH":
                if actual_dir == "UP":
                    bucket["TP"] += 1
                else:
                    bucket["FP"] += 1
            else:  # BEARISH
                if actual_dir == "DOWN":
                    bucket["TN"] += 1
                else:
                    bucket["FN"] += 1

        _tally(overall)
        _tally(by_confidence.get(conf_band, by_confidence["medium"]))
        _tally(by_alignment.get(tf_align, by_alignment["daily_only"]))
        # Daily gets every completed trade
        _tally(by_timeframe["daily"])
        # Weekly only if both signals available
        if ts.get("weekly_signal") is not None:
            _tally(by_timeframe["weekly"])

    return {
        "overall":        _matrix_metrics(**{k: overall[k] for k in ("TP", "FP", "FN", "TN")}),
        "by_confidence":  {
            k: _matrix_metrics(**{x: v[x] for x in ("TP", "FP", "FN", "TN")})
            for k, v in by_confidence.items()
        },
        "by_alignment":   {
            k: _matrix_metrics(**{x: v[x] for x in ("TP", "FP", "FN", "TN")})
            for k, v in by_alignment.items()
        },
        "by_timeframe":   {
            k: _matrix_metrics(**{x: v[x] for x in ("TP", "FP", "FN", "TN")})
            for k, v in by_timeframe.items()
        },
        "meta": {
            "no_trade_periods": n_no_trade,   # NEUTRAL / swing-filtered out
            "pending_periods":  n_pending,    # exit date not yet reached
            "note": (
                "TP: predicted BULLISH + actual UP  |  "
                "FP: predicted BULLISH + actual DOWN  |  "
                "FN: predicted BEARISH + actual UP   |  "
                "TN: predicted BEARISH + actual DOWN"
            ),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Per-ticker runner
# ─────────────────────────────────────────────────────────────────────────────

def _run_ticker(ticker_meta: Dict, windows: List[Tuple[date, date]], verbose: bool) -> Dict:
    """Run all windows for a single ticker and return the full ticker result."""
    ticker   = ticker_meta["ticker"]
    cap_tier = ticker_meta.get("cap_tier", "unknown")
    sector   = ticker_meta.get("sector",   "Unknown")

    all_periods: List[Dict] = []
    for signal_date, result_date in windows:
        period = _run_period(
            ticker, cap_tier, sector, signal_date, result_date, verbose=verbose
        )
        all_periods.append(period)
        # Small sleep between periods to avoid hammering Polygon
        time.sleep(0.3)

    # ── Per-ticker summary ────────────────────────────────────────────
    completed_trades = [
        p for p in all_periods
        if p.get("trade_setup") and p.get("actual_outcome")
           and isinstance(p["actual_outcome"], dict)
           and "signal_correct" in p["actual_outcome"]
    ]
    n_correct = sum(1 for p in completed_trades if p["actual_outcome"]["signal_correct"])
    accuracy = (
        round(n_correct / len(completed_trades) * 100.0, 1)
        if completed_trades else None
    )

    bullish_trades = [p for p in completed_trades if p["trade_setup"]["direction"] == "BULLISH"]
    bearish_trades = [p for p in completed_trades if p["trade_setup"]["direction"] == "BEARISH"]

    # Current (forward-looking) trade setup
    current_period = next(
        (p for p in all_periods if p.get("is_current") and p.get("trade_setup")), None
    )

    return {
        "ticker":          ticker,
        "cap_tier":        cap_tier,
        "sector":          sector,
        "periods":         all_periods,
        "ticker_summary": {
            "total_periods":         len(all_periods),
            "swing_trades_generated": len([p for p in all_periods if p.get("trade_setup")]),
            "completed_trades":       len(completed_trades),
            "n_correct":              n_correct,
            "accuracy_pct":           accuracy,
            "bullish_trades":         len(bullish_trades),
            "bearish_trades":         len(bearish_trades),
            "error_periods":          len([p for p in all_periods if p.get("error")]),
        },
        "current_setup": current_period.get("trade_setup") if current_period else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def _build_windows() -> List[Tuple[date, date]]:
    """Return historical windows + current-date forward window."""
    windows = list(HISTORICAL_WINDOWS)
    windows.append((CURRENT_SIGNAL_DATE, CURRENT_RESULT_DATE))
    return windows


def _select_tickers(args) -> List[Dict]:
    """Resolve ticker list from CLI args or master data."""
    if args.tickers:
        # User-supplied list — no cap_tier info available
        return [
            {"ticker": t.strip().upper(), "cap_tier": "unknown", "sector": "Unknown"}
            for t in args.tickers.split(",")
            if t.strip()
        ]
    return _load_default_tickers(n_large=4, n_mid=3, n_small=3)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Swing-trade backtest with cutoff Jan 1 2026 — Polygon only.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tickers", type=str, default="",
        help="Comma-separated ticker list. Default: 10 mixed-cap from halal master.",
    )
    parser.add_argument(
        "--no-matrix", action="store_true",
        help="Skip confusion-matrix computation (faster run).",
    )
    parser.add_argument(
        "--workers", type=int, default=MAX_WORKERS,
        help=f"Parallel ticker workers (default {MAX_WORKERS}; max recommended 4).",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print each period as it runs.",
    )
    args = parser.parse_args()

    _abort_if_no_polygon()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tickers  = _select_tickers(args)
    windows  = _build_windows()
    n_hist   = len(HISTORICAL_WINDOWS)

    print("\n" + "═" * 64)
    print("  SWING TRADE BACKTEST  —  cutoff Jan 1 2026")
    print("═" * 64)
    print(f"  Tickers         : {len(tickers)}  ({', '.join(t['ticker'] for t in tickers)})")
    print(f"  Historical winds: {n_hist}  (Jan–Mar 2026 monthly)")
    print(f"  Current signal  : {CURRENT_SIGNAL_DATE.isoformat()}  [forward prediction]")
    print(f"  Swing filter    : {SWING_MIN_DAYS} – {SWING_MAX_DAYS} days")
    print(f"  Workers         : {args.workers}")
    print(f"  Output dir      : {OUTPUT_DIR}")
    print("═" * 64 + "\n")

    # ── Run all tickers in parallel ───────────────────────────────────
    ticker_results: List[Dict] = []
    worker_fn = lambda tm: _run_ticker(tm, windows, verbose=args.verbose)

    if args.workers == 1:
        for tm in tickers:
            print(f"Running {tm['ticker']} ({tm['cap_tier']}) …")
            ticker_results.append(worker_fn(tm))
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(worker_fn, tm): tm for tm in tickers}
            for fut in as_completed(futures):
                tm = futures[fut]
                try:
                    result = fut.result()
                    ticker_results.append(result)
                    acc_str = (
                        f"  acc={result['ticker_summary']['accuracy_pct']}%"
                        if result["ticker_summary"]["accuracy_pct"] is not None
                        else "  acc=n/a"
                    )
                    print(
                        f"  ✓  {tm['ticker']:<6} {tm['cap_tier']:<6}"
                        f"  trades={result['ticker_summary']['swing_trades_generated']}"
                        f"{acc_str}"
                    )
                except Exception as exc:
                    print(f"  ✗  {tm['ticker']:<6}  ERROR: {exc}")
                    ticker_results.append({"ticker": tm["ticker"], "error": str(exc)})

    # ── Collect all periods for confusion matrix ──────────────────────
    all_periods_flat: List[Dict] = []
    for tr in ticker_results:
        for period in tr.get("periods", []):
            # Skip the current (forward) window from the matrix
            if not period.get("is_current", False):
                all_periods_flat.append(period)

    confusion_matrix: Optional[Dict] = None
    if not args.no_matrix:
        confusion_matrix = _build_confusion_matrix(all_periods_flat)

    # ── Trade candidates (current forward-looking setups) ─────────────
    trade_candidates: List[Dict] = []
    for tr in ticker_results:
        cs = tr.get("current_setup")
        if cs:
            trade_candidates.append({
                "ticker":     tr["ticker"],
                "cap_tier":   tr["cap_tier"],
                "sector":     tr["sector"],
                **cs,
            })

    # Sort by conviction: aligned + high confidence first
    def _sort_key(cand: Dict) -> Tuple:
        tf = cand.get("timeframe_alignment", "daily_only")
        cb = cand.get("confidence_band", "low")
        tf_score = {"aligned": 0, "weekly_neutral": 1, "daily_only": 2, "conflict": 3}.get(tf, 4)
        cb_score = {"high": 0, "medium": 1, "low": 2}.get(cb, 3)
        return (tf_score, cb_score, -cand.get("boosted_confidence_pct", 0))

    trade_candidates.sort(key=_sort_key)

    # ── Aggregate stats ───────────────────────────────────────────────
    all_completed = [
        p for tr in ticker_results
        for p in tr.get("periods", [])
        if not p.get("is_current")
           and p.get("trade_setup")
           and isinstance(p.get("actual_outcome"), dict)
           and "signal_correct" in p["actual_outcome"]
    ]
    n_total_correct = sum(1 for p in all_completed if p["actual_outcome"]["signal_correct"])
    overall_acc = (
        round(n_total_correct / len(all_completed) * 100.0, 1)
        if all_completed else None
    )

    # ── Assemble JSON ─────────────────────────────────────────────────
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_payload: Dict[str, Any] = {
        "meta": {
            "run_timestamp":        datetime.now().isoformat(),
            "cutoff_date":          CUTOFF_DATE.isoformat(),
            "first_signal_date":    HISTORICAL_WINDOWS[0][0].isoformat(),
            "current_signal_date":  CURRENT_SIGNAL_DATE.isoformat(),
            "tickers":              [t["ticker"] for t in tickers],
            "ticker_universe":      f"{len(tickers)} tickers (4 large + 3 mid + 3 small from Halal master)",
            "signal_windows":       [
                {"signal_date": s.isoformat(), "result_date": r.isoformat()}
                for s, r in windows
            ],
            "swing_min_days":       SWING_MIN_DAYS,
            "swing_max_days":       SWING_MAX_DAYS,
            "data_source":          "Polygon.io (primary — no yfinance fallback)",
            "timeframes":           ["daily", "weekly"],
            "atr_target_mult":      ATR_TARGET_MULT,
            "atr_stop_mult":        ATR_STOP_MULT,
        },
        "aggregate_summary": {
            "total_tickers":          len(ticker_results),
            "total_periods_run":      sum(len(tr.get("periods", [])) for tr in ticker_results),
            "total_swing_trades":     sum(
                tr.get("ticker_summary", {}).get("swing_trades_generated", 0)
                for tr in ticker_results
            ),
            "total_completed_trades": len(all_completed),
            "overall_accuracy_pct":   overall_acc,
            "trade_candidates_today": len(trade_candidates),
        },
        "confusion_matrix":  confusion_matrix,
        "trade_candidates":  trade_candidates,
        "tickers":           {tr["ticker"]: tr for tr in ticker_results},
    }

    # ── Write JSON ────────────────────────────────────────────────────
    ts_path     = OUTPUT_DIR / f"swing_backtest_{ts_str}.json"
    latest_path = OUTPUT_DIR / "swing_backtest_latest.json"

    with open(ts_path, "w") as fh:
        json.dump(output_payload, fh, indent=2, default=str)
    with open(latest_path, "w") as fh:
        json.dump(output_payload, fh, indent=2, default=str)

    # ── Console summary ───────────────────────────────────────────────
    print("\n" + "─" * 64)
    print("  RESULTS SUMMARY")
    print("─" * 64)
    agg = output_payload["aggregate_summary"]
    print(f"  Tickers run         : {agg['total_tickers']}")
    print(f"  Periods evaluated   : {agg['total_periods_run']}")
    print(f"  Swing trades found  : {agg['total_swing_trades']}")
    print(f"  Completed trades    : {agg['total_completed_trades']}")
    if overall_acc is not None:
        print(f"  Overall accuracy    : {overall_acc}%")

    if confusion_matrix:
        ov = confusion_matrix["overall"]
        print(f"\n  CONFUSION MATRIX  (BULLISH=positive class)")
        print(f"  ┌────────────────┬────────────┬────────────┐")
        print(f"  │                │ ACTUAL UP  │ ACTUAL DOWN│")
        print(f"  ├────────────────┼────────────┼────────────┤")
        print(f"  │ PRED BULLISH   │  TP={ov['TP']:<6}  │  FP={ov['FP']:<6}  │")
        print(f"  │ PRED BEARISH   │  FN={ov['FN']:<6}  │  TN={ov['TN']:<6}  │")
        print(f"  └────────────────┴────────────┴────────────┘")
        print(f"  Accuracy={ov['accuracy_pct']}%  Precision={ov['precision_pct']}%  "
              f"Recall={ov['recall_pct']}%  F1={ov['f1_score']}  MCC={ov['MCC']}")

    if trade_candidates:
        print(f"\n  CURRENT TRADE CANDIDATES  ({CURRENT_SIGNAL_DATE.isoformat()})")
        print(f"  {'TICKER':<6}  {'DIR':<8}  {'ENTRY':>7}  {'TARGET':>7}  "
              f"{'STOP':>7}  {'DAYS':>4}  {'CONF':>6}  TF-ALIGN")
        for cand in trade_candidates:
            print(
                f"  {cand['ticker']:<6}  {cand['direction']:<8}  "
                f"{cand['entry_price']:>7.2f}  {cand['target_price']:>7.2f}  "
                f"{cand['stop_loss']:>7.2f}  {cand['holding_days_est']:>4}d  "
                f"{cand['confidence_band']:>6}  {cand['timeframe_alignment']}"
            )

    print(f"\n  JSON → {ts_path}")
    print(f"  JSON → {latest_path}  (latest symlink)")
    print()


if __name__ == "__main__":
    main()
