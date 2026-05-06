"""
backtest.py — Monthly backtest engine for the Phoenix Agent.

Logic mirrors the Technical and Fundamental agent backtest modules:
  1. Run analyze_ticker() as of *signal_date*.
  2. Fetch the actual closing price at *result_date* (typically 1 month later).
  3. Compare the Phoenix signal (BUY/WATCH/AVOID) against actual direction.
  4. Accumulate per-period results and compute summary statistics.

Signal → direction mapping:
    BUY   → bullish  (correct if price rose)
    WATCH → neutral  (excluded from directional accuracy)
    AVOID → bearish  (correct if price fell)

Public API
──────────
  run_monthly_backtest(ticker, months)       → Dict
  build_backtest_months(start, end)          → List[(signal_date, result_date)]
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .data_client import PhoenixDataClient
from .service import analyze_ticker

logger = logging.getLogger(__name__)

# Signal → directional prediction
_SIGNAL_TO_DIRECTION = {
    "BUY":   "bullish",
    "WATCH": "neutral",
    "AVOID": "bearish",
}

# Shared client for price lookups
_client: Optional[PhoenixDataClient] = None


def _get_client() -> PhoenixDataClient:
    global _client
    if _client is None:
        _client = PhoenixDataClient()
    return _client


# ─────────────────────────────────────────────────────────────────────────────
# Public functions
# ─────────────────────────────────────────────────────────────────────────────

def run_monthly_backtest(
    ticker: str,
    months: List[Tuple[date, date]],
    account_size: float = 100_000,
) -> Dict[str, Any]:
    """
    Run a monthly backtest for *ticker* across a list of (signal_date, result_date) pairs.

    Parameters
    ----------
    ticker:       Stock symbol (e.g. "NVDA").
    months:       List of (signal_date, result_date) tuples.
                  signal_date = date the signal is computed.
                  result_date = date the actual price is fetched for comparison.
    account_size: Account size for position sizing in each period.

    Returns
    -------
    Dict with keys:
        ticker, periods (list of per-period results), summary
    """
    periods: List[Dict[str, Any]] = []

    for signal_date, result_date in months:
        period = _run_period(ticker, signal_date, result_date, account_size)
        periods.append(period)

    # Summary stats
    directional = [p for p in periods if p["signal"] in ("BUY", "AVOID")]
    correct     = [p for p in directional if p.get("signal_correct")]
    buy_signals = [p for p in periods if p["signal"] == "BUY"]
    avg_rr      = (
        sum(p["reward_risk"] for p in buy_signals if p.get("reward_risk"))
        / len(buy_signals) if buy_signals else None
    )

    accuracy = (
        len(correct) / len(directional) * 100.0 if directional else None
    )

    n = len(periods)
    return {
        "ticker": ticker.upper(),
        "periods": periods,
        "summary": {
            "total_periods":        n,
            "buy_signals":          len(buy_signals),
            "watch_signals":        sum(1 for p in periods if p["signal"] == "WATCH"),
            "avoid_signals":        sum(1 for p in periods if p["signal"] == "AVOID"),
            "directional_signals":  len(directional),
            "correct_signals":      len(correct),
            "accuracy_pct":         round(accuracy, 1) if accuracy is not None else None,
            "avg_reward_risk":      round(avg_rr, 2) if avg_rr is not None else None,
            "warning": (
                f"This covers {n} month{'s' if n != 1 else ''} on one stock. "
                f"{n} data point{'s are' if n != 1 else ' is'} not statistically "
                "significant — use this to understand signal behaviour, not to validate it."
            ),
        },
    }


def build_backtest_months(
    start: date,
    end: date,
) -> List[Tuple[date, date]]:
    """
    Build a list of (signal_date, result_date) pairs spanning start→end.

    signal_date = first trading day of each month (approximated as the 2nd)
    result_date = last calendar day of that month (which Polygon snaps to the last trading day)
    """
    from calendar import monthrange

    months: List[Tuple[date, date]] = []
    current = date(start.year, start.month, 1)

    while current <= end:
        sig_date    = date(current.year, current.month, min(2, monthrange(current.year, current.month)[1]))
        last_day    = monthrange(current.year, current.month)[1]
        result_date = date(current.year, current.month, last_day)

        if result_date > end:
            break
        months.append((sig_date, result_date))

        # Advance one month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return months


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run_period(
    ticker: str,
    signal_date: date,
    result_date: date,
    account_size: float,
) -> Dict[str, Any]:
    """Run analysis for one period and compare against actual price move."""

    # Phoenix analysis at signal_date
    result = analyze_ticker(
        ticker=ticker,
        as_of_date=signal_date.isoformat(),
        account_size=account_size,
    )

    signal     = result.get("signal", "AVOID")
    score      = result.get("score", 0.0)
    pattern    = (result.get("pattern") or {}).get("pattern_name", "None")
    stage      = (result.get("stage") or {}).get("stage", 0)
    entry_px   = (result.get("entry") or {}).get("entry_price")
    stop_px    = (result.get("risk") or {}).get("stop_price")
    target_1   = (result.get("risk") or {}).get("target_1")
    rr         = (result.get("risk") or {}).get("reward_risk")
    hard_pass  = result.get("hard_filter_passed", False)

    # Fetch actual price at result_date
    signal_price = _get_price(ticker, signal_date)
    result_price = _get_price(ticker, result_date)

    actual_direction: Optional[str] = None
    pct_change: Optional[float] = None
    signal_correct: Optional[bool] = None

    if signal_price and result_price:
        pct_change = (result_price - signal_price) / signal_price * 100.0
        actual_direction = "bullish" if pct_change > 0 else "bearish"
        predicted = _SIGNAL_TO_DIRECTION.get(signal)
        if predicted in ("bullish", "bearish"):
            signal_correct = (predicted == actual_direction)

    return {
        "signal_date":       signal_date.isoformat(),
        "result_date":       result_date.isoformat(),
        "signal":            signal,
        "score":             score,
        "stage":             stage,
        "pattern":           pattern,
        "hard_filter_passed":hard_pass,
        "entry_price":       entry_px,
        "stop_price":        stop_px,
        "target_1":          target_1,
        "reward_risk":       rr,
        "signal_price":      round(signal_price, 4) if signal_price else None,
        "result_price":      round(result_price, 4) if result_price else None,
        "pct_change":        round(pct_change, 2) if pct_change is not None else None,
        "actual_direction":  actual_direction,
        "signal_correct":    signal_correct,
    }


def _get_price(ticker: str, target_date: date) -> Optional[float]:
    """Fetch closing price for ticker at or just before target_date."""
    client = _get_client()
    try:
        bars = client._fetch_bars(ticker, target_date, warnings=[])
        if bars:
            # Return the bar closest to target_date
            return bars[-1].close
    except Exception as exc:
        logger.debug("Price fetch failed for %s @ %s: %s", ticker, target_date, exc)
    return None
