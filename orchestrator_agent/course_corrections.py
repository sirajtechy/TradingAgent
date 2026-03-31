"""
course_corrections.py — Step 3: 4 concrete course correction rules.

Rule 1: Dynamic Weight Adjustment (ADX-based)
Rule 2: Conflict Override Logic (raise abstain threshold)
Rule 3: Trailing Stop Refinement (3% hard floor)
Rule 4: Regime Detection Filter (VIX/volatility gate)

These layer on top of the existing CWAF fusion without breaking it.
Each rule is a pure function that takes a FusionResult + market context
and may override the final_signal / final_confidence.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .config import OrchestratorSettings
from .models import FusionResult


# ─────────────────────────────────────────────────────────────────────────────
# Rule 1 — Dynamic Weight Adjustment (ADX-based)
# ─────────────────────────────────────────────────────────────────────────────

ADX_STRONG_TREND = 25.0   # ADX > 25 → trending, trust tech more
ADX_WEAK_TREND   = 15.0   # ADX < 15 → choppy, trust fund more


def apply_adx_weight_adjustment(
    result: FusionResult,
    adx: Optional[float],
    settings: OrchestratorSettings,
) -> FusionResult:
    """
    Rule 1: When ADX is available, dynamically shift tech/fund weights.

    ADX > 25 (trending): tech weight ↑ to 0.65, fund weight ↓ to 0.35
    ADX < 15 (choppy):   tech weight ↓ to 0.25, fund weight ↑ to 0.75
    Otherwise:           keep existing weights

    Re-computes the orchestrator score with new weights.
    """
    if adx is None:
        return result

    tech_out = result.tech_output
    fund_out = result.fund_output
    if tech_out is None or fund_out is None:
        return result

    existing_weights = result.weights_applied.copy()
    tw = existing_weights.get("tech", 0.5)
    fw = existing_weights.get("fund", 0.5)

    if adx > ADX_STRONG_TREND:
        new_tw, new_fw = min(tw * 1.35, 0.85), max(fw * 0.70, 0.15)
    elif adx < ADX_WEAK_TREND:
        new_tw, new_fw = max(tw * 0.55, 0.20), min(fw * 1.45, 0.80)
    else:
        return result  # neutral zone — no adjustment

    # Normalise
    total = new_tw + new_fw
    new_tw, new_fw = new_tw / total, new_fw / total

    new_score = new_tw * tech_out.score + new_fw * fund_out.score

    # Reapply band thresholds
    new_signal = _score_to_signal(new_score, settings)

    return FusionResult(
        final_signal=new_signal,
        final_confidence=result.final_confidence,
        orchestrator_score=round(new_score, 2),
        conflict_detected=result.conflict_detected,
        conflict_resolution=result.conflict_resolution,
        weights_applied={"tech": round(new_tw, 3), "fund": round(new_fw, 3)},
        tech_output=tech_out,
        fund_output=fund_out,
        tech_error=result.tech_error,
        fund_error=result.fund_error,
        note=f"{result.note or ''} | Rule1:ADX={adx:.1f}→weights({new_tw:.2f},{new_fw:.2f})",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 2 — Conflict Override Logic
# ─────────────────────────────────────────────────────────────────────────────

CONFLICT_ABSTAIN_GAP   = 0.10   # gap < 0.10 → abstain (downgraded from 0.15)
CONFLICT_MIN_SCORE_GAP = 8.0    # score gap < 8 pts → abstain


def apply_conflict_override(
    result: FusionResult,
    settings: OrchestratorSettings,
) -> FusionResult:
    """
    Rule 2: Tighten conflict resolution — abstain more aggressively.

    If conflict was detected and the winning agent's lead is narrow
    (confidence gap < 0.10  OR  score gap < 8 pts), override to neutral.

    RCA finding: weak dominant signals still fire under old gap=0.15 threshold.
    This rule raises the bar; only clear winners get to fire.
    """
    if not result.conflict_detected:
        return result

    tech_out = result.tech_output
    fund_out = result.fund_output
    if tech_out is None or fund_out is None:
        return result

    conf_gap = abs(tech_out.computed_confidence - fund_out.computed_confidence)
    score_gap = abs(tech_out.score - fund_out.score)

    if conf_gap < CONFLICT_ABSTAIN_GAP or score_gap < CONFLICT_MIN_SCORE_GAP:
        return FusionResult(
            final_signal="neutral",
            final_confidence=min(result.final_confidence * 0.70, 0.45),
            orchestrator_score=50.0,
            conflict_detected=True,
            conflict_resolution="abstained_narrow_gap",
            weights_applied=result.weights_applied,
            tech_output=tech_out,
            fund_output=fund_out,
            tech_error=result.tech_error,
            fund_error=result.fund_error,
            note=f"{result.note or ''} | Rule2:conflict_override→neutral (gap={conf_gap:.2f}/{score_gap:.1f})",
        )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Rule 3 — Trailing Stop Refinement
# ─────────────────────────────────────────────────────────────────────────────

TRAILING_STOP_PCT = 3.0   # 3% adverse move within a period → score penalty


def apply_trailing_stop_filter(
    result: FusionResult,
    intra_period_drawdown_pct: Optional[float],
    settings: OrchestratorSettings,
) -> FusionResult:
    """
    Rule 3: If intra-period drawdown exceeds 3%, penalise confidence.

    Timing errors (RCA Category 2) are misses on small moves.
    By detecting that price moved adversely ≥ 3% intra-period, we
    downgrade the signal's confidence, narrowing the conviction band
    and helping the system abstain on borderline calls retroactively.

    In live trading this would trigger an early exit.
    In backtest this discounts the signal confidence.
    """
    if intra_period_drawdown_pct is None:
        return result

    if abs(intra_period_drawdown_pct) >= TRAILING_STOP_PCT:
        discounted_conf = result.final_confidence * 0.65
        note = (
            f"{result.note or ''} | Rule3:trailing_stop_triggered "
            f"(drawdown={intra_period_drawdown_pct:.1f}%)"
        )
        return FusionResult(
            final_signal=result.final_signal,
            final_confidence=round(discounted_conf, 4),
            orchestrator_score=result.orchestrator_score,
            conflict_detected=result.conflict_detected,
            conflict_resolution=result.conflict_resolution,
            weights_applied=result.weights_applied,
            tech_output=result.tech_output,
            fund_output=result.fund_output,
            tech_error=result.tech_error,
            fund_error=result.fund_error,
            note=note,
        )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Rule 4 — Regime Detection Filter
# ─────────────────────────────────────────────────────────────────────────────

HIGH_VOLATILITY_THRESHOLD = 25.0   # 30-day realised vol % → high regime
DOWNTREND_THRESHOLD       = -5.0   # 3-month price change % → downtrend


def apply_regime_filter(
    result: FusionResult,
    realised_vol_30d: Optional[float],
    price_change_3m: Optional[float],
    settings: OrchestratorSettings,
) -> FusionResult:
    """
    Rule 4: Block bullish signals in high-volatility / downtrend regimes.

    If both conditions hold:
      - 30-day realised volatility > 25%
      - 3-month price change < -5%

    Then downgrade any bullish signal to neutral.

    RCA finding: Market Regime Errors cluster in months with high vol
    and sustained downtrends. The old CWAF had no regime awareness.
    """
    if result.final_signal != "bullish":
        return result

    if realised_vol_30d is None or price_change_3m is None:
        return result

    high_vol = realised_vol_30d > HIGH_VOLATILITY_THRESHOLD
    downtrend = price_change_3m < DOWNTREND_THRESHOLD

    if high_vol and downtrend:
        return FusionResult(
            final_signal="neutral",
            final_confidence=result.final_confidence * 0.60,
            orchestrator_score=50.0,  # clamp to neutral band
            conflict_detected=result.conflict_detected,
            conflict_resolution=result.conflict_resolution,
            weights_applied=result.weights_applied,
            tech_output=result.tech_output,
            fund_output=result.fund_output,
            tech_error=result.tech_error,
            fund_error=result.fund_error,
            note=(
                f"{result.note or ''} | Rule4:regime_filter_triggered "
                f"(vol={realised_vol_30d:.1f}%, 3m_chg={price_change_3m:.1f}%)"
            ),
        )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Composite: apply all 4 rules in sequence
# ─────────────────────────────────────────────────────────────────────────────

def apply_all_corrections(
    result: FusionResult,
    settings: OrchestratorSettings,
    *,
    adx: Optional[float] = None,
    intra_period_drawdown_pct: Optional[float] = None,
    realised_vol_30d: Optional[float] = None,
    price_change_3m: Optional[float] = None,
) -> FusionResult:
    """Apply all 4 course correction rules in order."""
    result = apply_adx_weight_adjustment(result, adx, settings)
    result = apply_conflict_override(result, settings)
    result = apply_trailing_stop_filter(result, intra_period_drawdown_pct, settings)
    result = apply_regime_filter(result, realised_vol_30d, price_change_3m, settings)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _score_to_signal(score: float, settings: OrchestratorSettings) -> str:
    if score >= settings.bullish_threshold:
        return "bullish"
    if score < settings.bearish_threshold:
        return "bearish"
    return "neutral"
