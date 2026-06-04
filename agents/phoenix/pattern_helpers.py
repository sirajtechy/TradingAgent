"""
Shared helper functions for Phoenix pattern detection.

These helpers are intentionally small and side-effect free so detector modules
can be split without changing the original pattern semantics.
"""

from __future__ import annotations

from typing import List, Optional

from .models import OHLCVBar, PatternMatch


def _vol_avg(bars: List[OHLCVBar], period: int = 20) -> float:
    """Rolling average volume over the last `period` bars."""
    window = bars[-period:] if len(bars) >= period else bars
    return sum(b.volume for b in window) / len(window) if window else 0.0


def _sma_series(values: List[float], period: int) -> List[Optional[float]]:
    n = len(values)
    result: List[Optional[float]] = [None] * n
    if period <= 0 or n < period:
        return result
    ws = sum(values[:period])
    result[period - 1] = ws / period
    for i in range(period, n):
        ws += values[i] - values[i - period]
        result[i] = ws / period
    return result


def _swing_high_idx(bars: List[OHLCVBar], lookback: int) -> int:
    """Index of the highest high within the last `lookback` bars."""
    window = bars[-lookback:]
    offset = len(bars) - lookback
    best_idx = 0
    best_val = window[0].high
    for i, b in enumerate(window):
        if b.high > best_val:
            best_val = b.high
            best_idx = i
    return offset + best_idx


def _trough_idx(bars: List[OHLCVBar], start: int, end: int) -> int:
    """Index of the lowest close between bars[start] and bars[end] (inclusive)."""
    best_idx = start
    best_val = bars[start].close
    for i in range(start + 1, min(end + 1, len(bars))):
        if bars[i].close < best_val:
            best_val = bars[i].close
            best_idx = i
    return best_idx


def _no_pattern(reason: str = "No qualifying pattern found") -> PatternMatch:
    return PatternMatch(
        pattern_name="None",
        confirmed=False,
        volume_confirmed=False,
        pivot_price=0.0,
        confidence=0.0,
        vcp_contractions=0,
        base_depth_pct=0.0,
        description=reason,
    )
