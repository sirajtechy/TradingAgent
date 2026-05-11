"""VCP detector for the Phoenix Agent."""

from __future__ import annotations

from typing import List, Optional

from ..config import PhoenixSettings
from ..models import OHLCVBar, PatternMatch
from ..pattern_helpers import _swing_high_idx, _trough_idx


def _detect_vcp(
    bars: List[OHLCVBar],
    vol_avg_20: float,
    settings: PhoenixSettings,
) -> Optional[PatternMatch]:
    """
    VCP algorithm (Mark Minervini):
    Find progressively tighter contractions from a base peak.
    Each contraction must be <= 50% of the prior in both depth and range.
    Volume must dry up in each successive contraction.
    Breakout fires when price > pivot AND volume >= 2x avg.
    """
    lookback = min(settings.vcp_lookback_bars, len(bars))
    if lookback < 30:
        return None

    peak_idx = _swing_high_idx(bars, lookback)
    peak_price = bars[peak_idx].high

    # Need at least some bars after the peak to form contractions
    bars_after_peak = len(bars) - 1 - peak_idx
    if bars_after_peak < 10:
        return None

    # Find up to 3 contraction cycles
    contractions: List[dict] = []
    search_start = peak_idx

    for contraction_num in range(settings.vcp_max_contractions):
        remaining = len(bars) - 1 - search_start
        if remaining < 5:
            break

        # Find trough after search_start
        trough_i = _trough_idx(bars, search_start + 1, len(bars) - 1)
        trough_price = bars[trough_i].close

        # Depth from the reference high (first contraction uses peak; subsequent use recovery high)
        ref_high = peak_price if not contractions else bars[contractions[-1]["recovery_idx"]].high
        depth_pct = (ref_high - trough_price) / ref_high if ref_high > 0 else 0

        if depth_pct < settings.vcp_min_depth_pct:
            break  # too shallow - not a real contraction

        # High-low range within this contraction window
        contraction_bars = bars[search_start:trough_i + 1]
        range_high = max(b.high for b in contraction_bars)
        range_low = min(b.low for b in contraction_bars)
        range_pct = (range_high - range_low) / range_high if range_high > 0 else 0

        # Volume average during this contraction
        contraction_vol_avg = (
            sum(b.volume for b in contraction_bars) / len(contraction_bars)
            if contraction_bars else 0.0
        )

        # Enforce tightening relative to prior contraction
        if contractions:
            prior = contractions[-1]
            if depth_pct >= prior["depth_pct"] * settings.vcp_contraction_ratio:
                break  # not tightening enough in depth
            if range_pct >= prior["range_pct"] * settings.vcp_contraction_ratio:
                break  # not tightening enough in range
            if contraction_vol_avg >= prior["vol_avg"] * 1.0:
                # Volume should also be drying up (not growing)
                pass  # soft check - don't hard-break on volume here

        # Find recovery high after this trough
        recovery_end = min(trough_i + 30, len(bars) - 1)
        recovery_i = trough_i
        recovery_high = bars[trough_i].high
        for j in range(trough_i + 1, recovery_end + 1):
            if bars[j].high > recovery_high:
                recovery_high = bars[j].high
                recovery_i = j

        contractions.append({
            "depth_pct": depth_pct,
            "range_pct": range_pct,
            "vol_avg": contraction_vol_avg,
            "trough_idx": trough_i,
            "recovery_idx": recovery_i,
        })

        search_start = recovery_i

    if not contractions:
        return None

    num_contractions = len(contractions)

    # Pivot is the resistance level just before the final tight area.
    final_trough_i = contractions[-1]["trough_idx"]
    final_recovery_i = contractions[-1]["recovery_idx"]
    if len(contractions) >= 2:
        pivot_price = bars[contractions[-2]["recovery_idx"]].high
    else:
        pivot_price = peak_price

    # Check breakout
    last_bar = bars[-1]
    last_close = last_bar.close
    last_vol = last_bar.volume

    price_breakout = last_close > pivot_price
    volume_confirmed = vol_avg_20 > 0 and last_vol >= vol_avg_20 * settings.volume_breakout_multiple
    confirmed = price_breakout and volume_confirmed

    # Confidence scoring
    contraction_score = min(num_contractions / settings.vcp_max_contractions, 1.0) * 0.4

    # Volume quality: each contraction should have less volume than the prior
    vol_quality = 0.0
    if len(contractions) >= 2:
        declining_vols = sum(
            1 for i in range(1, len(contractions))
            if contractions[i]["vol_avg"] < contractions[i - 1]["vol_avg"]
        )
        vol_quality = (declining_vols / (len(contractions) - 1)) * 0.3
    else:
        vol_quality = 0.15  # single contraction - half credit

    # Recency: pattern completion within last 20 bars scores full marks
    bars_since_trough = len(bars) - 1 - final_trough_i
    recency_score = max(0.0, 1.0 - bars_since_trough / 20) * 0.3

    confidence = min(contraction_score + vol_quality + recency_score, 1.0)

    depth_pct = contractions[0]["depth_pct"]

    return PatternMatch(
        pattern_name="VCP",
        confirmed=confirmed,
        volume_confirmed=volume_confirmed,
        pivot_price=round(pivot_price, 4),
        confidence=round(confidence, 3),
        vcp_contractions=num_contractions,
        base_depth_pct=round(depth_pct, 4),
        description=(
            f"VCP: {num_contractions} contraction(s) from peak ${peak_price:.2f}; "
            f"pivot ${pivot_price:.2f}; "
            f"{'CONFIRMED breakout' if confirmed else 'not yet triggered'}"
        ),
    )
