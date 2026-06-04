"""Tight Flag detector for the Phoenix Agent."""

from __future__ import annotations

from typing import List, Optional

from ..config import PhoenixSettings
from ..models import OHLCVBar, PatternMatch


def _detect_tight_flag(
    bars: List[OHLCVBar],
    vol_avg_20: float,
    settings: PhoenixSettings,
) -> Optional[PatternMatch]:
    """
    Tight Flag / Pocket Pivot (Phoenix version):
      - Flagpole: gain >= 8% in <= 15 bars
      - Flag: retrace <= 50% of pole in <= 20 bars
      - Volume: drying up during flag (< 75% avg)
      - Breakout: close above flag high AND volume >= 2x avg
    """
    pole_gain = settings.flag_pole_min_gain_pct / 100
    pole_max_bar = settings.flag_pole_max_bars
    max_retrace = settings.flag_max_retrace_pct
    flag_max_bar = settings.flag_max_bars
    dryup_thresh = settings.volume_dryup_threshold
    vol_mult = settings.volume_breakout_multiple

    if len(bars) < pole_max_bar + flag_max_bar + 2:
        return None

    last_bar = bars[-1]
    last_close = last_bar.close
    last_vol = last_bar.volume

    # Search for a flagpole that ends before the current bar
    best: Optional[PatternMatch] = None
    best_conf = -1.0

    for pole_end in range(len(bars) - 2, max(len(bars) - flag_max_bar - 2, pole_max_bar), -1):
        pole_top_price = bars[pole_end].high

        # Find pole base: lowest low within pole_max_bar before pole_end
        pole_start = max(0, pole_end - pole_max_bar)
        pole_base_price = min(bars[i].low for i in range(pole_start, pole_end + 1))
        if pole_base_price <= 0:
            continue

        pole_gain_actual = (pole_top_price - pole_base_price) / pole_base_price
        if pole_gain_actual < pole_gain:
            continue  # pole too small

        # Flag body: bars from pole_end to current (excluding current)
        flag_bars = bars[pole_end:len(bars) - 1]
        if len(flag_bars) < 3 or len(flag_bars) > flag_max_bar:
            continue

        flag_low = min(b.low for b in flag_bars)
        flag_high = max(b.high for b in flag_bars)
        pole_height = pole_top_price - pole_base_price

        retrace = (pole_top_price - flag_low) / pole_height if pole_height > 0 else 1.0
        if retrace > max_retrace:
            continue  # retraced too much - not tight

        # Volume dryup during flag
        flag_vol_avg = sum(b.volume for b in flag_bars) / len(flag_bars) if flag_bars else 0
        vol_drying = flag_vol_avg < vol_avg_20 * dryup_thresh if vol_avg_20 > 0 else False

        # Breakout check
        pivot_price = flag_high
        price_breakout = last_close > pivot_price
        vol_confirmed = vol_avg_20 > 0 and last_vol >= vol_avg_20 * vol_mult
        confirmed = price_breakout and vol_confirmed

        # Confidence
        pole_score = min(pole_gain_actual / 0.20, 1.0) * 0.3  # 20% pole = max score
        retrace_score = max(0.0, (max_retrace - retrace) / max_retrace) * 0.3
        dryup_score = 0.25 if vol_drying else 0.0
        confirm_score = 0.15 if confirmed else 0.0
        confidence = pole_score + retrace_score + dryup_score + confirm_score

        if confidence > best_conf:
            best_conf = confidence
            depth_pct = (pole_top_price - flag_low) / pole_top_price if pole_top_price > 0 else 0
            best = PatternMatch(
                pattern_name="Tight Flag",
                confirmed=confirmed,
                volume_confirmed=vol_confirmed,
                pivot_price=round(pivot_price, 4),
                confidence=round(confidence, 3),
                vcp_contractions=0,
                base_depth_pct=round(depth_pct, 4),
                description=(
                    f"Tight Flag: pole +{pole_gain_actual*100:.1f}% in "
                    f"{pole_end - pole_start} bars; "
                    f"retrace {retrace*100:.1f}% (max {max_retrace*100:.0f}%); "
                    f"vol {'drying up' if vol_drying else 'not drying'}; "
                    f"pivot ${pivot_price:.2f}; "
                    f"{'CONFIRMED' if confirmed else 'not triggered'}"
                ),
            )

    return best
