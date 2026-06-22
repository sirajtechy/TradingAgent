"""Steve McIntosh — concentration and pyramid overlay."""

from __future__ import annotations

from typing import List

from agents.strategies.common.market_regime import evaluate_market_regime
from agents.strategies.common.models import StrategyContext, StrategySignal

from .leader_rank import evaluate_leader_rank
from .position_tiers import map_position_tiers


def analyze(ctx: StrategyContext) -> StrategySignal:
    rank = evaluate_leader_rank(ctx)
    phoenix = ctx.phoenix_result or {}
    regime = evaluate_market_regime(ctx.spy_snapshot)
    regime_ok = bool(regime.get("regime_ok"))

    phoenix_signal = phoenix.get("signal") or "AVOID"
    phoenix_buy = phoenix_signal == "BUY"
    # Phase 2: recovery-upgrade WATCH unlocks McIntosh's starter-tier entry
    # even in weak-tape regimes (the regime check is structurally satisfied
    # by the recovery detector that fired upstream).
    phoenix_recovery_watch = (
        phoenix_signal == "WATCH"
        and phoenix.get("phoenix_entry_mode") == "recovery_upgrade"
    )
    rank_score = float(rank.get("leader_rank_score") or 0.0)

    tiers = map_position_tiers(
        leader_rank_score=rank_score,
        entry_trigger=phoenix_buy,
        phoenix_signal=phoenix_signal,
        market_regime_ok=regime_ok or phoenix_recovery_watch,
    )

    setup_detected = phoenix_buy or phoenix_signal == "WATCH"
    entry_trigger = tiers.get("position_tier") != "none" and (
        phoenix_buy or phoenix_recovery_watch
    )

    score = rank_score
    if not regime_ok:
        score *= 0.5

    disqualifiers: List[str] = []
    if not regime_ok:
        disqualifiers.append("Weak market tape — McIntosh keeps cash.")
    if rank.get("adr_pct") and rank["adr_pct"] > 10:
        disqualifiers.append(f"High ADR ({rank['adr_pct']}%) — size down.")

    if score >= 75 and entry_trigger:
        signal = "bullish"
    else:
        signal = "neutral"

    subscores = {
        "fastest_horse_rank": rank_score,
        "leader_tier": rank.get("leader_tier"),
        "atr_extension_rank": rank.get("adr_pct"),
        "starter_position_pct": tiers.get("starter_pct"),
        "pyramid_permission": tiers.get("pyramid_permission"),
    }

    return StrategySignal(
        strategy_id="mcintosh",
        ticker=ctx.ticker.upper(),
        as_of_date=ctx.as_of_date,
        regime_ok=regime_ok,
        setup_detected=setup_detected,
        setup_type="leader_concentration",
        entry_trigger=bool(entry_trigger),
        stop_logic={"method": "atr_aware_sizing", "level": None, "max_risk_pct": tiers.get("risk_per_trade_pct")},
        position_tier=str(tiers.get("position_tier") or "none"),
        confidence=round(score, 2),
        score=round(score, 2),
        signal=signal,
        disqualifiers=disqualifiers,
        subscores=subscores,
        explanation=list(rank.get("notes") or [])[:6],
        data_quality="good" if ctx.snapshot else "partial",
        warnings=[],
    )
