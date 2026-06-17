"""Minervini SEPA trend template (10-point checklist)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.strategies.common.features import compute_rs_rank, slope_rising, sma_at, snapshot_bars
from agents.strategies.common.models import StrategyContext


def evaluate_trend_template(ctx: StrategyContext) -> Dict[str, Any]:
    snap = ctx.snapshot
    bars = snapshot_bars(snap)
    spy_bars = snapshot_bars(ctx.spy_snapshot)
    phoenix = ctx.phoenix_result or {}

    if not bars or snap is None:
        return {
            "applicable": False,
            "pass_count": 0,
            "total": 10,
            "score_pct": 0.0,
            "checks": {},
            "notes": ["Insufficient snapshot for trend template."],
        }

    price = snap.as_of_price
    smas = snap.smas
    sma150 = sma_at(bars, 150)
    sma200 = smas.sma200
    sma200_prior = sma_at(bars, 200, offset=21)
    sma50 = smas.sma50
    sma150_prior = sma_at(bars, 150, offset=21)

    rs_rank = compute_rs_rank(bars, spy_bars) if spy_bars else None
    pct_above_low = None
    if snap.low_52w > 0:
        pct_above_low = (price - snap.low_52w) / snap.low_52w * 100.0
    pct_from_high = None
    if snap.high_52w > 0:
        pct_from_high = (snap.high_52w - price) / snap.high_52w * 100.0

    fund = ctx.fund_result or {}
    growth = (fund.get("frameworks") or {}).get("growth_profile") or {}
    eps_q = growth.get("eps_qoq_growth_pct")
    eps_y = growth.get("eps_yoy_growth_pct")
    if eps_q is None:
        exp = fund.get("experimental_score") or {}
        subs = exp.get("subscores") or {}
        if subs.get("growth") is not None and subs["growth"] >= 60:
            eps_q = 1.0
    if eps_y is None and growth.get("revenue_yoy_growth_pct") is not None:
        eps_y = growth.get("revenue_yoy_growth_pct")

    checks = {
        "price_above_150sma": sma150 is not None and price > sma150,
        "price_above_200sma": sma200 is not None and price > sma200,
        "sma150_above_200sma": sma150 is not None and sma200 is not None and sma150 > sma200,
        "sma200_rising": slope_rising(sma200, sma200_prior),
        "sma50_above_150_200": (
            sma50 is not None and sma150 is not None and sma200 is not None and sma50 > sma150 and sma50 > sma200
        ),
        "price_above_50sma": sma50 is not None and price > sma50,
        "pct_above_52w_low_30": pct_above_low is not None and pct_above_low >= 30.0,
        "within_25pct_of_52w_high": pct_from_high is not None and pct_from_high <= 25.0,
        "rs_rank_70_plus": rs_rank is not None and rs_rank >= 70.0,
        "eps_growth_recent": (eps_q is not None and eps_q > 0) or (eps_y is not None and eps_y > 0),
    }

    stage = (phoenix.get("stage") or {}).get("stage")
    if stage == 2:
        checks["stage_2_confirmed"] = True
    else:
        checks["stage_2_confirmed"] = False

    core_checks = {k: v for k, v in checks.items() if k != "stage_2_confirmed"}
    pass_count = sum(1 for v in core_checks.values() if v)
    score_pct = pass_count / len(core_checks) * 100.0

    notes: List[str] = []
    if rs_rank is not None:
        notes.append(f"RS rank vs SPY (63d): {rs_rank:.1f}")
    if stage != 2:
        notes.append(f"Phoenix stage {stage} — Minervini prefers Stage 2.")

    return {
        "applicable": True,
        "pass_count": pass_count,
        "total": len(core_checks),
        "score_pct": round(score_pct, 1),
        "checks": checks,
        "rs_rank": rs_rank,
        "notes": notes,
    }
