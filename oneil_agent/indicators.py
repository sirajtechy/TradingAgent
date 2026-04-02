"""
indicators.py — Pure-math technical indicators for the O'Neil agent.

All functions are deterministic and side-effect free.
Inputs are plain Python lists (oldest-first); outputs match input length
with ``None`` padding where insufficient data exists.

Indicators computed on WEEKLY bars:
    EMA(10), EMA(21), EMA(50)      — O'Neil's key moving averages
    SMA(30)                         — Weinstein stage moving average
    RSI(14)                         — momentum oscillator
    MACD(12, 26, 9)                 — trend + momentum

Indicators computed on DAILY bars:
    EMA(200)                        — primary trend filter (daily TF)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .models import DailyBar, WeeklyBar


# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0.0:
        return None
    return a / b


# ─────────────────────────────────────────────────────────────────────────────
# Moving averages
# ─────────────────────────────────────────────────────────────────────────────

def sma(values: List[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average. Returns list same length as *values*."""
    n = len(values)
    result: List[Optional[float]] = [None] * n
    if period <= 0 or n < period:
        return result
    window_sum = sum(values[:period])
    result[period - 1] = window_sum / period
    for i in range(period, n):
        window_sum += values[i] - values[i - period]
        result[i] = window_sum / period
    return result


def ema(values: List[float], period: int) -> List[Optional[float]]:
    """
    Exponential Moving Average seeded with the first-period SMA.
    Multiplier = 2 / (period + 1).
    """
    n = len(values)
    result: List[Optional[float]] = [None] * n
    if period <= 0 or n < period:
        return result
    multiplier = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    for i in range(period, n):
        result[i] = (values[i] - result[i - 1]) * multiplier + result[i - 1]  # type: ignore[operator]
    return result


# ─────────────────────────────────────────────────────────────────────────────
# RSI
# ─────────────────────────────────────────────────────────────────────────────

def rsi(values: List[float], period: int = 14) -> List[Optional[float]]:
    """
    Wilder's RSI.  Seed = simple average of first *period* gains/losses.
    Subsequent values use Wilder's smoothing (SMMA).
    """
    n = len(values)
    result: List[Optional[float]] = [None] * n
    if n <= period:
        return result

    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, n):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _rsi_val(ag: float, al: float) -> float:
        if al == 0.0:
            return 100.0
        rs = ag / al
        return 100.0 - 100.0 / (1.0 + rs)

    result[period] = _rsi_val(avg_gain, avg_loss)

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        result[i] = _rsi_val(avg_gain, avg_loss)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# MACD
# ─────────────────────────────────────────────────────────────────────────────

def macd(
    values: List[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> Dict[str, List[Optional[float]]]:
    """
    MACD = EMA(fast) − EMA(slow)
    Signal = EMA(9) of MACD line
    Histogram = MACD − Signal

    Returns dict with keys: "macd_line", "signal_line", "histogram"
    (all same length as *values*).
    """
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)

    n = len(values)
    macd_line: List[Optional[float]] = [None] * n
    for i in range(n):
        if fast_ema[i] is not None and slow_ema[i] is not None:
            macd_line[i] = fast_ema[i] - slow_ema[i]  # type: ignore[operator]

    # Signal = EMA(9) of MACD values (skip Nones)
    # We need to compute EMA only over not-None streak
    signal_line: List[Optional[float]] = [None] * n
    histogram: List[Optional[float]] = [None] * n

    # Extract non-None macd values and their indices
    valid_macd: List[Tuple[int, float]] = [
        (i, v) for i, v in enumerate(macd_line) if v is not None
    ]
    if len(valid_macd) >= signal_period:
        m_vals = [v for _, v in valid_macd]
        m_signal = ema(m_vals, signal_period)
        for j, (orig_i, _) in enumerate(valid_macd):
            if m_signal[j] is not None:
                signal_line[orig_i] = m_signal[j]
                histogram[orig_i] = macd_line[orig_i] - m_signal[j]  # type: ignore[operator]

    return {
        "macd_line":   macd_line,
        "signal_line": signal_line,
        "histogram":   histogram,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Volume ratio
# ─────────────────────────────────────────────────────────────────────────────

def volume_ratio(volumes: List[float], period: int = 10) -> List[Optional[float]]:
    """Current volume / N-period average volume."""
    n = len(volumes)
    result: List[Optional[float]] = [None] * n
    avgs = sma(volumes, period)
    for i in range(n):
        if avgs[i] is not None and avgs[i] != 0:
            result[i] = volumes[i] / avgs[i]  # type: ignore[operator]
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Composite weekly indicator computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_weekly(bars: List[WeeklyBar]) -> Dict[str, Optional[float]]:
    """
    Compute all weekly indicators from a list of WeeklyBar objects.

    Returns a flat dict of the LATEST (most recent bar) values only.
    All series are computed from the full bar list for warm-up accuracy.
    """
    if not bars:
        return {}

    closes  = [b.close for b in bars]
    volumes = [b.volume for b in bars]

    ema10  = ema(closes, 10)
    ema21  = ema(closes, 21)
    ema50  = ema(closes, 50)
    sma30  = sma(closes, 30)
    rsi14  = rsi(closes, 14)
    macd_d = macd(closes, 12, 26, 9)
    vol_r  = volume_ratio(volumes, 10)

    def _last(series: List[Optional[float]]) -> Optional[float]:
        for v in reversed(series):
            if v is not None:
                return v
        return None

    def _prev(series: List[Optional[float]], offset: int = 1) -> Optional[float]:
        count = 0
        for v in reversed(series):
            if v is not None:
                count += 1
                if count > offset:
                    return v
        return None

    # Check if MACD histogram is rising (last vs prev bar)
    hist_last = _last(macd_d["histogram"])
    hist_prev = _prev(macd_d["histogram"])

    return {
        "ema_10w":           _last(ema10),
        "ema_21w":           _last(ema21),
        "ema_50w":           _last(ema50),
        "sma_30w":           _last(sma30),
        "sma_30w_prev10":    _prev(sma30, 10),    # for slope
        "rsi_14w":           _last(rsi14),
        "rsi_14w_prev":      _prev(rsi14, 1),
        "macd_line":         _last(macd_d["macd_line"]),
        "macd_signal_line":  _last(macd_d["signal_line"]),
        "macd_histogram":    hist_last,
        "macd_histogram_prev": hist_prev,
        "volume_ratio_10w":  _last(vol_r),
        # Raw series — passed to stage_analysis and patterns
        "_ema10_series":     ema10,
        "_sma30_series":     sma30,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Daily EMA(200)
# ─────────────────────────────────────────────────────────────────────────────

def compute_daily_ema200(bars: List[DailyBar]) -> Optional[float]:
    """
    Compute the 200-day EMA from daily bars.
    Returns only the last (most recent) value.
    """
    if len(bars) < 200:
        return None
    closes = [b.close for b in bars]
    series = ema(closes, 200)
    for v in reversed(series):
        if v is not None:
            return v
    return None
