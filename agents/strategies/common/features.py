"""Shared deterministic feature helpers for strategy modules."""

from __future__ import annotations

from typing import List, Optional, Tuple

from agents.phoenix.models import OHLCVBar, PhoenixSnapshot


def sma_at(bars: List[OHLCVBar], period: int, offset: int = 0) -> Optional[float]:
    end = len(bars) - offset
    start = end - period
    if start < 0 or end <= 0:
        return None
    window = bars[start:end]
    if len(window) < period:
        return None
    return sum(b.close for b in window) / period


def ema_series(closes: List[float], period: int) -> List[Optional[float]]:
    if not closes or period <= 0:
        return [None] * len(closes)
    out: List[Optional[float]] = [None] * len(closes)
    k = 2.0 / (period + 1)
    ema: Optional[float] = None
    for i, c in enumerate(closes):
        if ema is None:
            if i + 1 >= period:
                ema = sum(closes[i + 1 - period : i + 1]) / period
                out[i] = ema
        else:
            ema = c * k + ema * (1 - k)
            out[i] = ema
    return out


def ema_at(bars: List[OHLCVBar], period: int, offset: int = 0) -> Optional[float]:
    closes = [b.close for b in bars]
    series = ema_series(closes, period)
    idx = len(series) - 1 - offset
    if idx < 0:
        return None
    return series[idx]


def slope_rising(current: Optional[float], prior: Optional[float], threshold_pct: float = 0.3) -> bool:
    if current is None or prior is None or prior == 0:
        return False
    return (current - prior) / abs(prior) * 100.0 > threshold_pct


def compute_rs_rank(
    ticker_bars: List[OHLCVBar],
    spy_bars: List[OHLCVBar],
    period: int = 63,
) -> Optional[float]:
    """Heuristic RS rank 0–100 vs SPY over ``period`` bars."""
    if len(ticker_bars) < period + 1 or len(spy_bars) < period + 1:
        return None
    t0 = ticker_bars[-period - 1].close
    t1 = ticker_bars[-1].close
    s0 = spy_bars[-period - 1].close
    s1 = spy_bars[-1].close
    if t0 <= 0 or s0 <= 0:
        return None
    t_ret = (t1 - t0) / t0 * 100.0
    s_ret = (s1 - s0) / s0 * 100.0
    rel = t_ret - s_ret
    rank = 50.0 + rel * 2.0
    return round(min(max(rank, 0.0), 100.0), 1)


def compute_rmv(bars: List[OHLCVBar], period: int = 15) -> Optional[float]:
    """
    Relative measure of volatility (RMV proxy).

    0 = tight/compressed, 100 = expanded. Moglen-style tightness score.
    """
    if len(bars) < period * 2:
        return None
    ranges: List[float] = []
    for b in bars:
        if b.close <= 0:
            continue
        ranges.append((b.high - b.low) / b.close * 100.0)
    if len(ranges) < period * 2:
        return None
    recent = sum(ranges[-period:]) / period
    baseline = sum(ranges[-period * 2 : -period]) / period
    if baseline <= 0:
        return None
    ratio = recent / baseline
    score = (ratio - 0.5) / 1.0 * 100.0
    return round(min(max(score, 0.0), 100.0), 1)


def compute_adr_pct(bars: List[OHLCVBar], period: int = 20) -> Optional[float]:
    if len(bars) < period:
        return None
    window = bars[-period:]
    pcts = [(b.high - b.low) / b.close * 100.0 for b in window if b.close > 0]
    if not pcts:
        return None
    return round(sum(pcts) / len(pcts), 2)


def daily_vwap_proxy(bars: List[OHLCVBar], period: int = 20) -> Optional[float]:
    """Rolling daily typical-price VWAP proxy (not true intraday VWAP)."""
    if len(bars) < period:
        return None
    window = bars[-period:]
    num = 0.0
    den = 0.0
    for b in window:
        tp = (b.high + b.low + b.close) / 3.0
        num += tp * b.volume
        den += b.volume
    if den <= 0:
        return None
    return num / den


def gap_pct(bars: List[OHLCVBar]) -> Optional[float]:
    if len(bars) < 2:
        return None
    prev = bars[-2].close
    if prev <= 0:
        return None
    return round((bars[-1].open - prev) / prev * 100.0, 2)


def is_rangebound(bars: List[OHLCVBar], lookback: int = 20, max_range_pct: float = 8.0) -> bool:
    if len(bars) < lookback:
        return False
    window = bars[-lookback:]
    hi = max(b.high for b in window)
    lo = min(b.low for b in window)
    mid = (hi + lo) / 2.0
    if mid <= 0:
        return False
    return (hi - lo) / mid * 100.0 <= max_range_pct


def ema_trend_grid(bars: List[OHLCVBar]) -> Tuple[int, int, dict]:
    """Return (up_count, total, grid dict) for 10/21/50/200 EMA/SMA style grid."""
    price = bars[-1].close
    e10 = ema_at(bars, 10)
    e21 = ema_at(bars, 21)
    s50 = sma_at(bars, 50)
    s200 = sma_at(bars, 200)
    grid = {
        "price": round(price, 2),
        "ema10": round(e10, 2) if e10 else None,
        "ema21": round(e21, 2) if e21 else None,
        "sma50": round(s50, 2) if s50 else None,
        "sma200": round(s200, 2) if s200 else None,
    }
    refs = [("ema10", e10), ("ema21", e21), ("sma50", s50), ("sma200", s200)]
    up = 0
    total = 0
    for key, val in refs:
        if val is None:
            grid[f"{key}_above"] = None
            continue
        total += 1
        above = price > val
        grid[f"{key}_above"] = above
        if above:
            up += 1
    return up, total, grid


def snapshot_bars(snapshot: Optional[PhoenixSnapshot]) -> List[OHLCVBar]:
    return list(snapshot.bars) if snapshot and snapshot.bars else []
