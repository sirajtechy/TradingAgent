"""
service.py — Public API for the Macroeconomics Agent.

Session-scoped agent (market-wide, not per ticker).

Usage::

    from agents.macro.service import analyze_market

    result = analyze_market("2026-06-01")
    print(result["signal"])   # bullish / neutral / bearish
    print(result["score"])    # 0–100
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from .composite_client import CompositeMacroClient
from .graph import build_graph
from .models import MacroRequest


def analyze_market(
    as_of_date: Optional[str] = None,
    settings: Optional[MacroSettings] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Macroeconomic backdrop for ~1-month swing trades at a cutoff date.
    """
    resolved_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()
    client = CompositeMacroClient()
    graph = build_graph(client)
    state = graph.invoke({"request": MacroRequest(as_of_date=resolved_date)})
    evaluation = dict(state["evaluation"])
    evaluation["agent_id"] = "macro"
    evaluation["as_of_date"] = resolved_date.isoformat()
    return evaluation
