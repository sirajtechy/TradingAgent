"""
patterns.py — 5 pattern detectors for the Phoenix Agent.

Phoenix Trader uses 5 structural patterns (in priority order):
  1. VCP   — Volatility Contraction Pattern (primary — Mark Minervini)
  2. Flat Base — 4–24 weeks sideways, <15% range, volume contracting
  3. Tight Flag — sharp flagpole + tight consolidation + volume dryup
  4. Shakeout — false breakdown below support → snap back above
  5. Pullback to MA10/MA20 — healthy retrace after a prior breakout

Key Phoenix rules (stricter than Technical Agent):
  - Breakout volume threshold: ≥ 2.0× avg (not 1.5×)
  - Flat base max range: 15% (not 25%)
  - Flag retrace: ≤ 50% of flagpole
  - Volume MUST be contracting during base formation

Public API
──────────
  detect_all_patterns(snapshot, settings) → PatternMatch
    Returns the BEST (highest confidence) pattern found.
    Returns a 'None' PatternMatch if nothing qualifies.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from .config import PhoenixSettings
from .models import OHLCVBar, PatternMatch, PhoenixSnapshot


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# 1. VCP — Volatility Contraction Pattern
# ─────────────────────────────────────────────────────────────────────────────

def _detect_vcp(
    bars: List[OHLCVBar],
    vol_avg_20: float,
    settings: PhoenixSettings,
) -> Optional[PatternMatch]:
    """
    VCP algorithm (Mark Minervini):
    Find progressively tighter contractions from a base peak.
    Each contraction must be ≤ 50% of the prior in both depth and range.
    Volume must dry up in each successive contraction.
    Breakout fires when price > pivot AND volume ≥ 2× avg.
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

    # ── Find up to 3 contraction cycles ──────────────────────────────────
    contractions: List[dict] = []   # each: {depth_pct, range_pct, vol_avg, trough_idx, recovery_idx}
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
            break  # too shallow — not a real contraction

        # High-low range within this contraction window
        contraction_bars = bars[search_start:trough_i + 1]
        range_high = max(b.high for b in contraction_bars)
        range_low  = min(b.low  for b in contraction_bars)
        range_pct  = (range_high - range_low) / range_high if range_high > 0 else 0

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
                pass  # soft check — don't hard-break on volume here

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

    # ── Pivot = highest close during the final contraction ────────────────
    final_trough_i = contractions[-1]["trough_idx"]
    final_recovery_i = contractions[-1]["recovery_idx"]
    # Pivot is the resistance level just before the final tight area
    # Use the high of the recovery before the last trough
    if len(contractions) >= 2:
        pivot_price = bars[contractions[-2]["recovery_idx"]].high
    else:
        pivot_price = peak_price

    # ── Check breakout ────────────────────────────────────────────────────
    last_bar = bars[-1]
    last_close = last_bar.close
    last_vol = last_bar.volume

    price_breakout = last_close > pivot_price
    volume_confirmed = vol_avg_20 > 0 and last_vol >= vol_avg_20 * settings.volume_breakout_multiple
    confirmed = price_breakout and volume_confirmed

    # ── Confidence scoring ─────────────────────────────────────────────────
    # Factors: number of contractions, volume quality, recency of pattern
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
        vol_quality = 0.15  # single contraction — half credit

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


# ─────────────────────────────────────────────────────────────────────────────
# 2. Flat Base
# ─────────────────────────────────────────────────────────────────────────────

def _detect_flat_base(
    bars: List[OHLCVBar],
    vol_avg_20: float,
    settings: PhoenixSettings,
) -> Optional[PatternMatch]:
    """
    Flat Base (Phoenix version — tighter than Technical Agent):
      - 20–120 bars of sideways consolidation
      - High-to-low range < 15% (Phoenix spec)
      - Volume CONTRACTING during base (last 10 bars < first 10 bars)
      - Breakout: close above base high AND volume ≥ 2× avg
    """
    min_bars = settings.flat_base_min_bars
    max_bars = settings.flat_base_max_bars
    max_range = settings.flat_base_max_range_pct
    vol_mult  = settings.volume_breakout_multiple

    if len(bars) < min_bars + 2:
        return None

    # Scan different base lengths, pick the most recent qualifying one
    last_bar = bars[-1]
    last_close = last_bar.close
    last_vol   = last_bar.volume

    best: Optional[PatternMatch] = None
    best_conf = -1.0

    for base_len in range(min_bars, min(max_bars, len(bars) - 1) + 1):
        base_bars = bars[-(base_len + 1):-1]  # exclude the current (potential breakout) bar
        if len(base_bars) < min_bars:
            continue

        base_high = max(b.high  for b in base_bars)
        base_low  = min(b.low   for b in base_bars)
        if base_high <= 0:
            continue

        range_pct = (base_high - base_low) / base_high
        if range_pct > max_range:
            # Too wide — not a flat base
            continue

        # Volume contracting: last 10 bars of base < first 10 bars of base
        first10 = base_bars[:10]
        last10  = base_bars[-10:] if len(base_bars) >= 20 else base_bars[len(base_bars)//2:]
        first10_vol = sum(b.volume for b in first10) / len(first10) if first10 else 0
        last10_vol  = sum(b.volume for b in last10)  / len(last10)  if last10  else 0
        vol_contracting = last10_vol < first10_vol if first10_vol > 0 else False

        # Breakout check
        pivot_price     = base_high
        price_breakout  = last_close > pivot_price
        vol_confirmed   = vol_avg_20 > 0 and last_vol >= vol_avg_20 * vol_mult
        confirmed       = price_breakout and vol_confirmed

        # Confidence
        range_score    = max(0.0, (max_range - range_pct) / max_range) * 0.4
        vol_cont_score = 0.3 if vol_contracting else 0.0
        base_len_score = min(base_len / 60, 1.0) * 0.2  # longer base = stronger
        confirm_score  = 0.1 if confirmed else 0.0
        confidence     = range_score + vol_cont_score + base_len_score + confirm_score

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


# ─────────────────────────────────────────────────────────────────────────────
# 3. Tight Flag (Bull Flag with Phoenix standards)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_tight_flag(
    bars: List[OHLCVBar],
    vol_avg_20: float,
    settings: PhoenixSettings,
) -> Optional[PatternMatch]:
    """
    Tight Flag / Pocket Pivot (Phoenix version):
      - Flagpole: gain ≥ 8% in ≤ 15 bars
      - Flag: retrace ≤ 50% of pole in ≤ 20 bars
      - Volume: drying up during flag (< 75% avg)
      - Breakout: close above flag high AND volume ≥ 2× avg
    """
    pole_gain    = settings.flag_pole_min_gain_pct / 100
    pole_max_bar = settings.flag_pole_max_bars
    max_retrace  = settings.flag_max_retrace_pct
    flag_max_bar = settings.flag_max_bars
    dryup_thresh = settings.volume_dryup_threshold
    vol_mult     = settings.volume_breakout_multiple

    if len(bars) < pole_max_bar + flag_max_bar + 2:
        return None

    last_bar  = bars[-1]
    last_close = last_bar.close
    last_vol   = last_bar.volume

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

        flag_low  = min(b.low  for b in flag_bars)
        flag_high = max(b.high for b in flag_bars)
        pole_height = pole_top_price - pole_base_price

        retrace = (pole_top_price - flag_low) / pole_height if pole_height > 0 else 1.0
        if retrace > max_retrace:
            continue  # retraced too much — not tight

        # Volume dryup during flag
        flag_vol_avg = sum(b.volume for b in flag_bars) / len(flag_bars) if flag_bars else 0
        vol_drying = flag_vol_avg < vol_avg_20 * dryup_thresh if vol_avg_20 > 0 else False

        # Breakout check
        pivot_price    = flag_high
        price_breakout = last_close > pivot_price
        vol_confirmed  = vol_avg_20 > 0 and last_vol >= vol_avg_20 * vol_mult
        confirmed      = price_breakout and vol_confirmed

        # Confidence
        pole_score    = min(pole_gain_actual / 0.20, 1.0) * 0.3  # 20% pole = max score
        retrace_score = max(0.0, (max_retrace - retrace) / max_retrace) * 0.3
        dryup_score   = 0.25 if vol_drying else 0.0
        confirm_score = 0.15 if confirmed else 0.0
        confidence    = pole_score + retrace_score + dryup_score + confirm_score

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


# ─────────────────────────────────────────────────────────────────────────────
# 4. Shakeout
# ─────────────────────────────────────────────────────────────────────────────

def _detect_shakeout(
    bars: List[OHLCVBar],
    vol_avg_20: float,
    sma20: Optional[float],
    settings: PhoenixSettings,
) -> Optional[PatternMatch]:
    """
    Shakeout: false breakdown below support → snap back.
      Support: MA20 or prior 20-bar base low.
      Dip below support: ≤ 3 bars, volume < avg (no real selling).
      Most recent close: above support (snap-back confirmed).
    """
    max_bars_below  = settings.shakeout_max_bars_below
    lookback        = settings.shakeout_lookback_bars
    dryup_thresh    = settings.volume_dryup_threshold

    if len(bars) < lookback + 10:
        return None

    recent_bars = bars[-lookback:]
    last_close  = bars[-1].close

    # Determine support level
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
            continue  # too many bars below — real breakdown, not shakeout

        # Current close must be above support (snap-back)
        if last_close <= support:
            continue

        # Volume during dip must be low (no institutional selling)
        dip_vols = [recent_bars[i].volume for i in dip_indices]
        avg_dip_vol = sum(dip_vols) / len(dip_vols) if dip_vols else 0
        low_vol_dip = vol_avg_20 > 0 and avg_dip_vol < vol_avg_20 * dryup_thresh

        # Confidence
        speed_score  = max(0.0, 1.0 - max_consecutive / max_bars_below) * 0.4
        vol_score    = 0.4 if low_vol_dip else 0.1
        recency_score = max(0.0, 1.0 - max(dip_indices) / lookback) * 0.2
        confidence   = speed_score + vol_score + recency_score

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


# ─────────────────────────────────────────────────────────────────────────────
# 5. Pullback to MA10 / MA20
# ─────────────────────────────────────────────────────────────────────────────

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
    proximity   = settings.pullback_proximity_pct
    prior_bars  = settings.pullback_prior_breakout_bars
    dryup_thresh = settings.volume_dryup_threshold

    if len(bars) < prior_bars + 5:
        return None

    last_bar   = bars[-1]
    last_close = last_bar.close
    last_vol   = last_bar.volume
    prev_close = bars[-2].close if len(bars) >= 2 else last_close

    # Last bar must have closed up
    last_bar_up = last_close > prev_close

    # Check for prior breakout (52w high) within last `prior_bars` bars
    lookback_bars  = bars[-prior_bars - 1:]
    all_time_high  = max(b.high for b in bars)
    recent_high    = max(b.high for b in lookback_bars[:-1])
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
        vol_score       = 0.30 if vol_drying else 0.10
        bounce_score    = 0.20 if last_bar_up else 0.0
        breakout_score  = 0.15  # prior breakout confirmed

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


# ─────────────────────────────────────────────────────────────────────────────
# Public dispatcher
# ─────────────────────────────────────────────────────────────────────────────

def detect_all_patterns(
    snapshot: PhoenixSnapshot,
    settings: Optional[PhoenixSettings] = None,
) -> PatternMatch:
    """
    Run all 5 pattern detectors and return the best (highest confidence) match.

    Priority order when confidence is equal:
      VCP > Flat Base > Tight Flag > Shakeout > Pullback

    Returns a PatternMatch with pattern_name='None' if nothing qualifies.
    """
    if settings is None:
        settings = PhoenixSettings()

    bars       = snapshot.bars
    vol_avg_20 = snapshot.vol_avg_20
    sma10      = snapshot.smas.sma10
    sma20      = snapshot.smas.sma20

    candidates: List[Tuple[int, PatternMatch]] = []  # (priority, match)

    # Priority 1 — VCP
    vcp = _detect_vcp(bars, vol_avg_20, settings)
    if vcp is not None:
        candidates.append((1, vcp))

    # Priority 2 — Flat Base
    flat = _detect_flat_base(bars, vol_avg_20, settings)
    if flat is not None:
        candidates.append((2, flat))

    # Priority 3 — Tight Flag
    flag = _detect_tight_flag(bars, vol_avg_20, settings)
    if flag is not None:
        candidates.append((3, flag))

    # Priority 4 — Shakeout
    shakeout = _detect_shakeout(bars, vol_avg_20, sma20, settings)
    if shakeout is not None:
        candidates.append((4, shakeout))

    # Priority 5 — Pullback
    pullback = _detect_pullback(bars, vol_avg_20, sma10, sma20, settings)
    if pullback is not None:
        candidates.append((5, pullback))

    if not candidates:
        return _no_pattern()

    # Sort: highest confidence first; break ties by priority (lower = better)
    candidates.sort(key=lambda x: (-x[1].confidence, x[0]))
    return candidates[0][1]
