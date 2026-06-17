"""FRR — Find, Remove, Replace on rebalance dates."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Set, Tuple

from agents.portfolio.models import Holding, TickerScore
from agents.portfolio.universe import exit_rank_threshold


def frr_actions(
    holdings: Dict[str, Holding],
    ranked: List[TickerScore],
    *,
    exit_rank: int,
    num_stocks: int,
) -> Tuple[List[str], List[str], List[TickerScore]]:
    """
    Return (to_remove, to_hold, replacements_needed).

    Remove when rank > exit_rank. Replace with top-ranked names not held.
    """
    rank_map = {r.ticker: r for r in ranked}
    to_remove: List[str] = []
    to_hold: List[str] = []

    for sym, holding in holdings.items():
        row = rank_map.get(sym)
        if row is None or row.rank > exit_rank:
            to_remove.append(sym)
        else:
            to_hold.append(sym)

    held = set(to_hold)
    replacements: List[TickerScore] = []
    for row in ranked:
        if row.ticker in held:
            continue
        if len(held) + len(replacements) >= num_stocks:
            break
        replacements.append(row)

    return to_remove, to_hold, replacements


def rebalance_dates(start: date, end: date, day_of_month: int = 21) -> List[date]:
    """Monthly rebalance calendar (clamp day to month length)."""
    dates: List[date] = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        import calendar

        last_day = calendar.monthrange(cur.year, cur.month)[1]
        dom = min(day_of_month, last_day)
        rd = date(cur.year, cur.month, dom)
        if start <= rd <= end:
            dates.append(rd)
        # next month
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return dates
