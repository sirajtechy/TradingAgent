"""Pullback detector for the Phoenix Agent."""

from __future__ import annotations

from typing import List, Optional

from ..config import PhoenixSettings
from ..models import OHLCVBar, PatternMatch


def _detect_pullback(
    bars: List[OHLCVBar],
    vol_avg_20: float,
    sma10: Optional[float],
    sma20: Optional[float],
    settings: PhoenixSettings,
) -> Optional[PatternMatch]:
    """
    Pullback Entry:
      1. Prior breakout or 52w high within last 20 bars.
      2. Price within 2% of MA10 or MA20.
      3. Volume during pullback < 75% avg (healthy retrace).
      4. Last bar closed UP (bounce starting).
    """
    proximity = settings.pullback_proximity_pct
    prior_bars = settings.pullback_prior_breakout_bars
    dryup_thresh = settings.volume_dryup_threshold

    if len(bars) < prior_bars + 5:
        return None

    last_bar = bars[-1]
    last_close = last_bar.close
    last_vol = last_bar.volume
    prev_close = bars[-2].close if len(bars) >= 2 else last_close

    # Last bar must have closed up
    last_bar_up = last_close > prev_close

    # Check for prior breakout (52w high) within last `prior_bars` bars
    lookback_bars = bars[-prior_bars - 1:]
    all_time_high = max(b.high for b in bars)
    recent_high = max(b.high for b in lookback_bars[:-1])
    prior_breakout = recent_high >= all_time_high * 0.98  # within 2% of ATH

    if not prior_breakout:
        return None

    # Volume drying up in pullback (last 5 bars)
    pullback_bars = bars[-6:-1]
    pullback_vol_avg = sum(b.volume for b in pullback_bars) / len(pullback_bars) if pullback_bars else 0
    vol_drying = vol_avg_20 > 0 and pullback_vol_avg < vol_avg_20 * dryup_thresh

    # Check proximity to MA10 or MA20
    best: Optional[PatternMatch] = None
    best_conf = -1.0

    for ma_val, ma_name in [(sma10, "MA10"), (sma20, "MA20")]:
        if ma_val is None or ma_val <= 0:
            continue

        pct_from_ma = abs(last_close - ma_val) / ma_val
        if pct_from_ma > proximity:
            continue  # not close enough to MA

        # Confidence
        proximity_score = max(0.0, 1.0 - pct_from_ma / proximity) * 0.35
        vol_score = 0.30 if vol_drying else 0.10
        bounce_score = 0.20 if last_bar_up else 0.0
        breakout_score = 0.15  # prior breakout confirmed

        confidence = proximity_score + vol_score + bounce_score + breakout_score

        if confidence > best_conf:
            best_conf = confidence
            pivot_price = ma_val
            depth_pct = (recent_high - last_close) / recent_high if recent_high > 0 else 0
            best = PatternMatch(
                pattern_name="Pullback",
                confirmed=last_bar_up,
                volume_confirmed=vol_drying,
                pivot_price=round(pivot_price, 4),
                confidence=round(confidence, 3),
                vcp_contractions=0,
                base_depth_pct=round(depth_pct, 4),
                description=(
                    f"Pullback to {ma_name} (${ma_val:.2f}): "
                    f"price ${last_close:.2f} ({pct_from_ma*100:.1f}% away); "
                    f"vol {'drying' if vol_drying else 'elevated'}; "
                    f"last bar {'UP (bounce)' if last_bar_up else 'DOWN'}"
                ),
            )

    return best
