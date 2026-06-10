"""
service.py — Public API for the Insider Trades Agent.

Per-ticker agent: insider buy/sell activity from FMP.

Usage::

    from agents.insider.service import analyze_ticker

    result = analyze_ticker("AAPL", "2026-06-01")
    print(result["signal"])
    print(result["metrics"])
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from .composite_client import load_composite_client
from .config import InsiderSettings, load_settings
from .graph import build_graph
from .models import InsiderRequest


def analyze_ticker(
    ticker: str,
    as_of_date: Optional[str] = None,
    settings: Optional[InsiderSettings] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Insider trading activity analysis for a single ticker at cutoff date.
    """
    resolved_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()
    tk = ticker.strip().upper()
    cfg = settings
    if cfg is None and api_key:
        try:
            cfg = load_settings(api_key=api_key)
        except Exception:
            cfg = None
    client = load_composite_client(api_key=api_key or (cfg.api_key if cfg else None))
    graph = build_graph(client)
    state = graph.invoke({"request": InsiderRequest(ticker=tk, as_of_date=resolved_date)})
    evaluation = dict(state["evaluation"])
    evaluation["agent_id"] = "insider"
    evaluation["ticker"] = tk
    evaluation["as_of_date"] = resolved_date.isoformat()
    return evaluation
