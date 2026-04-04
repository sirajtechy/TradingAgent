"""
stage_analysis.py — Weinstein 4-stage market cycle classifier.

Uses the 30-week Simple Moving Average (SMA) and its slope, along with
price position relative to the MA, to classify the stock into one of four
stages defined by Stan Weinstein in "Secrets for Profiting in Bull and
Bear Markets".

Stage 1 — Basing / Accumulation
    Price meanders sideways below or around a flat/declining 30-week MA.
    Low volume, no clear trend.  Accumulation by institutions.
    → NEUTRAL: avoid until Stage 2 breakout.

Stage 2 — Uptrend (THE BUY ZONE)
    Price breaks above the 30-week MA, which itself begins rising.
    This is the ideal entry window O'Neil and Weinstein both advocate.
    → BULLISH: O'Neil bases form here.

Stage 3 — Distribution / Topping
    Price remains near highs but the 30-week MA flattens or starts to
    roll over.  Volume patterns show distribution.  Often produces late-
    stage bases with lower success rates.
    → CAUTION: higher-risk entry zone.

Stage 4 — Downtrend (AVOID)
    Price breaks below the declining 30-week MA.  Institutions selling.
    No O'Neil base qualifies here.
    → BEARISH: stay out / short setups only.
"""

from __future__ import annotations

from typing import List, Optional

from .models import StageResult, WeeklyBar


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _slope(current: Optional[float], prior: Optional[float]) -> str:
    """Determine MA slope based on current vs prior value."""
    if current is None or prior is None:
        return "flat"
    delta_pct = (current - prior) / abs(prior) * 100 if prior != 0 else 0
    if delta_pct > 0.5:
        return "rising"
    if delta_pct < -0.5:
        return "falling"
    return "flat"


def _sma(values: List[float], period: int) -> List[Optional[float]]:
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


# ─────────────────────────────────────────────────────────────────────────────
# Stage classifier
# ─────────────────────────────────────────────────────────────────────────────

def classify_stage(bars: List[WeeklyBar]) -> StageResult:
    """
    Classify the current market stage for the given weekly bar history.

    Requires at least 35 weekly bars (30 for SMA + 5 for slope context).
    Returns a best-effort result if data is insufficient.
    """
    if len(bars) < 35:
        return StageResult(
            stage=1,
            description="Stage 1 — Insufficient data for stageclassification",
            sma_30w=None,
            ma_slope="flat",
            price_vs_ma="below",
        )

    closes = [b.close for b in bars]
    sma30  = _sma(closes, 30)

    # Current and prior values
    current_close: float = closes[-1]
    sma_current: Optional[float] = None
    sma_10w_ago: Optional[float] = None

    # Most recent SMA value
    for v in reversed(sma30):
        if v is not None:
            sma_current = v
            break

    # SMA value 10 bars ago (for slope)
    valid = [(i, v) for i, v in enumerate(sma30) if v is not None]
    if len(valid) >= 11:
        sma_10w_ago = valid[-11][1]
    elif valid:
        sma_10w_ago = valid[0][1]

    ma_slope = _slope(sma_current, sma_10w_ago)
    price_vs_ma = "above" if (sma_current is not None and current_close > sma_current) else "below"

    # ── Classification logic ──────────────────────────────────────────────
    if price_vs_ma == "above" and ma_slope == "rising":
        stage = 2
        description = "Stage 2 — Uptrend: price above rising 30wMA (BUY ZONE)"

    elif price_vs_ma == "above" and ma_slope in ("flat", "falling"):
        stage = 3
        description = "Stage 3 — Distribution: price near highs, 30wMA flattening (CAUTION)"

    elif price_vs_ma == "below" and ma_slope == "falling":
        stage = 4
        description = "Stage 4 — Downtrend: price below declining 30wMA (AVOID)"

    elif price_vs_ma == "below" and ma_slope in ("flat", "rising"):
        # Potentially transitioning from Stage 4 → Stage 1 → Stage 2
        # Price still below MA but MA is no longer falling → Stage 1
        stage = 1
        description = "Stage 1 — Basing: price below 30wMA, MA flattening (accumulation phase)"

    else:
        # Flat price, flat MA → Stage 1 by default
        stage = 1
        description = "Stage 1 — Basing: sideways consolidation near 30wMA"

    return StageResult(
        stage=stage,
        description=description,
        sma_30w=round(sma_current, 4) if sma_current else None,
        ma_slope=ma_slope,
        price_vs_ma=price_vs_ma,
    )
