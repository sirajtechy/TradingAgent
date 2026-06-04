"""Flat Base detector for the Phoenix Agent."""

from __future__ import annotations

from typing import List, Optional

from ..config import PhoenixSettings
from ..models import OHLCVBar, PatternMatch


def _detect_flat_base(
    bars: List[OHLCVBar],
    vol_avg_20: float,
    settings: PhoenixSettings,
) -> Optional[PatternMatch]:
    """
    Flat Base (Phoenix version - tighter than Technical Agent):
      - 20-120 bars of sideways consolidation
      - High-to-low range < 15% (Phoenix spec)
      - Volume CONTRACTING during base (last 10 bars < first 10 bars)
      - Breakout: close above base high AND volume >= 2x avg
    """
    min_bars = settings.flat_base_min_bars
    max_bars = settings.flat_base_max_bars
    max_range = settings.flat_base_max_range_pct
    vol_mult = settings.volume_breakout_multiple

    if len(bars) < min_bars + 2:
        return None

    # Scan different base lengths, pick the most recent qualifying one
    last_bar = bars[-1]
    last_close = last_bar.close
    last_vol = last_bar.volume

    best: Optional[PatternMatch] = None
    best_conf = -1.0

    for base_len in range(min_bars, min(max_bars, len(bars) - 1) + 1):
        base_bars = bars[-(base_len + 1):-1]  # exclude the current (potential breakout) bar
        if len(base_bars) < min_bars:
            continue

        base_high = max(b.high for b in base_bars)
        base_low = min(b.low for b in base_bars)
        if base_high <= 0:
            continue

        range_pct = (base_high - base_low) / base_high
        if range_pct > max_range:
            # Too wide - not a flat base
            continue

        # Volume contracting: last 10 bars of base < first 10 bars of base
        first10 = base_bars[:10]
        last10 = base_bars[-10:] if len(base_bars) >= 20 else base_bars[len(base_bars)//2:]
        first10_vol = sum(b.volume for b in first10) / len(first10) if first10 else 0
        last10_vol = sum(b.volume for b in last10) / len(last10) if last10 else 0
        vol_contracting = last10_vol < first10_vol if first10_vol > 0 else False

        # Breakout check
        pivot_price = base_high
        price_breakout = last_close > pivot_price
        vol_confirmed = vol_avg_20 > 0 and last_vol >= vol_avg_20 * vol_mult
        confirmed = price_breakout and vol_confirmed

        # Confidence
        range_score = max(0.0, (max_range - range_pct) / max_range) * 0.4
        vol_cont_score = 0.3 if vol_contracting else 0.0
        base_len_score = min(base_len / 60, 1.0) * 0.2  # longer base = stronger
        confirm_score = 0.1 if confirmed else 0.0
        confidence = range_score + vol_cont_score + base_len_score + confirm_score

        if confidence > best_conf:
            best_conf = confidence
            depth_pct = (base_high - base_low) / base_high
            best = PatternMatch(
                pattern_name="Flat Base",
                confirmed=confirmed,
                volume_confirmed=vol_confirmed,
                pivot_price=round(pivot_price, 4),
                confidence=round(confidence, 3),
                vcp_contractions=0,
                base_depth_pct=round(depth_pct, 4),
                description=(
                    f"Flat Base: {base_len} bars, range {range_pct*100:.1f}% "
                    f"(max {max_range*100:.0f}%), pivot ${pivot_price:.2f}; "
                    f"vol {'contracting' if vol_contracting else 'not contracting'}; "
                    f"{'CONFIRMED' if confirmed else 'not triggered'}"
                ),
            )

    return best
