"""Position sizing — equal weight with optional tier bumps."""

from __future__ import annotations

from typing import Dict, List

from agents.portfolio.config import PortfolioRules
from agents.portfolio.models import TickerScore


def size_positions(
    selected: List[TickerScore],
    *,
    budget: float,
    rules: PortfolioRules,
    tier_map: Dict[str, str] | None = None,
) -> Dict[str, float]:
    """
    Return ticker -> dollar allocation.

    Tier bumps from config (high +20%, low -20%) when ``tier_map`` provided.
    """
    if not selected:
        return {}

    tier_map = tier_map or {}
    bumps = (rules.raw.get("position_sizing") or {}).get("tier_bumps_pct") or {}
    base = budget / len(selected)
    raw_allocs: Dict[str, float] = {}

    for row in selected:
        tier = tier_map.get(row.ticker, "medium")
        bump = float(bumps.get(tier, 0.0))
        raw_allocs[row.ticker] = base * (1.0 + bump)

    total = sum(raw_allocs.values())
    if total <= 0:
        return {t: budget / len(selected) for t in raw_allocs}

    scale = budget / total
    return {t: round(v * scale, 2) for t, v in raw_allocs.items()}


def shares_from_allocation(dollar_alloc: float, price: float) -> float:
    if price <= 0:
        return 0.0
    return max(int(dollar_alloc / price), 0)
