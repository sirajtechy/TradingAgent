"""
patterns.py — O'Neil CAN SLIM base pattern detector (weekly bars).

Implements William O'Neil's 4 primary constructive base formations:

  1. Cup with Handle  — most reliable; 7–65 week U-shape, 12–50% depth,
                        handle = 1–8 week tight consolidation off right rim
  2. Double Bottom    — W-shaped; two troughs ≤ 5% apart, ≥ 7 weeks wide
  3. Flat Base        — ≥ 5 weeks of tight price action (≤ 10–15% depth)
                        after a prior uptrend; signals continuation
  4. Ascending Base   — series of 3 higher pullback lows, each 10–20% deep;
                        often a sign of institutional accumulation

Volume analysis:
  - Volume dry-up at base lows / in the handle (< 65% of 10-week average)
    is a KEY O'Neil signal of supply exhaustion (bullish).
  - Breakout volume surge (> 1.5× average) confirms the move.

Late-stage detection:
  - Base number ≥ 3 from the major low = late-stage base (lower success).
  - Heuristic: count distinct consolidations from the 52-week low region.

Entry-point (pivot) rules:
  Cup w/Handle : high of the handle (or right rim if no handle) + 0.10   *
  Double Bottom: middle peak high + 0.10
  Flat Base    : top of the range + 0.10
  Ascending    : most recent swing high + 0.10
  (* In practice the agent returns the raw pivot; service adds the premium)

References:
  - William O'Neil, "How to Make Money in Stocks" (4th ed.)
  - Investors Business Daily base count methodology
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .models import BasePattern, WeeklyBar

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

_CUP_LOOKBACK   = 65    # Max weeks reviewed for cup search
_CUP_MIN_WEEKS  = 7
_CUP_MAX_WEEKS  = 65
_CUP_MIN_DEPTH  = 0.12  # 12%
_CUP_MAX_DEPTH  = 0.50  # 50% (normal market); use 0.65 in bear markets
_CUP_RIM_RATIO  = 0.85  # right rim must be ≥ 85% of left rim high
_HANDLE_MAX_WKS = 8
_HANDLE_MAX_DEC = 0.12  # max handle decline 12%
_DB_MIN_WEEKS   = 7
_DB_MAX_WEEKS   = 80
_DB_TROUGH_PCT  = 0.05  # two troughs within 5% of each other
_FLAT_MIN_WEEKS = 5
_FLAT_MAX_DEPTH = 0.15  # 15% depth threshold for flat base
_FLAT_UPTREND   = 0.20  # prior uptrend must be ≥ 20%
_ASC_MIN_PULLS  = 3     # minimum pullbacks for ascending base
_ASC_MAX_DEPTH  = 0.20  # max depth per pullback
_VOL_DRY_RATIO  = 0.65  # volume dry-up: < 65% of 10-week avg
_EXTREMA_ORDER  = 3     # local extrema half-window


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extrema(
    values: List[float],
    order: int = _EXTREMA_ORDER,
) -> Tuple[List[int], List[int]]:
    """
    Find local maxima and minima indices.
    A point i is a local max if it is ≥ all *order* neighbours on each side.
    Ties are included (≥ rather than >), which helps detect flat tops.
    """
    n = len(values)
    highs: List[int] = []
    lows:  List[int] = []
    for i in range(order, n - order):
        window = values[i - order: i + order + 1]
        if values[i] >= max(window):
            highs.append(i)
        if values[i] <= min(window):
            lows.append(i)
    return highs, lows


def _avg_volume(volumes: List[float], start: int, end: int) -> float:
    segment = volumes[start: end + 1]
    return sum(segment) / len(segment) if segment else 0.0


def _vol_dry_up(
    volumes: List[float],
    check_start: int,
    check_end: int,
    reference_avg: float,
) -> bool:
    """
    True if every volume bar in [check_start, check_end] is below
    *_VOL_DRY_RATIO* × *reference_avg*.  Requires at least 1 bar.
    """
    if reference_avg <= 0:
        return False
    segment = volumes[check_start: check_end + 1]
    if not segment:
        return False
    return all(v < reference_avg * _VOL_DRY_RATIO for v in segment)


def _count_bases(
    bars: List[WeeklyBar],
    base_start_idx: int,
) -> int:
    """
    Approximate base-count heuristic from the 52-week (104-bar) low.

    Strategy:
      1. Identify the lowest close in the 104 bars preceding base_start_idx.
      2. Scan from that low forward and count distinct consolidations
         (defined as a contiguous region where close range < 15% of midpoint).
      3. The current base counts as +1.

    A base_count ≥ 3 triggers the late-stage flag.
    """
    lookback = min(104, base_start_idx)
    if lookback < 10:
        return 1

    segment_bars = bars[:base_start_idx]
    segment_closes = [b.close for b in segment_bars[-lookback:]]
    if not segment_closes:
        return 1

    min_close = min(segment_closes)
    low_idx_offset = segment_closes.index(min_close)
    post_low = segment_closes[low_idx_offset:]

    # Sliding window: 10-bar windows, count how many form a base (spread < 15%)
    base_count = 0
    window_size = 6
    in_base = False
    for j in range(0, len(post_low) - window_size + 1, 3):
        window = post_low[j: j + window_size]
        mid = (max(window) + min(window)) / 2
        spread_pct = (max(window) - min(window)) / mid if mid > 0 else 0
        if spread_pct < 0.15:
            if not in_base:
                base_count += 1
                in_base = True
        else:
            in_base = False

    return max(1, base_count + 1)  # +1 for the current base being analysed


# ─────────────────────────────────────────────────────────────────────────────
# Pattern 1: Cup with Handle
# ─────────────────────────────────────────────────────────────────────────────

def detect_cup_with_handle(bars: List[WeeklyBar]) -> Optional[BasePattern]:
    """
    Detect the most recent Cup with Handle (or plain Cup) on weekly bars.

    O'Neil criteria:
    - Duration: 7–65 weeks
    - Depth: 12–50% from left rim high to cup low
    - Right rim: ≥ 85% of left rim high
    - U-shape: not a sharp V (at least 20% of duration near the bottom)
    - Handle: 1–8 weeks, pullback ≤ 12%, hugs right rim
    - Pivot: handle high (or right rim if no handle)
    """
    if len(bars) < 15:
        return None

    lookback = min(_CUP_LOOKBACK, len(bars))
    window = bars[-lookback:]
    highs   = [b.high for b in window]
    lows    = [b.low for b in window]
    closes  = [b.close for b in window]
    volumes = [b.volume for b in window]
    n = len(window)

    hi_idx, lo_idx = _extrema(highs, order=_EXTREMA_ORDER)

    best: Optional[Dict[str, Any]] = None
    best_conf = 0.0

    for ai in range(len(hi_idx)):
        for bi in range(ai + 1, len(hi_idx)):
            li, ri = hi_idx[ai], hi_idx[bi]

            duration = ri - li
            if duration < _CUP_MIN_WEEKS or duration > _CUP_MAX_WEEKS:
                continue

            # Cup bottom: lowest low between left and right rim
            bottom_val = min(lows[li:ri + 1])
            bottom_idx = li + lows[li:ri + 1].index(bottom_val)

            left_high  = highs[li]
            right_high = highs[ri]

            # Depth check
            depth = (left_high - bottom_val) / left_high
            if depth < _CUP_MIN_DEPTH or depth > _CUP_MAX_DEPTH:
                continue

            # Right rim must be close to left rim
            if right_high < left_high * _CUP_RIM_RATIO:
                continue
            if right_high > left_high * 1.10:  # right rim not >10% above left
                continue

            # U-shape check: enough bars near the bottom
            bottom_zone = bottom_val * (1.0 + depth * 0.30)
            near_bottom = sum(1 for j in range(li, ri + 1) if closes[j] <= bottom_zone)
            if near_bottom < max(2, int(duration * 0.15)):
                continue

            # 10-week avg volume for dry-up reference
            avg_vol = _avg_volume(volumes, max(0, li - 10), li)
            if avg_vol == 0:
                avg_vol = _avg_volume(volumes, 0, ri)

            # Handle detection
            handle_start = ri + 1
            handle_end   = min(n - 1, ri + _HANDLE_MAX_WKS)

            if handle_start > n - 1:
                # No room for handle
                pivot = right_high
                has_handle = False
                vdu = _vol_dry_up(volumes, max(0, bottom_idx - 2), bottom_idx, avg_vol)
            else:
                h_highs  = highs[handle_start: handle_end + 1]
                h_lows   = lows[handle_start: handle_end + 1]
                if h_highs:
                    hh = max(h_highs)
                    hl = min(h_lows)
                    pullback = (hh - hl) / hh if hh > 0 else 1.0
                    if hh <= right_high * 1.02 and pullback <= _HANDLE_MAX_DEC:
                        pivot      = hh
                        has_handle = True
                        vdu = _vol_dry_up(volumes, handle_start, handle_end, avg_vol)
                    else:
                        pivot      = right_high
                        has_handle = False
                        vdu = _vol_dry_up(volumes, max(0, bottom_idx - 2), bottom_idx, avg_vol)
                else:
                    pivot      = right_high
                    has_handle = False
                    vdu = False

            # Confidence scoring
            conf = 0.0
            # Depth quality (12-33% ideal)
            if 0.12 <= depth <= 0.33:
                conf += 0.22
            elif depth < 0.12:
                conf += 0.08
            else:
                conf += 0.12

            # Right rim symmetry
            rim_ratio = right_high / left_high
            if rim_ratio >= 0.98:
                conf += 0.20
            elif rim_ratio >= 0.92:
                conf += 0.14
            else:
                conf += 0.07

            # Handle
            if has_handle:
                conf += 0.15

            # Volume dry-up
            if vdu:
                conf += 0.15

            # Duration (7-26 weeks = ideal)
            if 7 <= duration <= 26:
                conf += 0.12
            else:
                conf += 0.06

            # Recency (right rim / pivot close to present)
            bars_back = n - 1 - ri
            if bars_back <= 2:
                conf += 0.16
            elif bars_back <= 6:
                conf += 0.10
            else:
                conf += 0.04

            if conf > best_conf:
                best_conf = conf
                best = {
                    "li": li, "ri": ri, "pivot": pivot,
                    "depth": depth, "duration": duration,
                    "has_handle": has_handle, "vdu": vdu,
                    "start_bar": window[li],
                    "end_bar": window[min(n - 1, ri + (2 if has_handle else 0))],
                    "base_start_abs": len(bars) - lookback + li,
                }

    if best is None or best_conf < 0.20:
        return None

    base_num = _count_bases(bars, best["base_start_abs"])
    name = "Cup with Handle" if best["has_handle"] else "Cup (no handle)"

    return BasePattern(
        name=name,
        direction="bullish",
        confidence=round(best_conf, 3),
        start_date=best["start_bar"].bar_date,
        end_date=best["end_bar"].bar_date,
        base_duration_weeks=best["duration"],
        pivot_level=round(best["pivot"], 4),
        base_depth_pct=round(best["depth"] * 100, 1),
        base_number=base_num,
        is_late_stage=base_num >= 3,
        has_volume_dry_up=best["vdu"],
        description=(
            f"{name} — {best['duration']}-week base, "
            f"{best['depth'] * 100:.0f}% depth, pivot ${best['pivot']:.2f}"
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pattern 2: Double Bottom
# ─────────────────────────────────────────────────────────────────────────────

def detect_double_bottom(bars: List[WeeklyBar]) -> Optional[BasePattern]:
    """
    Detect the most-recent Double Bottom (W-pattern).

    O'Neil criteria:
    - Duration: ≥ 7 weeks between the two troughs
    - Troughs within 5% of each other (second can be slightly lower = shakeout)
    - Middle peak is the pivot + 0.10
    - Volume dry-up at second bottom is bullish
    """
    if len(bars) < 12:
        return None

    lookback = min(_DB_MAX_WEEKS, len(bars))
    window = bars[-lookback:]
    highs   = [b.high for b in window]
    lows    = [b.low for b in window]
    volumes = [b.volume for b in window]
    n = len(window)

    _, lo_idx = _extrema(lows, order=_EXTREMA_ORDER)

    best: Optional[Dict[str, Any]] = None
    best_conf = 0.0

    for ai in range(len(lo_idx)):
        for bi in range(ai + 1, len(lo_idx)):
            first, second = lo_idx[ai], lo_idx[bi]

            duration = second - first
            if duration < _DB_MIN_WEEKS or duration > _DB_MAX_WEEKS:
                continue

            lo1 = lows[first]
            lo2 = lows[second]

            # Troughs within 5%
            if abs(lo1 - lo2) / lo1 > _DB_TROUGH_PCT:
                continue

            # Middle peak between the two troughs
            mid_section = highs[first: second + 1]
            mid_peak    = max(mid_section)
            mid_idx     = first + mid_section.index(mid_peak)

            # The middle peak must be meaningfully above the troughs
            peak_rise = (mid_peak - lo1) / lo1
            if peak_rise < 0.05:
                continue

            pivot = mid_peak

            # Volume dry-up at second bottom
            avg_vol = _avg_volume(volumes, max(0, first - 5), first)
            vdu = _vol_dry_up(volumes, max(0, second - 2), second, avg_vol)

            # Second trough lower (shakeout) = better setup
            shakeout = lo2 < lo1

            # Confidence
            conf = 0.0
            if 0.05 <= abs(lo1 - lo2) / lo1 <= 0.03:
                conf += 0.20
            else:
                conf += 0.12

            if shakeout:
                conf += 0.15  # under-cut pattern is more bullish

            if vdu:
                conf += 0.18

            if 7 <= duration <= 25:
                conf += 0.15
            else:
                conf += 0.08

            bars_back = n - 1 - second
            if bars_back <= 3:
                conf += 0.20
            elif bars_back <= 8:
                conf += 0.12
            else:
                conf += 0.05

            if conf > best_conf:
                best_conf = conf
                depth = (mid_peak - min(lo1, lo2)) / mid_peak
                best = {
                    "first": first, "second": second,
                    "pivot": pivot,
                    "depth": depth, "duration": duration,
                    "vdu": vdu,
                    "start_bar": window[first],
                    "end_bar": window[second],
                    "base_start_abs": len(bars) - lookback + first,
                }

    if best is None or best_conf < 0.20:
        return None

    base_num = _count_bases(bars, best["base_start_abs"])

    return BasePattern(
        name="Double Bottom",
        direction="bullish",
        confidence=round(best_conf, 3),
        start_date=best["start_bar"].bar_date,
        end_date=best["end_bar"].bar_date,
        base_duration_weeks=best["duration"],
        pivot_level=round(best["pivot"], 4),
        base_depth_pct=round(best["depth"] * 100, 1),
        base_number=base_num,
        is_late_stage=base_num >= 3,
        has_volume_dry_up=best["vdu"],
        description=(
            f"Double Bottom — {best['duration']}-week base, pivot ${best['pivot']:.2f}"
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pattern 3: Flat Base
# ─────────────────────────────────────────────────────────────────────────────

def detect_flat_base(bars: List[WeeklyBar]) -> Optional[BasePattern]:
    """
    Detect the most-recent Flat Base.

    O'Neil criteria:
    - At least 5 weeks in duration
    - Depth: ≤ 10–15% from high to low within the base
    - Forms after a prior uptrend of ≥ 20% (continuation base)
    - Tight weekly closes show institutional holding (no distribution)
    - Pivot: top of the base + 0.10
    """
    if len(bars) < 12:
        return None

    closes  = [b.close for b in bars]
    highs   = [b.high for b in bars]
    lows    = [b.low for b in bars]
    volumes = [b.volume for b in bars]
    n = len(bars)

    best: Optional[Dict[str, Any]] = None
    best_conf = 0.0

    # Scan different window sizes
    for window_weeks in range(5, min(30, n)):
        for start in range(max(0, n - 52), n - window_weeks + 1):
            end = start + window_weeks - 1
            seg_highs  = highs[start: end + 1]
            seg_lows   = lows[start: end + 1]
            seg_closes = closes[start: end + 1]

            h_max = max(seg_highs)
            l_min = min(seg_lows)
            mid   = (h_max + l_min) / 2

            depth = (h_max - l_min) / h_max if h_max > 0 else 1.0
            if depth > _FLAT_MAX_DEPTH:
                continue

            # Prior uptrend: close at start of window vs close 12 weeks before
            prior_start = max(0, start - 12)
            prior_gain  = (closes[start] - closes[prior_start]) / closes[prior_start] if closes[prior_start] > 0 else 0
            if prior_gain < _FLAT_UPTREND:
                continue

            pivot = h_max

            # Volume dry-up (tight base should have quiet volume)
            avg_vol = _avg_volume(volumes, max(0, start - 10), start - 1) if start > 0 else 0
            vdu = _vol_dry_up(volumes, start, end, avg_vol) if avg_vol > 0 else False

            # Tight close test: ≥ 60% of weeks have closes within 5% of high
            near_high = sum(1 for c in seg_closes if c >= h_max * 0.95)
            tightness  = near_high / len(seg_closes)

            # Recency
            bars_back = n - 1 - end

            conf = 0.0
            if depth <= 0.08:
                conf += 0.25
            elif depth <= 0.12:
                conf += 0.18
            else:
                conf += 0.10

            if tightness >= 0.60:
                conf += 0.18
            elif tightness >= 0.40:
                conf += 0.10

            if prior_gain >= 0.50:
                conf += 0.15
            elif prior_gain >= 0.20:
                conf += 0.10

            if window_weeks >= 7:
                conf += 0.12
            else:
                conf += 0.06

            if vdu:
                conf += 0.12

            if bars_back <= 2:
                conf += 0.18
            elif bars_back <= 6:
                conf += 0.10
            else:
                conf += 0.04

            if conf > best_conf:
                best_conf = conf
                best = {
                    "start": start, "end": end,
                    "pivot": pivot,
                    "depth": depth,
                    "duration": window_weeks,
                    "vdu": vdu,
                    "start_bar": bars[start],
                    "end_bar": bars[end],
                }

    if best is None or best_conf < 0.25:
        return None

    base_num = _count_bases(bars, best["start"])

    return BasePattern(
        name="Flat Base",
        direction="bullish",
        confidence=round(best_conf, 3),
        start_date=best["start_bar"].bar_date,
        end_date=best["end_bar"].bar_date,
        base_duration_weeks=best["duration"],
        pivot_level=round(best["pivot"], 4),
        base_depth_pct=round(best["depth"] * 100, 1),
        base_number=base_num,
        is_late_stage=base_num >= 3,
        has_volume_dry_up=best["vdu"],
        description=(
            f"Flat Base — {best['duration']}-week base, "
            f"{best['depth'] * 100:.0f}% depth, pivot ${best['pivot']:.2f}"
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pattern 4: Ascending Base
# ─────────────────────────────────────────────────────────────────────────────

def detect_ascending_base(bars: List[WeeklyBar]) -> Optional[BasePattern]:
    """
    Detect an Ascending Base — 3+ consecutive pullbacks with higher lows.

    O'Neil criteria:
    - At least 3 pullbacks each with a higher low than the previous
    - Each pullback 10–20% deep (not too shallow, not too deep)
    - Each recovery brings price back near or above the prior high
    - Signals strong institutions buying every dip
    - Pivot: most recent swing high in the formation
    """
    if len(bars) < 15:
        return None

    lookback = min(65, len(bars))
    window = bars[-lookback:]
    highs   = [b.high for b in window]
    lows    = [b.low for b in window]
    volumes = [b.volume for b in window]
    n = len(window)

    hi_idx, lo_idx = _extrema(highs, order=_EXTREMA_ORDER)

    best: Optional[Dict[str, Any]] = None
    best_conf = 0.0

    # Need at least 3 trough-peak cycles
    if len(lo_idx) < _ASC_MIN_PULLS or len(hi_idx) < _ASC_MIN_PULLS:
        return None

    # Scan for sequences of 3+ ascending pullback lows
    for start_lo in range(len(lo_idx) - _ASC_MIN_PULLS + 1):
        lo_seq = lo_idx[start_lo: start_lo + _ASC_MIN_PULLS]

        # Each low must be higher than the previous
        lo_vals = [lows[i] for i in lo_seq]
        if not all(lo_vals[j] > lo_vals[j - 1] for j in range(1, len(lo_vals))):
            continue

        # Find associated highs
        hi_seq: List[int] = []
        for lo_i in lo_seq:
            # Find the nearest high after this low
            after_highs = [h for h in hi_idx if h > lo_i]
            if after_highs:
                hi_seq.append(after_highs[0])

        if len(hi_seq) < _ASC_MIN_PULLS - 1:
            continue

        # Check each pullback depth
        depths: List[float] = []
        for j in range(len(hi_seq)):
            if j < len(lo_seq):
                # pullback = from prior high to trough
                prior_hi = highs[hi_seq[j - 1]] if j > 0 else highs[hi_seq[0]]
                trough   = lo_vals[j]
                d = (prior_hi - trough) / prior_hi if prior_hi > 0 else 0
                depths.append(d)

        if not depths:
            continue

        valid_depths = [d for d in depths if 0.08 <= d <= _ASC_MAX_DEPTH]
        if len(valid_depths) < 2:
            continue

        # Pivot = most recent high in the sequence
        latest_hi_idx = hi_seq[-1]
        pivot = highs[latest_hi_idx]

        # Duration: total weeks from first low to most recent high
        duration = latest_hi_idx - lo_seq[0]

        # Volume dry-up
        avg_vol = _avg_volume(volumes, max(0, lo_seq[0] - 10), lo_seq[0])
        vdu = _vol_dry_up(volumes, lo_seq[-1] - 2, lo_seq[-1], avg_vol) if lo_seq[-1] >= 2 else False

        bars_back = n - 1 - latest_hi_idx

        conf = 0.0
        conf += 0.15 * min(len(lo_seq), 5) / 5     # more pullbacks → higher confidence
        conf += 0.15 if len(valid_depths) == len(depths) else 0.08
        conf += 0.15 if vdu else 0.0
        if bars_back <= 3:
            conf += 0.20
        elif bars_back <= 8:
            conf += 0.12
        else:
            conf += 0.05

        # Upward slope quality
        slope_gain = (lo_vals[-1] - lo_vals[0]) / lo_vals[0] if lo_vals[0] > 0 else 0
        if slope_gain >= 0.15:
            conf += 0.15
        elif slope_gain >= 0.05:
            conf += 0.10

        if conf > best_conf:
            best_conf = conf
            avg_depth = sum(depths) / len(depths) if depths else 0
            total_abs_start = len(bars) - lookback + lo_seq[0]
            best = {
                "start_idx": lo_seq[0], "end_idx": latest_hi_idx,
                "pivot": pivot,
                "depth": avg_depth, "duration": duration,
                "pullback_count": len(lo_seq),
                "vdu": vdu,
                "start_bar": window[lo_seq[0]],
                "end_bar": window[latest_hi_idx],
                "base_start_abs": total_abs_start,
            }

    if best is None or best_conf < 0.25:
        return None

    base_num = _count_bases(bars, best["base_start_abs"])

    return BasePattern(
        name="Ascending Base",
        direction="bullish",
        confidence=round(best_conf, 3),
        start_date=best["start_bar"].bar_date,
        end_date=best["end_bar"].bar_date,
        base_duration_weeks=best["duration"],
        pivot_level=round(best["pivot"], 4),
        base_depth_pct=round(best["depth"] * 100, 1),
        base_number=base_num,
        is_late_stage=base_num >= 3,
        has_volume_dry_up=best["vdu"],
        description=(
            f"Ascending Base — {best['pullback_count']} pullbacks, "
            f"{best['duration']}-week formation, pivot ${best['pivot']:.2f}"
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Combined detector
# ─────────────────────────────────────────────────────────────────────────────

def detect_all_patterns(bars: List[WeeklyBar]) -> List[BasePattern]:
    """
    Run all 4 O'Neil pattern detectors and return every pattern found,
    sorted by confidence (highest first).

    Each detector is fault-isolated — one failure does not abort the rest.
    """
    found: List[BasePattern] = []

    for detector_name, detector_fn in [
        ("Cup with Handle",  detect_cup_with_handle),
        ("Double Bottom",    detect_double_bottom),
        ("Flat Base",        detect_flat_base),
        ("Ascending Base",   detect_ascending_base),
    ]:
        try:
            result = detector_fn(bars)
            if result is not None:
                found.append(result)
        except Exception as exc:
            logger.warning("Pattern detector '%s' raised: %s", detector_name, exc)

    found.sort(key=lambda p: p.confidence, reverse=True)
    return found
