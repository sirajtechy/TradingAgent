"""Minervini SEPA strategy module."""

from __future__ import annotations

from typing import List

from agents.strategies.common.models import StrategyContext, StrategySignal

from .catalyst import evaluate_catalyst
from .chase_guard import evaluate_chase_guard
from .trend_template import evaluate_trend_template
from .vcp_quality import evaluate_vcp_quality


def analyze(ctx: StrategyContext) -> StrategySignal:
    phoenix = ctx.phoenix_result or {}
    ticker = ctx.ticker.upper()
    as_of = ctx.as_of_date

    template = evaluate_trend_template(ctx)
    vcp = evaluate_vcp_quality(phoenix)
    catalyst = evaluate_catalyst(ctx.fund_result)
    chase = evaluate_chase_guard(phoenix)

    disqualifiers: List[str] = []
    if not template.get("checks", {}).get("stage_2_confirmed", False):
        stage = (phoenix.get("stage") or {}).get("stage")
        if stage and stage != 2:
            disqualifiers.append(f"Not Stage 2 (stage={stage}).")
    if chase.get("invalid_if_chasing"):
        disqualifiers.append("Chasing: price extended above pivot threshold.")
    if template.get("pass_count", 0) < 6:
        disqualifiers.append(f"Trend template weak ({template.get('pass_count')}/10).")

    subscores = {
        "trend_template": template.get("score_pct", 0.0),
        "trend_template_pass_count": template.get("pass_count", 0),
        "vcp_quality": vcp.get("score", 0.0),
        "catalyst": catalyst.get("score", 0.0),
        "chase_penalty": chase.get("penalty", 0.0),
        "pivot_distance_pct": chase.get("pct_from_pivot"),
        "rs_rank": template.get("rs_rank"),
    }

    raw = (
        subscores["trend_template"] * 0.35
        + subscores["vcp_quality"] * 0.35
        + subscores["catalyst"] * 0.20
        + (100.0 - subscores["chase_penalty"]) * 0.10
    )
    score = max(0.0, min(raw, 100.0))

    setup_detected = bool(vcp.get("setup_detected"))
    setup_type = vcp.get("pattern_name") or "none"
    stage2 = template.get("checks", {}).get("stage_2_confirmed", False)
    entry_trigger = setup_detected and stage2 and not chase.get("invalid_if_chasing") and score >= 60.0

    if score >= 70 and not disqualifiers:
        signal = "bullish"
    elif score >= 50:
        signal = "neutral"
    else:
        signal = "bearish"

    risk = phoenix.get("risk") or {}
    stop_logic = {
        "method": "max_7_5_pct_from_entry",
        "level": risk.get("stop_price"),
        "max_risk_pct": risk.get("stop_pct") or 7.5,
    }

    explanation: List[str] = []
    explanation.append(f"Trend template: {template.get('pass_count')}/10 checks pass.")
    explanation.extend(vcp.get("notes") or [])
    explanation.extend(catalyst.get("notes") or [])
    if chase.get("summary"):
        explanation.append(str(chase["summary"]))

    warnings = list(ctx.warnings)
    if chase.get("chase_risk") == "elevated":
        warnings.append("Elevated chase risk — consider smaller size or pullback entry.")

    data_quality = "good" if ctx.snapshot else "partial"

    return StrategySignal(
        strategy_id="minervini",
        ticker=ticker,
        as_of_date=as_of,
        regime_ok=stage2,
        setup_detected=setup_detected,
        setup_type=str(setup_type).lower().replace(" ", "_"),
        entry_trigger=entry_trigger,
        stop_logic=stop_logic,
        position_tier="starter" if entry_trigger else "none",
        confidence=score,
        score=score,
        signal=signal,
        disqualifiers=disqualifiers,
        subscores=subscores,
        explanation=explanation[:8],
        data_quality=data_quality,
        warnings=warnings,
    )
