"""Steve McIntosh — leader ranking among Phoenix-qualified names."""

from __future__ import annotations

from agents.strategies.common.features import compute_adr_pct, compute_rs_rank, ema_at, snapshot_bars
from agents.strategies.common.models import StrategyContext


def evaluate_leader_rank(ctx: StrategyContext) -> dict:
    bars = snapshot_bars(ctx.snapshot)
    spy = snapshot_bars(ctx.spy_snapshot)
    phoenix = ctx.phoenix_result or {}

    rs = compute_rs_rank(bars, spy) if spy else None
    adr = compute_adr_pct(bars)
    phoenix_score = float(phoenix.get("score") or 0.0)
    stage = (phoenix.get("stage") or {}).get("stage")

    ema6 = ema_at(bars, 6)
    ema20 = ema_at(bars, 20)
    ema_cross = ema6 is not None and ema20 is not None and ema6 > ema20

    rank_score = phoenix_score * 0.45
    if rs is not None:
        rank_score += rs * 0.40
    if stage == 2:
        rank_score += 10.0
    if ema_cross:
        rank_score += 5.0
    if adr is not None:
        if 4.0 <= adr <= 7.0:
            rank_score += 5.0
        elif adr > 9.0:
            rank_score -= 10.0

    rank_score = max(0.0, min(rank_score, 100.0))

    tier = "C"
    if rank_score >= 80:
        tier = "A"
    elif rank_score >= 65:
        tier = "B"

    return {
        "leader_rank_score": round(rank_score, 1),
        "leader_tier": tier,
        "rs_rank": rs,
        "adr_pct": adr,
        "ema6_above_20": ema_cross,
        "notes": [
            f"Leader rank score {rank_score:.1f} (tier {tier}).",
            f"ADR {adr}%" if adr else "ADR unavailable.",
        ],
    }
