"""Shakeout detector for the Phoenix Agent."""

from __future__ import annotations

from typing import List, Optional

from ..config import PhoenixSettings
from ..models import OHLCVBar, PatternMatch


def _detect_shakeout(
    bars: List[OHLCVBar],
    vol_avg_20: float,
    sma20: Optional[float],
    settings: PhoenixSettings,
) -> Optional[PatternMatch]:
    """
    Shakeout: false breakdown below support -> snap back.
      Support: MA20 or prior 20-bar base low.
      Dip below support: <= 3 bars, volume < avg (no real selling).
      Most recent close: above support (snap-back confirmed).
    """
    max_bars_below = settings.shakeout_max_bars_below
    lookback = settings.shakeout_lookback_bars
    dryup_thresh = settings.volume_dryup_threshold

    if len(bars) < lookback + 10:
        return None

    recent_bars = bars[-lookback:]
    last_close = bars[-1].close

    # Determine support level:
    # Option A: SMA20
    # Option B: 20-bar base low (lowest low of prior 20 bars)
    base_low = min(b.low for b in bars[-21:-1]) if len(bars) >= 21 else None
    support_a = sma20
    support_b = base_low
    supports = [s for s in [support_a, support_b] if s is not None]
    if not supports:
        return None

    best: Optional[PatternMatch] = None
    best_conf = -1.0

    for support in supports:
        support_label = "SMA20" if support == support_a else "base low"

        # Find bars that dipped below support in recent lookback
        dip_indices = [
            i for i, b in enumerate(recent_bars) if b.close < support
        ]
        if not dip_indices:
            continue

        # Check the dip is recent and short
        consecutive_below = 0
        max_consecutive = 0
        for i in range(len(recent_bars)):
            if recent_bars[i].close < support:
                consecutive_below += 1
                max_consecutive = max(max_consecutive, consecutive_below)
            else:
                consecutive_below = 0

        if max_consecutive > max_bars_below:
            continue  # too many bars below - real breakdown, not shakeout

        # Current close must be above support (snap-back)
        if last_close <= support:
            continue

        # Volume during dip must be low (no institutional selling)
        dip_vols = [recent_bars[i].volume for i in dip_indices]
        avg_dip_vol = sum(dip_vols) / len(dip_vols) if dip_vols else 0
        low_vol_dip = vol_avg_20 > 0 and avg_dip_vol < vol_avg_20 * dryup_thresh

        # Confidence
        speed_score = max(0.0, 1.0 - max_consecutive / max_bars_below) * 0.4
        vol_score = 0.4 if low_vol_dip else 0.1
        recency_score = max(0.0, 1.0 - max(dip_indices) / lookback) * 0.2
        confidence = speed_score + vol_score + recency_score

        if confidence > best_conf:
            best_conf = confidence
            pivot_price = support
            depth_pct = abs(min(recent_bars[i].close for i in dip_indices) - support) / support if support > 0 else 0
            best = PatternMatch(
                pattern_name="Shakeout",
                confirmed=True,  # snap-back already confirmed by close > support
                volume_confirmed=low_vol_dip,
                pivot_price=round(pivot_price, 4),
                confidence=round(confidence, 3),
                vcp_contractions=0,
                base_depth_pct=round(depth_pct, 4),
                description=(
                    f"Shakeout: {max_consecutive} bar(s) below {support_label} "
                    f"(${support:.2f}); "
                    f"vol during dip {'low (clean)' if low_vol_dip else 'elevated (caution)'}; "
                    f"snap-back confirmed at ${last_close:.2f}"
                ),
            )

    return best
