"""Sector theme attribution from portfolio trades."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from agents.portfolio.models import TradeRecord


def sector_theme_report(trades: List[TradeRecord]) -> Dict[str, Any]:
    """Summarize BUY/SELL activity and realized flow by GICS sector."""
    by_sector: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"buys": 0, "sells": 0, "buy_notional": 0.0, "sell_notional": 0.0, "tickers": set()}
    )

    for t in trades:
        sec = t.sector or "Unknown"
        bucket = by_sector[sec]
        bucket["tickers"].add(t.ticker)
        if t.action == "BUY":
            bucket["buys"] += 1
            bucket["buy_notional"] += abs(t.proceeds)
        elif t.action == "SELL":
            bucket["sells"] += 1
            bucket["sell_notional"] += abs(t.proceeds)

    themes: List[Dict[str, Any]] = []
    for sector, data in sorted(by_sector.items(), key=lambda x: x[1]["buy_notional"], reverse=True):
        themes.append(
            {
                "sector": sector,
                "buys": data["buys"],
                "sells": data["sells"],
                "buy_notional_usd": round(data["buy_notional"], 2),
                "sell_notional_usd": round(data["sell_notional"], 2),
                "net_flow_usd": round(data["buy_notional"] - data["sell_notional"], 2),
                "unique_tickers": sorted(data["tickers"]),
            }
        )

    return {"sectors": themes, "sector_count": len(themes)}
