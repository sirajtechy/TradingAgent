"""
patterns.py — Chart-pattern recognition engine for the technical agent.

Scans the last 12 months (~252 trading days) of OHLCV data for classic
breakout / breakdown patterns.  Each detector is independent — they share
only the ``_find_local_extrema`` helper.

Detected patterns (8):
    Bullish:                        Bearish:
      1. Cup & Handle                 5. Head & Shoulders (top)
      2. Inverse Head & Shoulders     6. Double Top (M-pattern)
      3. Double Bottom (W-pattern)    7. Descending Triangle
      4. Bull Flag / Pennant
      * Ascending Triangle

Every detector returns a list of ``PatternSignal`` (may be empty).
``detect_all_patterns()`` is the single entry-point called by the LangGraph
``detect_patterns`` node.

Design principles:
    - No external dependencies (pure stdlib math).
    - Deterministic: same bars → same patterns.
    - Volume confirmation: breakout bar volume must exceed 1.5× the 20-day
      average to qualify as "volume confirmed".
    - Confidence is a composite of symmetry quality, volume confirmation,
      pattern depth, and recency.
    - No silent failures: if a sub-detector raises, it is caught and
      logged in the warnings list so the remaining detectors still run.

References:
    - Edwards & Magee, *Technical Analysis of Stock Trends* (1948)
    - Thomas Bulkowski, *Encyclopedia of Chart Patterns* (2005)
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import logging

from .models import OHLCVBar, PatternSignal

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------- #
# Configuration constants                                                   #
# ----------------------------------------------------------------------- #

# Minimum number of bars the lookback window must contain.
_MIN_LOOKBACK_BARS = 60
# Default lookback window in bars (~12 months).
_LOOKBACK_BARS = 252
# Breakout volume must exceed this multiple of the 20-bar average volume.
_VOLUME_SURGE_MULTIPLE = 1.5
# How many neighbours on each side to use when finding peaks / troughs.
_EXTREMA_ORDER = 5


# ====================================================================== #
# HELPERS                                                                   #
# ====================================================================== #

def _find_local_extrema(
    values: List[float],
    order: int = _EXTREMA_ORDER,
) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """
    Find local maxima and minima in *values* without scipy.

    A point at index *i* is a local max if it is strictly greater than
    the *order* points on either side (minima analogous).

    Args:
        values: Numeric series.
        order:  Half-window size.

    Returns:
        (maxima, minima) — each a list of ``(index, value)`` tuples
        sorted chronologically.
    """
    maxima: List[Tuple[int, float]] = []
    minima: List[Tuple[int, float]] = []
    n = len(values)

    for i in range(order, n - order):
        val = values[i]
        window = values[i - order : i + order + 1]

        if val == max(window) and window.count(val) == 1:
            maxima.append((i, val))
        if val == min(window) and window.count(val) == 1:
            minima.append((i, val))

    return maxima, minima


def _avg_volume(volumes: List[float], end_idx: int, window: int = 20) -> float:
    """
    Average volume over *window* bars ending at *end_idx* (inclusive).

    Returns 0.0 if there are not enough bars — the caller should treat
    this as "volume confirmation not available" rather than crashing.
    """
    start = max(0, end_idx - window + 1)
    segment = volumes[start : end_idx + 1]
    return sum(segment) / len(segment) if segment else 0.0


def _volume_confirmed(volumes: List[float], breakout_idx: int) -> bool:
    """True if the breakout bar's volume exceeds 1.5× the 20-bar average."""
    avg = _avg_volume(volumes, breakout_idx - 1)  # avg *before* breakout
    if avg <= 0:
        return False
    return volumes[breakout_idx] >= avg * _VOLUME_SURGE_MULTIPLE


def _pct_diff(a: float, b: float) -> float:
    """Absolute percentage difference between *a* and *b*.  Returns 0 if both are zero."""
    denom = (abs(a) + abs(b)) / 2.0
    if denom == 0:
        return 0.0
    return abs(a - b) / denom * 100.0


def _recency_bonus(pattern_end_idx: int, total_bars: int) -> float:
    """
    0.0 – 0.15 bonus based on how recently the pattern ended.

    A pattern that completed on the last bar gets the full 0.15.
    One that completed a year ago gets 0.0.
    """
    if total_bars <= 0:
        return 0.0
    bars_ago = total_bars - 1 - pattern_end_idx
    decay = max(0.0, 1.0 - bars_ago / total_bars)
    return round(decay * 0.15, 4)


# ====================================================================== #
# INDIVIDUAL PATTERN DETECTORS                                              #
# ====================================================================== #

def _detect_double_bottom(
    closes: List[float],
    lows: List[float],
    highs: List[float],
    volumes: List[float],
    dates: List[date],
) -> List[PatternSignal]:
    """
    Double Bottom (W-pattern) — two troughs at roughly the same level
    separated by a peak, followed by a breakout above that peak.

    Detection rules:
        1. Find consecutive minima pairs where the price level is within 3%.
        2. The two troughs must be 20–65 bars apart.
        3. There must be a peak between them (the "neckline").
        4. If the most recent close is above the neckline → breakout.
    """
    results: List[PatternSignal] = []
    _, minima = _find_local_extrema(lows, _EXTREMA_ORDER)
    maxima, _ = _find_local_extrema(highs, _EXTREMA_ORDER)
    n = len(closes)

    for i in range(len(minima) - 1):
        idx1, val1 = minima[i]
        idx2, val2 = minima[i + 1]
        gap = idx2 - idx1

        # Rule 2: spacing check
        if gap < 20 or gap > 65:
            continue

        # Rule 1: similar price level
        if _pct_diff(val1, val2) > 3.0:
            continue

        # Rule 3: find the highest peak between the two troughs
        mid_peaks = [(ix, vx) for ix, vx in maxima if idx1 < ix < idx2]
        if not mid_peaks:
            continue
        neckline_idx, neckline_val = max(mid_peaks, key=lambda t: t[1])

        # Rule 4: breakout check — is the latest close above neckline?
        breakout = closes[-1] > neckline_val
        vol_conf = _volume_confirmed(volumes, n - 1) if breakout else False

        # Confidence scoring
        symmetry = 1.0 - _pct_diff(val1, val2) / 3.0  # 0–1
        depth = min((neckline_val - min(val1, val2)) / neckline_val * 100, 20) / 20  # 0–1
        conf = 0.3 * symmetry + 0.25 * depth
        conf += 0.20 if breakout else 0.0
        conf += 0.15 if vol_conf else 0.0
        conf += _recency_bonus(idx2, n)
        conf = min(round(conf, 3), 1.0)

        # Measured move: neckline + (neckline - avg trough)
        avg_trough = (val1 + val2) / 2.0
        _pat_target = round(neckline_val + (neckline_val - avg_trough), 2) if breakout else None
        _breakout_date = dates[n - 1] if breakout else None

        results.append(PatternSignal(
            pattern_name="Double Bottom",
            direction="bullish",
            confidence=conf,
            start_date=dates[idx1],
            end_date=dates[idx2],
            breakout_confirmed=breakout,
            volume_confirmation=vol_conf,
            description=(
                f"Two lows at ~${val1:.2f} & ${val2:.2f}, "
                f"neckline ${neckline_val:.2f}"
                f"{', breakout confirmed' if breakout else ''}"
            ),
            breakout_price=round(neckline_val, 2) if breakout else None,
            breakout_date=_breakout_date,
            pattern_target=_pat_target,
        ))

    return results


def _detect_double_top(
    closes: List[float],
    lows: List[float],
    highs: List[float],
    volumes: List[float],
    dates: List[date],
) -> List[PatternSignal]:
    """
    Double Top (M-pattern) — two peaks at roughly the same level,
    followed by a breakdown below the trough between them.
    """
    results: List[PatternSignal] = []
    maxima, _ = _find_local_extrema(highs, _EXTREMA_ORDER)
    _, minima = _find_local_extrema(lows, _EXTREMA_ORDER)
    n = len(closes)

    for i in range(len(maxima) - 1):
        idx1, val1 = maxima[i]
        idx2, val2 = maxima[i + 1]
        gap = idx2 - idx1

        if gap < 20 or gap > 65:
            continue
        if _pct_diff(val1, val2) > 3.0:
            continue

        # Trough between the two peaks
        mid_troughs = [(ix, vx) for ix, vx in minima if idx1 < ix < idx2]
        if not mid_troughs:
            continue
        neckline_idx, neckline_val = min(mid_troughs, key=lambda t: t[1])

        breakout = closes[-1] < neckline_val
        vol_conf = _volume_confirmed(volumes, n - 1) if breakout else False

        symmetry = 1.0 - _pct_diff(val1, val2) / 3.0
        depth = min((max(val1, val2) - neckline_val) / max(val1, val2) * 100, 20) / 20
        conf = 0.3 * symmetry + 0.25 * depth
        conf += 0.20 if breakout else 0.0
        conf += 0.15 if vol_conf else 0.0
        conf += _recency_bonus(idx2, n)
        conf = min(round(conf, 3), 1.0)

        results.append(PatternSignal(
            pattern_name="Double Top",
            direction="bearish",
            confidence=conf,
            start_date=dates[idx1],
            end_date=dates[idx2],
            breakout_confirmed=breakout,
            volume_confirmation=vol_conf,
            description=(
                f"Two peaks at ~${val1:.2f} & ${val2:.2f}, "
                f"neckline ${neckline_val:.2f}"
                f"{', breakdown confirmed' if breakout else ''}"
            ),
        ))

    return results


def _detect_head_and_shoulders_top(
    closes: List[float],
    lows: List[float],
    highs: List[float],
    volumes: List[float],
    dates: List[date],
) -> List[PatternSignal]:
    """
    Head & Shoulders (bearish) — three peaks where the middle peak (head)
    is higher than the two shoulders.  Breakdown below the neckline
    (line connecting the two troughs) confirms the pattern.
    """
    results: List[PatternSignal] = []
    maxima, _ = _find_local_extrema(highs, _EXTREMA_ORDER)
    _, minima = _find_local_extrema(lows, _EXTREMA_ORDER)
    n = len(closes)

    for i in range(len(maxima) - 2):
        ls_idx, ls_val = maxima[i]       # left shoulder
        h_idx, h_val = maxima[i + 1]     # head
        rs_idx, rs_val = maxima[i + 2]   # right shoulder

        # Head must be higher than both shoulders
        if h_val <= ls_val or h_val <= rs_val:
            continue

        # Shoulders should be roughly symmetric (within 8%)
        if _pct_diff(ls_val, rs_val) > 8.0:
            continue

        # Spacing: each gap should be 10–50 bars
        if not (10 <= h_idx - ls_idx <= 50 and 10 <= rs_idx - h_idx <= 50):
            continue

        # Neckline: lowest trough between LS-H and H-RS
        left_troughs = [v for ix, v in minima if ls_idx < ix < h_idx]
        right_troughs = [v for ix, v in minima if h_idx < ix < rs_idx]
        if not left_troughs or not right_troughs:
            continue

        neckline = (min(left_troughs) + min(right_troughs)) / 2.0

        breakout = closes[-1] < neckline
        vol_conf = _volume_confirmed(volumes, n - 1) if breakout else False

        symmetry = 1.0 - _pct_diff(ls_val, rs_val) / 8.0
        head_prominence = min((h_val - max(ls_val, rs_val)) / h_val * 100, 15) / 15
        conf = 0.25 * symmetry + 0.20 * head_prominence
        conf += 0.25 if breakout else 0.0
        conf += 0.15 if vol_conf else 0.0
        conf += _recency_bonus(rs_idx, n)
        conf = min(round(conf, 3), 1.0)

        results.append(PatternSignal(
            pattern_name="Head & Shoulders",
            direction="bearish",
            confidence=conf,
            start_date=dates[ls_idx],
            end_date=dates[rs_idx],
            breakout_confirmed=breakout,
            volume_confirmation=vol_conf,
            description=(
                f"LS=${ls_val:.2f}, Head=${h_val:.2f}, RS=${rs_val:.2f}, "
                f"neckline ~${neckline:.2f}"
                f"{', breakdown confirmed' if breakout else ''}"
            ),
        ))

    return results


def _detect_inverse_head_and_shoulders(
    closes: List[float],
    lows: List[float],
    highs: List[float],
    volumes: List[float],
    dates: List[date],
) -> List[PatternSignal]:
    """
    Inverse Head & Shoulders (bullish) — three troughs where the middle
    trough (head) is lower than the two shoulders.  Breakout above the
    neckline confirms the pattern.
    """
    results: List[PatternSignal] = []
    _, minima = _find_local_extrema(lows, _EXTREMA_ORDER)
    maxima, _ = _find_local_extrema(highs, _EXTREMA_ORDER)
    n = len(closes)

    for i in range(len(minima) - 2):
        ls_idx, ls_val = minima[i]       # left shoulder
        h_idx, h_val = minima[i + 1]     # head (lowest)
        rs_idx, rs_val = minima[i + 2]   # right shoulder

        # Head must be lower than both shoulders
        if h_val >= ls_val or h_val >= rs_val:
            continue

        # Shoulders roughly symmetric (within 8%)
        if _pct_diff(ls_val, rs_val) > 8.0:
            continue

        if not (10 <= h_idx - ls_idx <= 50 and 10 <= rs_idx - h_idx <= 50):
            continue

        # Neckline: highest peak between LS-H and H-RS
        left_peaks = [v for ix, v in maxima if ls_idx < ix < h_idx]
        right_peaks = [v for ix, v in maxima if h_idx < ix < rs_idx]
        if not left_peaks or not right_peaks:
            continue

        neckline = (max(left_peaks) + max(right_peaks)) / 2.0

        breakout = closes[-1] > neckline
        vol_conf = _volume_confirmed(volumes, n - 1) if breakout else False

        symmetry = 1.0 - _pct_diff(ls_val, rs_val) / 8.0
        head_depth = min((min(ls_val, rs_val) - h_val) / min(ls_val, rs_val) * 100, 15) / 15
        conf = 0.25 * symmetry + 0.20 * head_depth
        conf += 0.25 if breakout else 0.0
        conf += 0.15 if vol_conf else 0.0
        conf += _recency_bonus(rs_idx, n)
        conf = min(round(conf, 3), 1.0)

        # Measured move: neckline + (neckline - head)
        _pat_target = round(neckline + (neckline - h_val), 2) if breakout else None
        _breakout_date = dates[n - 1] if breakout else None

        results.append(PatternSignal(
            pattern_name="Inverse Head & Shoulders",
            direction="bullish",
            confidence=conf,
            start_date=dates[ls_idx],
            end_date=dates[rs_idx],
            breakout_confirmed=breakout,
            volume_confirmation=vol_conf,
            description=(
                f"LS=${ls_val:.2f}, Head=${h_val:.2f}, RS=${rs_val:.2f}, "
                f"neckline ~${neckline:.2f}"
                f"{', breakout confirmed' if breakout else ''}"
            ),
            breakout_price=round(neckline, 2) if breakout else None,
            breakout_date=_breakout_date,
            pattern_target=_pat_target,
        ))

    return results


def _detect_bull_flag(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
    dates: List[date],
) -> List[PatternSignal]:
    """
    Bull Flag / Pennant — sharp advance (pole) followed by a tight
    consolidation channel (flag), ending with a breakout.

    Detection:
        1. Scan for a run-up of ≥8% in ≤15 bars (the pole).
        2. After the pole, look for 5–25 bars of consolidation where
           the range narrows and the slope is flat or slightly negative.
        3. If the latest close breaks above the flag high → confirmed.
    """
    results: List[PatternSignal] = []
    n = len(closes)
    if n < 30:
        return results

    # Slide a window looking for poles
    for pole_start in range(n - 30):
        for pole_len in range(5, 16):
            pole_end = pole_start + pole_len
            if pole_end >= n:
                break

            gain_pct = (closes[pole_end] - closes[pole_start]) / closes[pole_start] * 100
            if gain_pct < 8.0:
                continue

            # Look for a consolidation zone after the pole
            flag_start = pole_end
            best_flag_end = None
            best_range_ratio = float("inf")

            for flag_len in range(5, 26):
                flag_end = flag_start + flag_len
                if flag_end >= n:
                    break

                flag_highs = highs[flag_start : flag_end + 1]
                flag_lows = lows[flag_start : flag_end + 1]
                flag_range = max(flag_highs) - min(flag_lows)
                pole_range = highs[pole_end] - lows[pole_start]

                if pole_range <= 0:
                    continue

                range_ratio = flag_range / pole_range

                # Flag should be tight: range ≤ 50% of pole range
                if range_ratio <= 0.50 and range_ratio < best_range_ratio:
                    best_range_ratio = range_ratio
                    best_flag_end = flag_end

            if best_flag_end is None:
                continue

            flag_high = max(highs[flag_start : best_flag_end + 1])
            breakout = closes[-1] > flag_high and best_flag_end <= n - 1
            vol_conf = _volume_confirmed(volumes, n - 1) if breakout else False

            tightness = max(0.0, 1.0 - best_range_ratio / 0.50)
            conf = 0.25 * min(gain_pct / 15.0, 1.0) + 0.20 * tightness
            conf += 0.25 if breakout else 0.0
            conf += 0.15 if vol_conf else 0.0
            conf += _recency_bonus(best_flag_end, n)
            conf = min(round(conf, 3), 1.0)

            # Measured move: flag_high + pole height
            pole_height = closes[pole_end] - closes[pole_start]
            _pat_target = round(flag_high + pole_height, 2) if breakout else None
            _breakout_date = dates[n - 1] if breakout else None

            results.append(PatternSignal(
                pattern_name="Bull Flag",
                direction="bullish",
                confidence=conf,
                start_date=dates[pole_start],
                end_date=dates[best_flag_end],
                breakout_confirmed=breakout,
                volume_confirmation=vol_conf,
                description=(
                    f"Pole +{gain_pct:.1f}% in {pole_len} bars, "
                    f"flag range ratio {best_range_ratio:.2f}"
                    f"{', breakout confirmed' if breakout else ''}"
                ),
                breakout_price=round(flag_high, 2) if breakout else None,
                breakout_date=_breakout_date,
                pattern_target=_pat_target,
            ))

            # Only keep the best flag per pole — skip further pole_starts
            # that overlap with this detection
            break
        # After we found a pattern from this pole_start, skip ahead
        # to avoid duplicate overlapping detections
        # (the outer loop will naturally advance)

    # Deduplicate: keep the highest-confidence Bull Flag
    if results:
        results.sort(key=lambda p: p.confidence, reverse=True)
        results = results[:3]  # at most 3 bull flags

    return results


def _detect_ascending_triangle(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
    dates: List[date],
) -> List[PatternSignal]:
    """
    Ascending Triangle — flat resistance with rising support (higher lows).

    Detection:
        1. Find at least 3 highs within 2% of each other (flat resistance).
        2. Find at least 3 rising lows within the same window.
        3. Breakout above the resistance line confirms the pattern.
    """
    results: List[PatternSignal] = []
    maxima, _ = _find_local_extrema(highs, _EXTREMA_ORDER)
    _, minima = _find_local_extrema(lows, _EXTREMA_ORDER)
    n = len(closes)

    if len(maxima) < 3 or len(minima) < 3:
        return results

    # Slide a window of peaks to find flat resistance clusters
    for i in range(len(maxima) - 2):
        cluster = [maxima[i]]
        for j in range(i + 1, len(maxima)):
            if _pct_diff(maxima[j][1], cluster[0][1]) <= 2.0:
                cluster.append(maxima[j])

        if len(cluster) < 3:
            continue

        resistance = sum(v for _, v in cluster) / len(cluster)
        start_idx = cluster[0][0]
        end_idx = cluster[-1][0]

        # Find lows within this window
        window_lows = [(ix, vx) for ix, vx in minima if start_idx <= ix <= end_idx]
        if len(window_lows) < 2:
            continue

        # Check if lows are rising
        rising = all(
            window_lows[k + 1][1] > window_lows[k][1]
            for k in range(len(window_lows) - 1)
        )
        if not rising:
            continue

        breakout = closes[-1] > resistance
        vol_conf = _volume_confirmed(volumes, n - 1) if breakout else False

        touches = len(cluster)
        touch_quality = min(touches / 4.0, 1.0)  # 4+ touches = max
        conf = 0.30 * touch_quality
        conf += 0.25 if breakout else 0.0
        conf += 0.15 if vol_conf else 0.0
        conf += _recency_bonus(end_idx, n)
        conf = min(round(conf, 3), 1.0)

        # Measured move: resistance + triangle height (resistance - lowest low in window)
        window_low_vals = [vx for ix, vx in minima if start_idx <= ix <= end_idx]
        _tri_height = (resistance - min(window_low_vals)) if window_low_vals else 0.0
        _pat_target = round(resistance + _tri_height, 2) if breakout else None
        _breakout_date = dates[n - 1] if breakout else None

        results.append(PatternSignal(
            pattern_name="Ascending Triangle",
            direction="bullish",
            confidence=conf,
            start_date=dates[start_idx],
            end_date=dates[end_idx],
            breakout_confirmed=breakout,
            volume_confirmation=vol_conf,
            description=(
                f"Flat resistance ~${resistance:.2f} ({touches} touches), "
                f"rising lows"
                f"{', breakout confirmed' if breakout else ''}"
            ),
            breakout_price=round(resistance, 2) if breakout else None,
            breakout_date=_breakout_date,
            pattern_target=_pat_target,
        ))

    # Keep best
    if len(results) > 2:
        results.sort(key=lambda p: p.confidence, reverse=True)
        results = results[:2]

    return results


def _detect_descending_triangle(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
    dates: List[date],
) -> List[PatternSignal]:
    """
    Descending Triangle — flat support with declining resistance (lower highs).

    Detection mirrors ascending triangle but inverted.
    """
    results: List[PatternSignal] = []
    _, minima = _find_local_extrema(lows, _EXTREMA_ORDER)
    maxima, _ = _find_local_extrema(highs, _EXTREMA_ORDER)
    n = len(closes)

    if len(minima) < 3 or len(maxima) < 3:
        return results

    # Find flat support clusters
    for i in range(len(minima) - 2):
        cluster = [minima[i]]
        for j in range(i + 1, len(minima)):
            if _pct_diff(minima[j][1], cluster[0][1]) <= 2.0:
                cluster.append(minima[j])

        if len(cluster) < 3:
            continue

        support = sum(v for _, v in cluster) / len(cluster)
        start_idx = cluster[0][0]
        end_idx = cluster[-1][0]

        # Find highs within this window — should be declining
        window_highs = [(ix, vx) for ix, vx in maxima if start_idx <= ix <= end_idx]
        if len(window_highs) < 2:
            continue

        declining = all(
            window_highs[k + 1][1] < window_highs[k][1]
            for k in range(len(window_highs) - 1)
        )
        if not declining:
            continue

        breakout = closes[-1] < support
        vol_conf = _volume_confirmed(volumes, n - 1) if breakout else False

        touches = len(cluster)
        touch_quality = min(touches / 4.0, 1.0)
        conf = 0.30 * touch_quality
        conf += 0.25 if breakout else 0.0
        conf += 0.15 if vol_conf else 0.0
        conf += _recency_bonus(end_idx, n)
        conf = min(round(conf, 3), 1.0)

        results.append(PatternSignal(
            pattern_name="Descending Triangle",
            direction="bearish",
            confidence=conf,
            start_date=dates[start_idx],
            end_date=dates[end_idx],
            breakout_confirmed=breakout,
            volume_confirmation=vol_conf,
            description=(
                f"Flat support ~${support:.2f} ({touches} touches), "
                f"declining highs"
                f"{', breakdown confirmed' if breakout else ''}"
            ),
        ))

    if len(results) > 2:
        results.sort(key=lambda p: p.confidence, reverse=True)
        results = results[:2]

    return results


def _detect_cup_and_handle(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
    dates: List[date],
) -> List[PatternSignal]:
    """
    Cup & Handle — U-shaped recovery ("cup") followed by a small pullback
    ("handle") and then a breakout above the cup's rim.

    Detection algorithm:
        1. Find a local high (left rim), followed by a decline of ≥10%.
        2. Price then recovers to within 5% of the left rim (right rim).
        3. A small pullback of 3–10% forms the handle.
        4. Breakout above the rim on volume confirms the pattern.
        5. The cup must span at least 30 bars.
    """
    results: List[PatternSignal] = []
    maxima, _ = _find_local_extrema(highs, _EXTREMA_ORDER)
    _, minima = _find_local_extrema(lows, _EXTREMA_ORDER)
    n = len(closes)

    for pk_i in range(len(maxima)):
        rim_idx, rim_val = maxima[pk_i]

        # Scan for a trough that is ≥10% below the rim
        for tr_i in range(len(minima)):
            tr_idx, tr_val = minima[tr_i]
            if tr_idx <= rim_idx:
                continue
            depth_pct = (rim_val - tr_val) / rim_val * 100
            if depth_pct < 10.0:
                continue

            # Now look for recovery: a peak after the trough within 5% of rim
            for pk_j in range(pk_i + 1, len(maxima)):
                rr_idx, rr_val = maxima[pk_j]
                if rr_idx <= tr_idx:
                    continue

                # Cup must span ≥30 bars
                if rr_idx - rim_idx < 30:
                    continue

                # Right rim should be within 5% of left rim
                if _pct_diff(rim_val, rr_val) > 5.0:
                    continue

                # Look for handle: a small decline after right rim, 3–10%
                handle_found = False
                handle_end = rr_idx
                for hi in range(len(minima)):
                    h_idx, h_val = minima[hi]
                    if h_idx <= rr_idx:
                        continue
                    handle_depth = (rr_val - h_val) / rr_val * 100
                    if 3.0 <= handle_depth <= 10.0:
                        handle_found = True
                        handle_end = h_idx
                        break

                # Even without a handle, a cup is still meaningful
                actual_rim = max(rim_val, rr_val)
                breakout = closes[-1] > actual_rim
                vol_conf = _volume_confirmed(volumes, n - 1) if breakout else False

                # Confidence
                u_shape = min(depth_pct / 20.0, 1.0)  # deeper cup = better
                rim_match = 1.0 - _pct_diff(rim_val, rr_val) / 5.0
                conf = 0.20 * u_shape + 0.15 * rim_match
                conf += 0.10 if handle_found else 0.0
                conf += 0.25 if breakout else 0.0
                conf += 0.15 if vol_conf else 0.0
                conf += _recency_bonus(handle_end if handle_found else rr_idx, n)
                conf = min(round(conf, 3), 1.0)

                # Measured move: rim + cup depth (rim - trough)
                _cup_depth = rim_val - tr_val
                _pat_target = round(actual_rim + _cup_depth, 2) if breakout else None
                _breakout_date = dates[n - 1] if breakout else None

                results.append(PatternSignal(
                    pattern_name="Cup & Handle" if handle_found else "Cup (no handle)",
                    direction="bullish",
                    confidence=conf,
                    start_date=dates[rim_idx],
                    end_date=dates[handle_end if handle_found else rr_idx],
                    breakout_confirmed=breakout,
                    volume_confirmation=vol_conf,
                    description=(
                        f"Cup depth {depth_pct:.1f}%, rim ~${rim_val:.2f}"
                        f"{', handle present' if handle_found else ''}"
                        f"{', breakout confirmed' if breakout else ''}"
                    ),
                    breakout_price=round(actual_rim, 2) if breakout else None,
                    breakout_date=_breakout_date,
                    pattern_target=_pat_target,
                ))

                break  # only best recovery per trough
            break  # only first qualifying trough per rim

    # Keep top 2 by confidence
    if len(results) > 2:
        results.sort(key=lambda p: p.confidence, reverse=True)
        results = results[:2]

    return results


# ====================================================================== #
# MAIN ENTRY POINT                                                          #
# ====================================================================== #

def detect_all_patterns(
    bars: List[OHLCVBar],
    lookback: int = _LOOKBACK_BARS,
) -> Tuple[List[PatternSignal], List[str]]:
    """
    Scan the last *lookback* bars for all known chart patterns.

    This is the single function called by the LangGraph ``detect_patterns``
    node.

    Args:
        bars:     List of OHLCVBar objects, sorted oldest-first.
        lookback: Number of bars to scan (default 252 = ~12 months).

    Returns:
        (patterns, warnings) — *patterns* is sorted by confidence
        descending; *warnings* contains any error messages from
        sub-detectors that failed.
    """
    warnings_list: List[str] = []
    n = len(bars)

    if n < _MIN_LOOKBACK_BARS:
        warnings_list.append(
            f"Only {n} bars available; need at least {_MIN_LOOKBACK_BARS} "
            "for pattern detection. Returning empty."
        )
        return [], warnings_list

    # Trim to lookback window
    window = bars[-lookback:] if n > lookback else bars

    closes = [b.close for b in window]
    highs = [b.high for b in window]
    lows = [b.low for b in window]
    volumes = [b.volume for b in window]
    dates = [b.bar_date for b in window]

    all_patterns: List[PatternSignal] = []

    # Registry of all detectors — each returns List[PatternSignal]
    detectors = [
        ("Double Bottom", _detect_double_bottom),
        ("Double Top", _detect_double_top),
        ("Head & Shoulders", _detect_head_and_shoulders_top),
        ("Inverse H&S", _detect_inverse_head_and_shoulders),
        ("Bull Flag", _detect_bull_flag),
        ("Ascending Triangle", _detect_ascending_triangle),
        ("Descending Triangle", _detect_descending_triangle),
        ("Cup & Handle", _detect_cup_and_handle),
    ]

    for name, detector_fn in detectors:
        try:
            found = detector_fn(closes, highs, lows, volumes, dates)
            all_patterns.extend(found)
        except Exception as exc:
            logger.error("Pattern detector '%s' failed: %s", name, exc)
            warnings_list.append(
                f"Pattern detector '{name}' encountered an error: {exc}. "
                "Other detectors were not affected."
            )

    # Sort by confidence descending so the strongest patterns come first
    all_patterns.sort(key=lambda p: p.confidence, reverse=True)

    return all_patterns, warnings_list
