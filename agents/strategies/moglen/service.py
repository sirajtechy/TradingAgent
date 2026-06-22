"""Richard Moglen — regime-first momentum playbook."""

from __future__ import annotations

from typing import List

from agents.strategies.common.models import StrategyContext, StrategySignal

from .regime_guard import evaluate_regime
from .rmv import evaluate_rmv
from .setup_pack import classify_setup


def analyze(ctx: StrategyContext) -> StrategySignal:
    regime = evaluate_regime(ctx)
    rmv = evaluate_rmv(ctx)
    setup = classify_setup(ctx)
    phoenix = ctx.phoenix_result or {}

    regime_ok = bool(regime.get("regime_ok"))
    # Phase 2: Phoenix recovery-upgrade WATCH effectively satisfies Moglen's
    # regime check (the recovery detector already validated the broader market
    # turning up — index above EMA10 + rising + follow-through-day).
    recovery_watch = (
        phoenix.get("signal") == "WATCH"
        and phoenix.get("phoenix_entry_mode") == "recovery_upgrade"
    )
    effective_regime_ok = regime_ok or recovery_watch
    tight = bool(rmv.get("tight_right_side"))
    setup_detected = bool(setup.get("setup_detected"))
    setup_type = setup.get("setup_type") or "none"

    rmv15 = rmv.get("rmv15")
    aggression = float(regime.get("aggression_score") or 0.0)
    phoenix_score = float(phoenix.get("score") or 0.0)

    subscores = {
        "market_aggression": aggression,
        "rmv15": rmv15,
        "rmv_tight": 100.0 - (rmv15 or 50.0),
        "setup_quality": phoenix_score,
        "gap_pct": setup.get("gap_pct"),
    }

    score = aggression * 0.40 + subscores["rmv_tight"] * 0.25 + phoenix_score * 0.35
    if not regime_ok and not recovery_watch:
        score *= 0.65

    disqualifiers: List[str] = []
    if not regime_ok and not recovery_watch:
        disqualifiers.append("Market below rising 21 EMA — reduce new long aggression.")
    if setup_type == "none":
        disqualifiers.append("No Moglen setup pack match.")

    entry_trigger = effective_regime_ok and setup_detected and (tight or setup_type.startswith("gap")) and score >= 55.0

    if score >= 65 and effective_regime_ok and setup_detected:
        signal = "bullish"
    else:
        signal = "neutral"

    explanation: List[str] = list(regime.get("warnings") or [])
    explanation.extend(setup.get("notes") or [])
    explanation.extend(rmv.get("notes") or [])

    risk = phoenix.get("risk") or {}
    return StrategySignal(
        strategy_id="moglen",
        ticker=ctx.ticker.upper(),
        as_of_date=ctx.as_of_date,
        regime_ok=effective_regime_ok,
        setup_detected=setup_detected,
        setup_type=setup_type,
        entry_trigger=entry_trigger,
        stop_logic={
            "method": "low_of_day_or_pivot",
            "level": risk.get("stop_price"),
            "max_risk_pct": risk.get("stop_pct") or 5.0,
        },
        position_tier="starter" if entry_trigger else "none",
        confidence=round(score, 2),
        score=round(score, 2),
        signal=signal,
        disqualifiers=disqualifiers,
        subscores=subscores,
        explanation=explanation[:8],
        data_quality=regime.get("data_quality", "partial"),
        warnings=list(regime.get("warnings") or []),
    )
