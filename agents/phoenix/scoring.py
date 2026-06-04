"""
scoring.py — Phoenix composite score engine.

Score range: 0–100. Explicitly NO RSI, MACD, Bollinger Bands, Stochastics.
Phoenix philosophy: price structure + volume is the only signal.

Component breakdown (matches PhoenixSettings weights)
──────────────────────────────────────────────────────
  VOLUME (40 pts max):
    vol_trend_score    (0–15):  recent 10-bar avg > prior 10-bar avg?
    breakout_vol_score (0–15):  last-bar vol / avg. 2× = full 15 pts (linear).
    base_dryup_score   (0–10):  volume contracting during base = accumulation.

  PRICE STRUCTURE / MA (30 pts max):
    above_200dma       (0 or 10): hard — 10 pts if above, 0 if below.
    ma_alignment       (0 or 8):  price > SMA20 > SMA50 > SMA200 = 8 pts.
    ma_slopes          (0–7):     +2 per rising SMA (SMA20, SMA50, SMA200).
    proximity_to_ma    (0–5):     price within 5–10% of SMA20 = setup area.

  PATTERN (20 pts max):
    pattern_confirmed  (0 or 12): both price + volume breakout confirmed.
    pattern_confidence (0–5):     pattern.confidence × 5.
    recency            (0–3):     pattern or snapshot is fresh (last 5 bars).

  STAGE (10 pts max):
    Stage 2 = 10, Stage 1 = 3, Stage 3 = 2, Stage 4 = 0.

Signal mapping:
  score ≥ 70 → BUY
  score ≥ 50 → WATCH
  score <  50 → AVOID

Public API
──────────
  build_score(snapshot, stage, pattern, settings) → (score, breakdown, signal)
"""

from __future__ import annotations

from typing import Dict, Tuple

from .config import PhoenixSettings
from .models import PatternMatch, PhoenixSnapshot, StageResult


def build_score(
    snapshot: PhoenixSnapshot,
    stage: StageResult,
    pattern: PatternMatch,
    settings: PhoenixSettings | None = None,
) -> Tuple[float, Dict[str, float], str]:
    """
    Compute the Phoenix composite score.

    Parameters
    ----------
    snapshot:  PhoenixSnapshot (bars, SMAs, vol_avg_20, price).
    stage:     StageResult from classify_stage().
    pattern:   PatternMatch from detect_all_patterns().
    settings:  PhoenixSettings; uses defaults if None.

    Returns
    -------
    (score, score_breakdown, signal)
      score:           0.0–100.0
      score_breakdown: dict with keys 'volume', 'structure', 'pattern', 'stage'
      signal:          'BUY' / 'WATCH' / 'AVOID'
    """
    if settings is None:
        settings = PhoenixSettings()

    bars       = snapshot.bars
    smas       = snapshot.smas
    price      = snapshot.as_of_price
    vol_avg    = snapshot.vol_avg_20
    last_vol   = bars[-1].volume if bars else 0.0

    # ─────────────────────────────────────────────────────────────────────
    # VOLUME component  (max 40 raw pts → scaled by weight_volume)
    # ─────────────────────────────────────────────────────────────────────

    # vol_trend_score: is recent 10-bar avg > prior 10-bar avg?
    recent_10 = _vol_avg_n(bars, 0,  10)
    prior_10  = _vol_avg_n(bars, 10, 10)
    if recent_10 and prior_10 and prior_10 > 0:
        trend_ratio = recent_10 / prior_10
        vol_trend_score = min(trend_ratio - 1.0, 1.0) * 15  # 0–15 pts
        vol_trend_score = max(vol_trend_score, 0.0)
    else:
        vol_trend_score = 0.0

    # breakout_vol_score: last-bar volume vs average (2× = full 15 pts)
    if vol_avg > 0:
        vol_multiple = last_vol / vol_avg
        breakout_vol_score = min(vol_multiple / 2.0, 1.0) * 15  # scales linearly to 2×
    else:
        breakout_vol_score = 0.0

    # base_dryup_score: volume contracting during base (last 10 vs first 10 of base)
    base_len = min(40, len(bars) - 1)
    base_bars = bars[-(base_len + 1):-1] if len(bars) > base_len + 1 else bars[:-1]
    first10 = base_bars[:10]
    last10  = base_bars[-10:] if len(base_bars) >= 20 else base_bars[len(base_bars) // 2:]
    first10_vol_avg = sum(b.volume for b in first10) / len(first10) if first10 else 0
    last10_vol_avg  = sum(b.volume for b in last10)  / len(last10)  if last10  else 0
    if first10_vol_avg > 0 and last10_vol_avg < first10_vol_avg:
        dryup_ratio = 1.0 - (last10_vol_avg / first10_vol_avg)
        base_dryup_score = min(dryup_ratio * 10, 10.0)  # 0–10 pts
    else:
        base_dryup_score = 0.0

    volume_raw = vol_trend_score + breakout_vol_score + base_dryup_score  # 0–40
    volume_pts = (volume_raw / 40.0) * (settings.weight_volume * 100)

    # ─────────────────────────────────────────────────────────────────────
    # PRICE STRUCTURE / MA component  (max 30 raw pts → scaled by weight_structure)
    # ─────────────────────────────────────────────────────────────────────

    # above_200dma (0 or 10)
    above_200 = smas.sma200 is not None and price > smas.sma200
    above_200dma_pts = 10.0 if above_200 else 0.0

    # ma_alignment (0 or 8): price > SMA20 > SMA50 > SMA200
    ma_align_pts = 8.0 if stage.ma_alignment else 0.0

    # ma_slopes (0–7): +2 per rising SMA (SMA20, SMA50, SMA200) + 1 for SMA10
    slopes = stage.ma_slopes
    ma_slope_pts = 0.0
    ma_slope_pts += 2.0 if slopes.get("sma20")  == "rising" else 0.0
    ma_slope_pts += 2.0 if slopes.get("sma50")  == "rising" else 0.0
    ma_slope_pts += 2.0 if slopes.get("sma200") == "rising" else 0.0
    ma_slope_pts += 1.0 if slopes.get("sma10")  == "rising" else 0.0

    # proximity_to_ma (0–5): price within 5–10% of SMA20 = in setup zone
    proximity_pts = 0.0
    if smas.sma20 is not None and smas.sma20 > 0:
        pct_from_20 = abs(price - smas.sma20) / smas.sma20
        if pct_from_20 <= 0.05:
            proximity_pts = 5.0   # within 5% — ideal
        elif pct_from_20 <= 0.10:
            proximity_pts = 3.0   # within 10% — acceptable
        elif pct_from_20 <= 0.15:
            proximity_pts = 1.0   # within 15% — extended

    structure_raw = above_200dma_pts + ma_align_pts + ma_slope_pts + proximity_pts  # 0–30
    structure_pts = (structure_raw / 30.0) * (settings.weight_structure * 100)

    # ─────────────────────────────────────────────────────────────────────
    # PATTERN component  (max 20 raw pts → scaled by weight_pattern)
    # ─────────────────────────────────────────────────────────────────────

    has_pattern = pattern.pattern_name != "None" and pattern.pivot_price > 0

    # pattern_confirmed (0 or 12)
    confirmed_pts = 12.0 if (has_pattern and pattern.confirmed) else 0.0

    # pattern_confidence (0–5): pattern.confidence × 5
    confidence_pts = pattern.confidence * 5.0 if has_pattern else 0.0

    # recency (0–3): if pattern is from very recent bars (heuristic: high confidence = recent)
    # We use pattern.confidence > 0.5 as a proxy for recency since we don't store bar index
    recency_pts = 3.0 if (has_pattern and pattern.confidence >= 0.5) else (1.0 if has_pattern else 0.0)

    pattern_raw = confirmed_pts + confidence_pts + recency_pts  # 0–20
    pattern_pts = (pattern_raw / 20.0) * (settings.weight_pattern * 100)

    # ─────────────────────────────────────────────────────────────────────
    # STAGE component  (max 10 raw pts → scaled by weight_stage)
    # ─────────────────────────────────────────────────────────────────────
    stage_map = {2: 10.0, 1: 3.0, 3: 2.0, 4: 0.0}
    stage_raw = stage_map.get(stage.stage, 0.0)
    stage_pts = (stage_raw / 10.0) * (settings.weight_stage * 100)

    # ─────────────────────────────────────────────────────────────────────
    # Total score
    # ─────────────────────────────────────────────────────────────────────
    total_score = volume_pts + structure_pts + pattern_pts + stage_pts
    total_score = round(min(max(total_score, 0.0), 100.0), 2)

    breakdown: Dict[str, float] = {
        "volume":    round(volume_pts, 2),
        "structure": round(structure_pts, 2),
        "pattern":   round(pattern_pts, 2),
        "stage":     round(stage_pts, 2),
        # Sub-components for transparency
        "_vol_trend":       round(vol_trend_score, 2),
        "_breakout_vol":    round(breakout_vol_score, 2),
        "_base_dryup":      round(base_dryup_score, 2),
        "_above_200dma":    above_200dma_pts,
        "_ma_alignment":    ma_align_pts,
        "_ma_slopes":       ma_slope_pts,
        "_proximity_ma20":  proximity_pts,
        "_pattern_confirm": confirmed_pts,
        "_pattern_conf":    round(confidence_pts, 2),
        "_pattern_recency": recency_pts,
        "_stage_raw":       stage_raw,
    }

    # ─────────────────────────────────────────────────────────────────────
    # Signal mapping
    # ─────────────────────────────────────────────────────────────────────
    if total_score >= settings.buy_threshold:
        signal = "BUY"
    elif total_score >= settings.watch_threshold:
        signal = "WATCH"
    else:
        signal = "AVOID"

    return total_score, breakdown, signal


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _vol_avg_n(bars, offset: int, period: int) -> float | None:
    """Average volume of `period` bars starting `offset` bars from the end."""
    end   = len(bars) - offset
    start = end - period
    if start < 0 or end <= 0:
        return None
    window = bars[start:end]
    if not window:
        return None
    return sum(b.volume for b in window) / len(window)
