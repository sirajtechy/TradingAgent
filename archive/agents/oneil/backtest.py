"""
backtest.py — Monthly rolling backtest engine for the O'Neil Technical Analysis Agent.

Design principle
────────────────
Fetch ALL OHLCV bars for a ticker ONCE (covering the full 3-year window),
then for each (signal_date, result_date) pair:

  1. Slice the full bar series to bars on or before *signal_date*
     (point-in-time: the agent cannot see the future).
  2. Run the full O'Neil pipeline on the sliced bars:
       compute_weekly → detect_patterns → classify_stage → rules.evaluate
  3. Map ONeilSignal.direction (BULLISH/BEARISH/NEUTRAL) to a predicted
     price direction (up / down / abstain).
  4. Fetch the month-end closing price as of *result_date*.
  5. Compare predicted vs actual direction → signal_correct True/False/None.

Data source priority
────────────────────
  1. Polygon.io — primary source of truth for all OHLCV / close price data.
  2. yfinance   — emergency fallback.
"""

from __future__ import annotations

import logging
import time
import warnings
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import yfinance as yf

from agents.polygon_data import PolygonClient, PolygonDataError
from .data_client import ONeilDataClient, DataError
from .indicators import compute_weekly, compute_daily_ema200
from .models import ONeilRequest, ONeilSignal, WeeklyBar, DailyBar
from .patterns import detect_all_patterns
from .rules import evaluate
from .stage_analysis import classify_stage

logger = logging.getLogger(__name__)
_polygon = PolygonClient()

try:
    from .polygon_client import PolygonONeilClient, PolygonDataError
    _POLYGON_AVAILABLE = True
except ImportError:
    _POLYGON_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Signal → direction mapping
# ─────────────────────────────────────────────────────────────────────────────

_DIRECTION_TO_PREDICTION = {
    "BULLISH": "up",
    "BEARISH": "down",
    "NEUTRAL": None,   # abstain — not counted in confusion matrix
}


# ─────────────────────────────────────────────────────────────────────────────
# End-price fetcher (month-end close price via yfinance)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_end_price(ticker: str, result_date: date) -> Optional[Tuple[float, str]]:
    """
    Fetch the closing price on or just before *result_date*.

    Returns (price, actual_date_str) or None on failure.
    Polygon primary, yfinance fallback.
    """
    # ── Polygon primary ──────────────────────────────────────────────────
    if _polygon.is_available():
        try:
            result = _polygon.get_close_price(ticker, result_date)
            if result is not None:
                price, bar_date = result
                return price, bar_date.isoformat()
        except PolygonDataError as exc:
            logger.warning("Polygon end-price failed for %s: %s", ticker, exc)

    # ── yfinance fallback ────────────────────────────────────────────────
    start = result_date - timedelta(days=7)
    end   = result_date + timedelta(days=1)
    try:
        df = yf.Ticker(ticker).history(
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=True,
        )
        if df is None or df.empty:
            return None
        price = float(df["Close"].iloc[-1])
        ts    = df.index[-1]
        actual_date = ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10]
        return price, actual_date
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Core pipeline — run on pre-fetched, sliced bars
# ─────────────────────────────────────────────────────────────────────────────

def _analyze_from_bars(
    request: ONeilRequest,
    weekly_bars: List[WeeklyBar],
    daily_bars: List[DailyBar],
) -> ONeilSignal:
    """
    Run the full O'Neil analysis pipeline directly on pre-fetched bars.
    Bypasses the data-fetch graph node — used exclusively by the backtest.
    """
    inds     = compute_weekly(weekly_bars)
    ema200   = compute_daily_ema200(daily_bars)
    patterns = detect_all_patterns(weekly_bars)
    stage    = classify_stage(weekly_bars)
    last_close = weekly_bars[-1].close if weekly_bars else 0.0

    return evaluate(
        request=request,
        weekly_inds=inds,
        daily_ema200=ema200,
        patterns=patterns,
        stage=stage,
        last_close=last_close,
        warnings=[],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Bar fetcher (Polygon first, yfinance fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_full_bars(
    ticker: str,
    earliest_date: date,
    exchange: str = "US",
) -> Tuple[List[WeeklyBar], List[DailyBar]]:
    """
    Fetch the widest possible bar history to cover all backtest periods.

    We need at least:
      - 3 years of weekly bars (for patterns + stage on the earliest signal_date)
      - 2 years of daily bars  (for EMA-200d)

    The actual fetch uses a window relative to today so we get ALL history.
    """
    # Build a synthetic request anchored to today for the fetch
    from datetime import date as _date
    fetch_request = ONeilRequest(
        ticker=ticker,
        as_of_date=_date.today(),
        exchange=exchange,
    )

    # Try Polygon for US tickers
    if _POLYGON_AVAILABLE and exchange.upper() == "US":
        try:
            client = PolygonONeilClient()
            if client.is_available():
                weekly, daily, _ = client.fetch_bars(fetch_request)
                if len(weekly) >= 30:
                    return weekly, daily
        except Exception:
            pass

    # yfinance fallback
    yf_client = ONeilDataClient()
    weekly, daily, _ = yf_client.fetch(fetch_request)
    return weekly, daily


# ─────────────────────────────────────────────────────────────────────────────
# Period runner
# ─────────────────────────────────────────────────────────────────────────────

def _run_period(
    ticker: str,
    signal_date: date,
    result_date: date,
    all_weekly: List[WeeklyBar],
    all_daily: List[DailyBar],
    exchange: str = "US",
) -> Dict[str, Any]:
    """Evaluate a single (signal_date → result_date) period."""

    month_label = signal_date.strftime("%B %Y")

    # ── Slice bars to point-in-time ──────────────────────────────────────
    weekly_slice = [b for b in all_weekly if b.bar_date <= signal_date]
    daily_slice  = [b for b in all_daily  if b.bar_date <= signal_date]

    if len(weekly_slice) < 5:
        return {
            "month":         month_label,
            "signal_date":   signal_date.isoformat(),
            "result_date":   result_date.isoformat(),
            "error":         f"Insufficient weekly bars as of {signal_date}: {len(weekly_slice)}",
            "signal":        "unknown",
            "signal_correct": None,
        }

    # ── Run O'Neil pipeline ──────────────────────────────────────────────
    try:
        request = ONeilRequest(ticker=ticker, as_of_date=signal_date, exchange=exchange)
        sig = _analyze_from_bars(request, weekly_slice, daily_slice)
    except Exception as exc:
        return {
            "month":         month_label,
            "signal_date":   signal_date.isoformat(),
            "result_date":   result_date.isoformat(),
            "error":         f"Analysis failed: {exc}",
            "signal":        "unknown",
            "signal_correct": None,
        }

    start_price = sig.last_close
    prediction  = _DIRECTION_TO_PREDICTION.get(sig.direction)

    # ── Fetch end price ──────────────────────────────────────────────────
    end_result = _fetch_end_price(ticker, result_date)
    if end_result is None:
        return {
            "month":               month_label,
            "signal_date":         signal_date.isoformat(),
            "result_date":         result_date.isoformat(),
            "start_price":         round(start_price, 4),
            "error":               "End-price fetch failed",
            "signal":              sig.direction.lower(),
            "signal_correct":      None,
            "pattern_detected":    sig.pattern_detected,
            "pattern_confidence":  sig.pattern_confidence,
            "is_late_stage":       sig.is_late_stage,
            "volume_dry_up":       sig.volume_dry_up,
            "market_stage":        sig.market_stage,
            "confluence_score":    sig.confluence_score,
            "entry_price":         sig.entry_price,
            "stop_loss":           sig.stop_loss,
            "risk_reward_ratio":   sig.risk_reward_ratio,
        }

    end_price, end_date = end_result
    price_return_pct = ((end_price - start_price) / start_price) * 100.0 if start_price else None
    actual_direction = "up" if (price_return_pct or 0) >= 0 else "down"

    if prediction == "up":
        correct = actual_direction == "up"
    elif prediction == "down":
        correct = actual_direction == "down"
    else:
        correct = None   # neutral/unknown → abstention

    return {
        "month":               month_label,
        "signal_date":         signal_date.isoformat(),
        "result_date":         result_date.isoformat(),
        "start_price":         round(start_price, 4),
        "end_price":           round(end_price, 4),
        "end_price_date":      end_date,
        "price_return_pct":    round(price_return_pct, 2) if price_return_pct is not None else None,
        "actual_direction":    actual_direction,
        "signal":              sig.direction.lower(),
        "signal_correct":      correct,
        # O'Neil-specific fields
        "pattern_detected":    sig.pattern_detected,
        "pattern_confidence":  round(sig.pattern_confidence, 3) if sig.pattern_confidence else None,
        "is_late_stage":       sig.is_late_stage,
        "volume_dry_up":       sig.volume_dry_up,
        "market_stage":        sig.market_stage,
        "confluence_score":    sig.confluence_score,
        "entry_price":         sig.entry_price,
        "stop_loss":           sig.stop_loss,
        "risk_reward_ratio":   sig.risk_reward_ratio,
        "rsi_14w":             round(sig.rsi_14w, 1) if sig.rsi_14w else None,
        "macd_histogram":      round(sig.macd_histogram, 4) if sig.macd_histogram else None,
        "summary":             sig.summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public backtest runner
# ─────────────────────────────────────────────────────────────────────────────

def run_monthly_backtest(
    ticker: str,
    months: List[Tuple[date, date]],
    exchange: str = "US",
) -> Dict[str, Any]:
    """
    Run a rolling monthly backtest for *ticker*.

    Parameters
    ----------
    ticker   : Stock symbol (e.g. "AAPL", "RELIANCE").
    months   : List of (signal_date, result_date) tuples.
    exchange : "US" or "NSE".

    Returns
    -------
    Dict with:
      - ticker, periods (list of period dicts), summary (accuracy + pattern stats)
    """
    earliest = months[0][0] if months else date.today()

    # Fetch bars ONCE for the full window
    try:
        all_weekly, all_daily = _fetch_full_bars(ticker, earliest, exchange)
    except DataError as exc:
        return {
            "ticker": ticker.upper(),
            "periods": [],
            "summary": {
                "error": str(exc),
                "total_periods": 0,
                "accuracy_pct": None,
            },
        }

    periods: List[Dict[str, Any]] = []
    for signal_date, result_date in months:
        time.sleep(0.1)   # small throttle for end-price yfinance calls
        period = _run_period(
            ticker=ticker,
            signal_date=signal_date,
            result_date=result_date,
            all_weekly=all_weekly,
            all_daily=all_daily,
            exchange=exchange,
        )
        periods.append(period)

    # ── Accuracy summary ─────────────────────────────────────────────────
    directional = [p for p in periods if p.get("signal_correct") is not None]
    correct     = sum(1 for p in directional if p["signal_correct"])
    accuracy    = (correct / len(directional) * 100.0) if directional else None

    # ── Pattern breakdown ────────────────────────────────────────────────
    pattern_stats: Dict[str, Dict[str, int]] = {}
    for p in periods:
        pat = p.get("pattern_detected")
        pat_key = pat.split("—")[0].strip() if pat else "No Pattern"
        if pat_key not in pattern_stats:
            pattern_stats[pat_key] = {"total": 0, "correct": 0, "directional": 0}
        s = pattern_stats[pat_key]
        s["total"] += 1
        if p.get("signal_correct") is not None:
            s["directional"] += 1
        if p.get("signal_correct"):
            s["correct"] += 1

    pattern_accuracy = {
        name: {
            **s,
            "accuracy_pct": round(s["correct"] / s["directional"] * 100, 1) if s["directional"] else None,
        }
        for name, s in pattern_stats.items()
    }

    # ── Stage breakdown ──────────────────────────────────────────────────
    stage_stats: Dict[int, Dict[str, int]] = {}
    for p in periods:
        st = p.get("market_stage", 0)
        if st not in stage_stats:
            stage_stats[st] = {"total": 0, "correct": 0, "directional": 0}
        s = stage_stats[st]
        s["total"] += 1
        if p.get("signal_correct") is not None:
            s["directional"] += 1
        if p.get("signal_correct"):
            s["correct"] += 1

    # ── Late-stage analysis ──────────────────────────────────────────────
    late   = [p for p in directional if p.get("is_late_stage")]
    early  = [p for p in directional if not p.get("is_late_stage") and p.get("pattern_detected")]
    late_acc  = round(sum(1 for p in late if p["signal_correct"]) / len(late) * 100, 1) if late else None
    early_acc = round(sum(1 for p in early if p["signal_correct"]) / len(early) * 100, 1) if early else None

    return {
        "ticker": ticker.upper(),
        "periods": periods,
        "summary": {
            "total_periods":       len(periods),
            "directional_signals": len(directional),
            "correct_signals":     correct,
            "accuracy_pct":        round(accuracy, 1) if accuracy is not None else None,
            "pattern_breakdown":   pattern_accuracy,
            "stage_breakdown":     {
                str(k): {**v, "accuracy_pct": round(v["correct"] / v["directional"] * 100, 1) if v["directional"] else None}
                for k, v in sorted(stage_stats.items())
            },
            "late_stage_accuracy_pct":  late_acc,
            "early_stage_accuracy_pct": early_acc,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Report formatter
# ─────────────────────────────────────────────────────────────────────────────

def build_backtest_report(backtest: Dict[str, Any]) -> str:
    """Format a backtest result dict as a plain-text report."""

    ticker = backtest["ticker"]
    s      = backtest["summary"]
    lines  = [
        f"{'─'*56}",
        f"  O'Neil CAN SLIM Backtest — {ticker}",
        f"{'─'*56}",
    ]

    if "error" in s:
        lines.append(f"  ERROR: {s['error']}")
        return "\n".join(lines)

    n      = s["total_periods"]
    d      = s["directional_signals"]
    acc    = s["accuracy_pct"]
    acc_s  = f"{acc:.1f}%" if acc is not None else "N/A"
    lines.append(f"  Periods : {n}   Directional: {d}/{n}   Accuracy: {acc_s}")
    lines.append("")

    # Pattern breakdown
    lines.append("  Pattern Breakdown:")
    for name, ps in s.get("pattern_breakdown", {}).items():
        pa = ps.get("accuracy_pct")
        lines.append(
            f"    {name:<30} dir={ps['directional']:>2}/{ps['total']:>2}  "
            f"acc={f'{pa:.1f}%' if pa is not None else 'N/A':>6}"
        )

    # Stage breakdown
    lines.append("")
    lines.append("  Stage Breakdown:")
    stage_labels = {1: "Stage 1 (Basing)", 2: "Stage 2 (Uptrend)", 3: "Stage 3 (Dist.)", 4: "Stage 4 (Decline)"}
    for st, ss in s.get("stage_breakdown", {}).items():
        sa = ss.get("accuracy_pct")
        lbl = stage_labels.get(int(st), f"Stage {st}")
        lines.append(
            f"    {lbl:<24} dir={ss['directional']:>2}/{ss['total']:>2}  "
            f"acc={f'{sa:.1f}%' if sa is not None else 'N/A':>6}"
        )

    # Late vs early
    late_acc  = s.get("late_stage_accuracy_pct")
    early_acc = s.get("early_stage_accuracy_pct")
    if late_acc is not None or early_acc is not None:
        lines += [
            "",
            f"  Early-stage accuracy : {f'{early_acc:.1f}%' if early_acc is not None else 'N/A'}",
            f"  Late-stage accuracy  : {f'{late_acc:.1f}%' if late_acc is not None else 'N/A'}",
        ]

    # Per-period summary
    lines += ["", "  Periods:"]
    for p in backtest.get("periods", []):
        corr = "✓" if p.get("signal_correct") else ("✗" if p.get("signal_correct") is False else "—")
        pat  = (p.get("pattern_detected") or "None")[:35]
        ret  = p.get("price_return_pct")
        ret_s = f"{ret:+.1f}%" if ret is not None else "N/A"
        lines.append(
            f"  {corr} {p['month']:<14}  sig={p.get('signal','?'):<8}  "
            f"ret={ret_s:>7}  stage={p.get('market_stage','?')}  pat={pat}"
        )

    return "\n".join(lines)
