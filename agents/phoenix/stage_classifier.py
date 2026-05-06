"""
stage_classifier.py — Daily-bar Stage 1/2/3/4 classifier for the Phoenix Agent.

Phoenix Trader stage logic uses SMA10, SMA20, SMA50, and SMA200 on DAILY bars
(unlike the O'Neil agent which uses the 30-week SMA on weekly bars).

Stage definitions
─────────────────
  Stage 2 — Momentum (THE ONLY TRADEABLE STAGE):
    ALL of the following must be true:
      1. price > SMA20 > SMA50 > SMA200   (full bull alignment)
      2. SMA20 slope = rising (current > prior by > 0.3%)
      3. SMA200 slope = rising OR flat (not falling)
      4. Volume trend = expanding (recent 10-bar avg > prior 10-bar avg)

  Stage 4 — Decline (AVOID):
    ANY of the following is sufficient:
      1. price < SMA200
      2. SMA200 slope = falling

  Stage 3 — Exhaustion (REDUCE):
    Between 2 and 4:
      1. price > SMA200 but SMA20 flattening or declining
      2. Wide & loose price action (ATR expanding)

  Stage 1 — Accumulation (WATCH):
    Everything else (below SMA200 but not yet Stage 4 decline).

Public API
──────────
  classify_stage(snapshot, settings) → StageResult
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .config import PhoenixSettings
from .models import PhoenixSnapshot, StageResult


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _slope_label(current: Optional[float], prior: Optional[float], threshold_pct: float = 0.3) -> str:
    """Classify SMA slope as 'rising', 'flat', or 'falling'."""
    if current is None or prior is None or prior == 0:
        return "flat"
    delta_pct = (current - prior) / abs(prior) * 100
    if delta_pct > threshold_pct:
        return "rising"
    if delta_pct < -threshold_pct:
        return "falling"
    return "flat"


def _vol_10bar_avg(bars, offset: int = 0) -> Optional[float]:
    """Compute 10-bar average volume starting `offset` bars from the end."""
    end = len(bars) - offset
    start = end - 10
    if start < 0:
        return None
    window = bars[start:end]
    if not window:
        return None
    return sum(b.volume for b in window) / len(window)


def _atr_avg(bars, period: int = 10) -> Optional[float]:
    """Simple ATR (True Range average) for the last `period` bars."""
    if len(bars) < period + 1:
        return None
    trs = []
    for i in range(len(bars) - period, len(bars)):
        prev_close = bars[i - 1].close
        tr = max(
            bars[i].high - bars[i].low,
            abs(bars[i].high - prev_close),
            abs(bars[i].low - prev_close),
        )
        trs.append(tr)
    return sum(trs) / len(trs)


# ─────────────────────────────────────────────────────────────────────────────
# Public classifier
# ─────────────────────────────────────────────────────────────────────────────

def classify_stage(
    snapshot: PhoenixSnapshot,
    settings: Optional[PhoenixSettings] = None,
) -> StageResult:
    """
    Classify the current market stage for the ticker in *snapshot*.

    Parameters
    ----------
    snapshot:  PhoenixSnapshot from the data client (must have ≥210 bars).
    settings:  PhoenixSettings; uses defaults if None.

    Returns
    -------
    StageResult with stage (1–4), label, action, MA alignment flag,
    MA slopes dict, and human-readable notes.
    """
    if settings is None:
        settings = PhoenixSettings()

    smas = snapshot.smas
    price = snapshot.as_of_price
    bars = snapshot.bars
    threshold = settings.ma_slope_threshold_pct

    # ── Compute slopes ────────────────────────────────────────────────────
    sma20_slope  = _slope_label(smas.sma20,  smas.sma20_prior,  threshold)
    sma50_slope  = _slope_label(smas.sma50,  smas.sma50_prior,  threshold)
    sma200_slope = _slope_label(smas.sma200, smas.sma200_prior, threshold)
    sma10_slope  = _slope_label(smas.sma10,  smas.sma10_prior,  threshold)

    ma_slopes: Dict[str, str] = {
        "sma10":  sma10_slope,
        "sma20":  sma20_slope,
        "sma50":  sma50_slope,
        "sma200": sma200_slope,
    }

    # ── MA alignment check ────────────────────────────────────────────────
    ma_alignment = (
        smas.sma20 is not None
        and smas.sma50 is not None
        and smas.sma200 is not None
        and price > smas.sma20 > smas.sma50 > smas.sma200
    )

    notes: List[str] = []

    # Append SMA distance notes
    if smas.sma200 is not None:
        pct = (price - smas.sma200) / smas.sma200 * 100
        above = "above" if pct >= 0 else "below"
        notes.append(f"Price is {abs(pct):.1f}% {above} SMA200 (${smas.sma200:.2f})")

    if smas.sma20 is not None:
        pct = (price - smas.sma20) / smas.sma20 * 100
        above = "above" if pct >= 0 else "below"
        notes.append(f"Price is {abs(pct):.1f}% {above} SMA20 (${smas.sma20:.2f})")

    notes.append(
        f"SMA slopes → SMA10: {sma10_slope}, SMA20: {sma20_slope}, "
        f"SMA50: {sma50_slope}, SMA200: {sma200_slope}"
    )

    # ── Volume trend ──────────────────────────────────────────────────────
    recent_vol_avg = _vol_10bar_avg(bars, offset=0)   # last 10 bars
    prior_vol_avg  = _vol_10bar_avg(bars, offset=10)  # bars 11–20 ago
    vol_expanding = (
        recent_vol_avg is not None
        and prior_vol_avg is not None
        and recent_vol_avg > prior_vol_avg
    )
    if recent_vol_avg and prior_vol_avg:
        pct_chg = (recent_vol_avg - prior_vol_avg) / prior_vol_avg * 100
        direction = "expanding" if vol_expanding else "contracting"
        notes.append(f"Volume trend: {direction} ({pct_chg:+.1f}% vs prior 10 bars)")

    # ── ATR expansion check (used for Stage 3 wide-&-loose) ──────────────
    recent_atr = _atr_avg(bars, period=10)
    base_atr   = _atr_avg(bars[-60:-10] if len(bars) >= 70 else bars, period=min(10, len(bars) - 1))
    atr_expanding = (
        recent_atr is not None
        and base_atr is not None
        and base_atr > 0
        and recent_atr > base_atr * 1.25  # 25% wider than base ATR
    )

    # ─────────────────────────────────────────────────────────────────────
    # Stage 4 — AVOID (checked first — most dangerous)
    # ─────────────────────────────────────────────────────────────────────
    if smas.sma200 is not None and (price < smas.sma200 or sma200_slope == "falling"):
        triggers = []
        if price < smas.sma200:
            triggers.append(f"price (${price:.2f}) < SMA200 (${smas.sma200:.2f})")
        if sma200_slope == "falling":
            triggers.append("SMA200 slope is falling")
        notes.insert(0, f"Stage 4 trigger(s): {'; '.join(triggers)}")
        return StageResult(
            stage=4,
            label="Decline",
            action="AVOID",
            ma_alignment=ma_alignment,
            ma_slopes=ma_slopes,
            notes=notes,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Stage 2 — TRADE (all criteria must pass)
    # ─────────────────────────────────────────────────────────────────────
    stage2_criteria = {
        "ma_alignment":    ma_alignment,
        "sma20_rising":    sma20_slope == "rising",
        "sma200_not_fall": sma200_slope in ("rising", "flat"),
        "vol_expanding":   vol_expanding,
    }
    if all(stage2_criteria.values()):
        notes.insert(0, "Stage 2: all criteria met — full bull alignment + rising SMA20 + volume expanding")
        return StageResult(
            stage=2,
            label="Momentum",
            action="TRADE",
            ma_alignment=ma_alignment,
            ma_slopes=ma_slopes,
            notes=notes,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Borderline Stage 2 — strong but missing one criterion
    # (e.g. vol not yet expanding, or SMA20 just barely flat)
    # ─────────────────────────────────────────────────────────────────────
    strong_criteria_count = sum([
        ma_alignment,
        sma20_slope == "rising",
        sma200_slope in ("rising", "flat"),
    ])

    # ─────────────────────────────────────────────────────────────────────
    # Stage 3 — REDUCE (price above SMA200, but losing momentum)
    # ─────────────────────────────────────────────────────────────────────
    price_above_200 = smas.sma200 is not None and price > smas.sma200
    sma20_weak = sma20_slope in ("flat", "falling")

    if price_above_200 and sma20_weak:
        reason = []
        if sma20_slope == "flat":
            reason.append("SMA20 flattening")
        if sma20_slope == "falling":
            reason.append("SMA20 declining")
        if atr_expanding:
            reason.append("ATR expanding (wide & loose price action)")
        if not ma_alignment:
            reason.append("MA alignment broken")
        notes.insert(0, f"Stage 3: price above SMA200 but momentum fading — {', '.join(reason)}")
        return StageResult(
            stage=3,
            label="Exhaustion",
            action="REDUCE",
            ma_alignment=ma_alignment,
            ma_slopes=ma_slopes,
            notes=notes,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Stage 1 — WATCH (everything else — basing / accumulation)
    # ─────────────────────────────────────────────────────────────────────
    reason = []
    if not ma_alignment:
        reason.append("MA alignment not yet established")
    if not vol_expanding:
        reason.append("volume not yet expanding")
    if strong_criteria_count >= 2:
        reason.append("borderline — approaching Stage 2")
    notes.insert(0, f"Stage 1: basing/accumulation — {', '.join(reason) if reason else 'sideways consolidation'}")
    return StageResult(
        stage=1,
        label="Accumulation",
        action="WATCH",
        ma_alignment=ma_alignment,
        ma_slopes=ma_slopes,
        notes=notes,
    )
