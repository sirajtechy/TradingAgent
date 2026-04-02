"""
rules.py — Scoring engine for the O'Neil Technical Analysis Agent.

Responsibilities:
  1. Indicator confluence scoring (RSI + MACD + EMA-stack + Volume)
  2. Direction determination (BULLISH / BEARISH / NEUTRAL)
  3. Trade level calculation (Entry, Stop Loss, Target, Risk-Reward)
  4. Signal strength composite (0.0–1.0)
  5. Final ONeilSignal assembly and summary text generation

O'Neil trade rules applied:
  - Entry  : pivot price (breakout level of the base)
  - Stop   : 7% below entry (O'Neil's strict 7–8% sell rule)
  - Target : measured move from base depth (pivot + base_height × 1.0)
             — first target uses 1× the base height; 1.5× for upside range
  - For Stage 4 stocks: override to BEARISH regardless of patterns

Confluence grading:
  Score 4 : All four indicators align  → Strong
  Score 3 : Three align               → Moderate
  Score 2 : Two align                 → Weak
  Score 0–1: Conflicting / Neutral
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .models import BasePattern, ONeilSignal, ONeilRequest, StageResult


# ─────────────────────────────────────────────────────────────────────────────
# Confluence scoring
# ─────────────────────────────────────────────────────────────────────────────

def _compute_confluence(
    inds: Dict,
    direction: str,
) -> Tuple[int, Dict[str, bool]]:
    """
    Compute a 0–4 confluence score based on how many of the 4 key
    indicators (RSI, MACD, EMA-stack,  Volume) align with *direction*.

    Returns (score, detail_dict).
    """
    detail: Dict[str, bool] = {}
    score = 0

    # ── RSI ──────────────────────────────────────────────────────────────
    rsi = inds.get("rsi_14w")
    if rsi is not None:
        if direction == "BULLISH":
            # RSI above 50 and not heavily overbought
            rsi_ok = 50 < rsi < 80
        else:
            # RSI below 50 and not extremely oversold
            rsi_ok = rsi < 50
        detail["RSI"] = rsi_ok
        if rsi_ok:
            score += 1
    else:
        detail["RSI"] = False

    # ── MACD ─────────────────────────────────────────────────────────────
    hist = inds.get("macd_histogram")
    hist_prev = inds.get("macd_histogram_prev")
    if hist is not None:
        if direction == "BULLISH":
            # Histogram positive or turning positive (rising)
            rising = (hist_prev is not None and hist > hist_prev)
            macd_ok = hist > 0 or rising
        else:
            macd_ok = hist < 0
        detail["MACD"] = macd_ok
        if macd_ok:
            score += 1
    else:
        detail["MACD"] = False

    # ── EMA Stack ────────────────────────────────────────────────────────
    last_close = inds.get("last_close")
    ema10 = inds.get("ema_10w")
    ema21 = inds.get("ema_21w")
    ema50 = inds.get("ema_50w")
    if last_close and ema10 and ema21:
        if direction == "BULLISH":
            # Ideal: price > EMA10 > EMA21 (short-term stack)
            ema_ok = last_close > ema21 and ema10 > ema21
        else:
            # Bearish: price below both short EMAs
            ema_ok = last_close < ema21 and (ema10 is None or ema10 < ema21)
        detail["EMA"] = ema_ok
        if ema_ok:
            score += 1
    else:
        detail["EMA"] = False

    # ── Volume ───────────────────────────────────────────────────────────
    vol_ratio = inds.get("volume_ratio_10w")
    if vol_ratio is not None:
        if direction == "BULLISH":
            # Breakout volume: current week volume > 1.5× 10-week avg
            vol_ok = vol_ratio >= 1.4
        else:
            # Distribution: selling on above-average volume
            vol_ok = vol_ratio >= 1.2
        detail["Volume"] = vol_ok
        if vol_ok:
            score += 1
    else:
        detail["Volume"] = False

    return score, detail


# ─────────────────────────────────────────────────────────────────────────────
# Trade level calculation
# ─────────────────────────────────────────────────────────────────────────────

def _compute_trade_levels(
    pattern: Optional[BasePattern],
    last_close: float,
    stage: StageResult,
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Compute entry price, stop loss, target price, and risk-reward ratio.

    Entry  : pivot level from the pattern (or last_close if no pattern)
    Stop   : 7% below entry (O'Neil's hard sell rule)
    Target : entry + base_height (measured move — 100% projection)
    R/R    : (target − entry) / (entry − stop)

    Returns (entry, stop, target, rr)
    """
    if pattern is None or stage.stage in (3, 4):
        # No clear setup: return current close with protective levels only
        entry  = last_close
        stop   = round(entry * 0.93, 4)  # 7% stop
        target = round(entry * 1.20, 4)  # 20% target (arbitrary placeholder)
        rr     = round((target - entry) / (entry - stop), 2) if entry != stop else None
        return entry, stop, target, rr

    pivot = pattern.pivot_level
    entry = round(pivot, 4)

    # O'Neil: buy at the pivot, hard stop 7% below entry
    stop = round(entry * (1.0 - 0.07), 4)

    # Measured move: base depth from pivot = height above base low
    # base_depth_pct is the % from high to low of the base
    base_height = pivot * (pattern.base_depth_pct / 100.0)
    target_1x   = round(entry + base_height, 4)           # conservative
    target_15x  = round(entry + base_height * 1.5, 4)     # aggressive

    # Use 1× for late-stage / flat base, 1.5× for cup/double bottom
    if pattern.is_late_stage or pattern.name == "Flat Base":
        target = target_1x
    else:
        target = target_15x

    risk   = entry - stop
    reward = target - entry
    rr     = round(reward / risk, 2) if risk > 0 else None

    return entry, stop, target, rr


# ─────────────────────────────────────────────────────────────────────────────
# Direction determination
# ─────────────────────────────────────────────────────────────────────────────

def _determine_direction(
    inds: Dict,
    patterns: List[BasePattern],
    stage: StageResult,
) -> Tuple[str, float]:
    """
    Determine the overall direction (BULLISH / BEARISH / NEUTRAL) and
    a 0.0–1.0 signal strength.

    Priority rules:
      1. Stage 4 → force BEARISH regardless of patterns
      2. Stage 3 → cap at NEUTRAL unless very high-quality pattern
      3. Stage 2 + pattern → BULLISH
      4. No pattern + ambiguous indicators → NEUTRAL
    """

    # Stage 4: no entries allowed
    if stage.stage == 4:
        return "BEARISH", 0.75

    rsi  = inds.get("rsi_14w")
    hist = inds.get("macd_histogram")
    last = inds.get("last_close")
    e21  = inds.get("ema_21w")
    e50  = inds.get("ema_50w")

    # Count bullish indicator signals
    bull_signals = 0
    bear_signals = 0

    if rsi is not None:
        if rsi > 55:
            bull_signals += 1
        elif rsi < 45:
            bear_signals += 1

    if hist is not None:
        if hist > 0:
            bull_signals += 1
        else:
            bear_signals += 1

    if last and e21:
        if last > e21:
            bull_signals += 1
        else:
            bear_signals += 1

    if last and e50:
        if last > e50:
            bull_signals += 1
        else:
            bear_signals += 1

    total_ind = bull_signals + bear_signals
    ind_score = bull_signals / total_ind if total_ind > 0 else 0.5

    # Pattern quality bonus
    best_pattern_conf = max((p.confidence for p in patterns), default=0.0)
    has_pattern = len(patterns) > 0 and best_pattern_conf >= 0.35

    # Stage weighting
    if stage.stage == 2:
        stage_bull_bonus = 0.20
    elif stage.stage == 1:
        stage_bull_bonus = 0.05
    elif stage.stage == 3:
        stage_bull_bonus = -0.10  # caution
    else:
        stage_bull_bonus = 0.0

    adjusted_score = ind_score + stage_bull_bonus + (best_pattern_conf * 0.15 if has_pattern else 0)

    # Determine direction
    if adjusted_score >= 0.60 and (stage.stage in (2,) or has_pattern):
        direction = "BULLISH"
        strength  = min(0.95, adjusted_score * 0.9 + best_pattern_conf * 0.10)
    elif adjusted_score <= 0.40:
        direction = "BEARISH"
        strength  = min(0.90, (1 - adjusted_score) * 0.8)
    elif stage.stage == 3:
        direction = "NEUTRAL"
        strength  = 0.55
    else:
        direction = "NEUTRAL"
        strength  = 0.40 + abs(adjusted_score - 0.5) * 0.4

    # Stage 3: cap at NEUTRAL unless pattern confidence is very high
    if stage.stage == 3 and direction == "BULLISH" and best_pattern_conf < 0.65:
        direction = "NEUTRAL"
        strength  = min(strength, 0.55)

    return direction, round(strength, 4)


# ─────────────────────────────────────────────────────────────────────────────
# Summary text
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary(
    direction: str,
    pattern: Optional[BasePattern],
    stage: StageResult,
    inds: Dict,
    confluence: int,
    entry: Optional[float],
    stop: Optional[float],
    target: Optional[float],
    rr: Optional[float],
    last_close: float,
) -> str:
    parts = []

    # Direction + stage
    dir_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}.get(direction, "⚪")
    parts.append(f"{dir_emoji} {direction} | {stage.description}")

    # Pattern
    if pattern:
        late_flag = " ⚠️ LATE STAGE" if pattern.is_late_stage else ""
        vdu_flag  = " | Vol dry-up ✓" if pattern.has_volume_dry_up else ""
        parts.append(f"Pattern: {pattern.description}{late_flag}{vdu_flag}")
    else:
        parts.append("Pattern: None detected")

    # Indicators summary
    rsi  = inds.get("rsi_14w")
    hist = inds.get("macd_histogram")
    e10  = inds.get("ema_10w")
    e21  = inds.get("ema_21w")
    if rsi is not None and hist is not None:
        parts.append(
            f"RSI(14w)={rsi:.1f} | MACD hist={'↑' if hist > 0 else '↓'}{hist:+.3f} "
            f"| EMA(10)={e10:.2f}, EMA(21)={e21:.2f}" if e10 and e21 else
            f"RSI(14w)={rsi:.1f} | MACD hist={hist:+.3f}"
        )

    # Trade levels
    if entry and stop and target:
        parts.append(
            f"Entry ${entry:.2f} | Stop ${stop:.2f} (-7%) | "
            f"Target ${target:.2f} | R/R {rr:.1f}:1" if rr else
            f"Entry ${entry:.2f} | Stop ${stop:.2f} | Target ${target:.2f}"
        )

    # Confluence
    conf_label = {4: "Strong", 3: "Moderate", 2: "Weak", 1: "Weak", 0: "Conflicting"}.get(confluence, "N/A")
    parts.append(f"Confluence {confluence}/4 ({conf_label})")

    return " | ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Main evaluate function
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(
    request: ONeilRequest,
    weekly_inds: Dict,
    daily_ema200: Optional[float],
    patterns: List[BasePattern],
    stage: StageResult,
    last_close: float,
    warnings: List[str],
) -> ONeilSignal:
    """
    Assemble the complete ONeilSignal from all computed components.
    This is the single entry-point called by the graph's evaluate node.
    """

    # Enrich inds with last_close for helpers
    inds = {**weekly_inds, "last_close": last_close}

    # Direction + strength
    direction, strength = _determine_direction(inds, patterns, stage)

    # Pattern selection: best confidence
    best_pattern: Optional[BasePattern] = patterns[0] if patterns else None

    # Confluence based on determined direction
    confluence_score, confluence_detail = _compute_confluence(inds, direction)

    # Trade levels
    entry, stop, target, rr = _compute_trade_levels(best_pattern, last_close, stage)

    # Summary text
    summary = _build_summary(
        direction, best_pattern, stage, inds,
        confluence_score, entry, stop, target, rr, last_close,
    )

    # O'Neil-specific extra warnings
    if best_pattern and best_pattern.is_late_stage:
        warnings.append(
            f"Late-stage base (base #{best_pattern.base_number}) — historically lower success rate"
        )
    if stage.stage == 3:
        warnings.append("Stage 3 distribution — increased topping risk")
    if stage.stage == 4:
        warnings.append("Stage 4 downtrend — O'Neil methodology: do not buy")
    if best_pattern and best_pattern.base_depth_pct > 35:
        warnings.append(
            f"Deep base ({best_pattern.base_depth_pct:.0f}%) — may need longer repair time"
        )

    return ONeilSignal(
        ticker=request.ticker,
        as_of_date=request.as_of_date,
        direction=direction,
        signal_strength=strength,
        pattern_detected=best_pattern.description if best_pattern else None,
        pattern_confidence=best_pattern.confidence if best_pattern else 0.0,
        is_late_stage=best_pattern.is_late_stage if best_pattern else False,
        volume_dry_up=best_pattern.has_volume_dry_up if best_pattern else False,
        market_stage=stage.stage,
        stage_description=stage.description,
        last_close=last_close,
        entry_price=entry,
        stop_loss=stop,
        target_price=target,
        risk_reward_ratio=rr,
        rsi_14w=weekly_inds.get("rsi_14w"),
        macd_line=weekly_inds.get("macd_line"),
        macd_signal_line=weekly_inds.get("macd_signal_line"),
        macd_histogram=weekly_inds.get("macd_histogram"),
        ema_10w=weekly_inds.get("ema_10w"),
        ema_21w=weekly_inds.get("ema_21w"),
        ema_50w=weekly_inds.get("ema_50w"),
        ema_200d=daily_ema200,
        sma_30w=stage.sma_30w,
        volume_ratio_10w=weekly_inds.get("volume_ratio_10w"),
        confluence_score=confluence_score,
        confluence_detail=confluence_detail,
        summary=summary,
        warnings=warnings,
    )
