"""Lance Breitstein — execution-state features."""

from __future__ import annotations

from typing import List

from agents.strategies.common.models import StrategyContext, StrategySignal

from .trend_character import evaluate_trend_character
from .vwap_context import evaluate_vwap_context


def analyze(ctx: StrategyContext) -> StrategySignal:
    vwap = evaluate_vwap_context(ctx)
    trend = evaluate_trend_character(ctx)
    phoenix = ctx.phoenix_result or {}

    rangebound = bool(trend.get("rangebound"))
    above_vwap = vwap.get("above_vwap")
    steadily_below = vwap.get("steadily_below_vwap")
    character = trend.get("character") or "unknown"

    disqualifiers: List[str] = []
    if rangebound:
        disqualifiers.append("Rangebound — avoid per Breitstein rules.")
    if steadily_below and not above_vwap:
        disqualifiers.append("Steadily below VWAP — no long unless capitulation.")

    capitulation = character == "capitulatory"
    if steadily_below and not capitulation:
        disqualifiers.append("Below VWAP without capitulation reversal.")

    subscores = {
        "above_vwap_persistence": 100.0 if above_vwap else 20.0,
        "trend_alignment": 80.0 if character == "trending" else 40.0,
        "rangebound_penalty": 0.0 if not rangebound else 50.0,
        "capitulation_reversal": 90.0 if capitulation else 30.0,
    }

    score = (
        subscores["above_vwap_persistence"] * 0.35
        + subscores["trend_alignment"] * 0.35
        + subscores["capitulation_reversal"] * 0.20
        - subscores["rangebound_penalty"] * 0.10
    )
    score = max(0.0, min(score, 100.0))

    phoenix_buy = phoenix.get("signal") == "BUY"
    # Phase 2: accept Phoenix recovery-upgrade WATCH as an alternate gateway.
    # Recovery setups are reversal entries by definition — Phoenix will never
    # call them BUY (BUY = full trend continuation). Require tighter score
    # to compensate for the lower-conviction setup type.
    phoenix_recovery_watch = (
        phoenix.get("signal") == "WATCH"
        and phoenix.get("phoenix_entry_mode") == "recovery_upgrade"
    )
    standard_trigger = phoenix_buy and above_vwap and not rangebound and score >= 60.0
    recovery_trigger = (
        phoenix_recovery_watch and above_vwap and not rangebound and score >= 65.0
    )
    entry_trigger = bool(standard_trigger or recovery_trigger)

    if entry_trigger:
        signal = "bullish"
    else:
        signal = "neutral"

    explanation = list(vwap.get("notes") or []) + list(trend.get("notes") or [])

    return StrategySignal(
        strategy_id="breitstein",
        ticker=ctx.ticker.upper(),
        as_of_date=ctx.as_of_date,
        regime_ok=not rangebound,
        setup_detected=phoenix_buy,
        setup_type="vwap_confirmation" if above_vwap else "timing_pending",
        entry_trigger=entry_trigger,
        stop_logic={"method": "invalidation_low", "level": None, "max_risk_pct": 5.0},
        position_tier="starter" if entry_trigger else "none",
        confidence=round(score, 2),
        score=round(score, 2),
        signal=signal,
        disqualifiers=disqualifiers,
        subscores=subscores,
        explanation=explanation[:8],
        data_quality="partial" if vwap.get("applicable") else "unavailable",
        warnings=["Daily VWAP proxy only — intraday data improves Breitstein layer."],
    )
