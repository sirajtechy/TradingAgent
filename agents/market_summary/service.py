"""
service.py — Public API for the Market Summary Agent.

Session-scoped agent composing macro + Polygon market regime data.

Usage::

    from agents.market_summary.service import analyze_market

    result = analyze_market("2026-06-01")
    print(result["market_wide_signal"])
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from .config import MarketSummarySettings
from .data_client import MarketSummaryDataClient
from .graph import build_graph
from .models import MarketSummaryRequest


def analyze_market(
    as_of_date: Optional[str] = None,
    settings: Optional[MarketSummarySettings] = None,
) -> Dict[str, Any]:
    """
    Market-wide summary for swing-trade context at a cutoff date.
    """
    resolved_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()
    cfg = settings or MarketSummarySettings()
    client = MarketSummaryDataClient(cfg)
    graph = build_graph(client)
    state = graph.invoke({"request": MarketSummaryRequest(as_of_date=resolved_date)})
    evaluation = dict(state["evaluation"])
    evaluation["agent_id"] = "market_summary"
    evaluation["as_of_date"] = resolved_date.isoformat()
    return evaluation
