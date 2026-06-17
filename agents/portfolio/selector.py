"""Top-N selection with sector concentration caps."""

from __future__ import annotations

from typing import Dict, List, Set

from agents.portfolio.config import PortfolioRules
from agents.portfolio.models import TickerScore


def select_portfolio(
    ranked: List[TickerScore],
    *,
    num_stocks: int,
    rules: PortfolioRules,
    existing: Set[str] | None = None,
) -> List[TickerScore]:
    """
    Pick up to ``num_stocks`` names respecting sector cap.

    ``existing`` tickers already held get priority if still ranked above exit threshold.
    """
    existing = existing or set()
    sector_cap_value = rules.sector_cap_pct * rules.budget
    max_per_name = rules.single_name_cap_pct * rules.budget

    selected: List[TickerScore] = []
    sector_totals: Dict[str, float] = {}
    per_name_budget = rules.budget / max(num_stocks, 1)

    # Keep existing names first (FRR hold) if they appear in ranked list
    rank_map = {r.ticker: r for r in ranked}
    for sym in sorted(existing):
        row = rank_map.get(sym)
        if row is None:
            continue
        sector = row.sector
        alloc = min(per_name_budget, max_per_name)
        if sector_totals.get(sector, 0.0) + alloc > sector_cap_value and len(selected) >= num_stocks:
            continue
        selected.append(row)
        sector_totals[sector] = sector_totals.get(sector, 0.0) + alloc
        if len(selected) >= num_stocks:
            return selected

    for row in ranked:
        if row.ticker in {s.ticker for s in selected}:
            continue
        if len(selected) >= num_stocks:
            break
        alloc = min(per_name_budget, max_per_name)
        sector = row.sector
        if sector_totals.get(sector, 0.0) + alloc > sector_cap_value:
            continue
        selected.append(row)
        sector_totals[sector] = sector_totals.get(sector, 0.0) + alloc

    return selected
