"""
service.py — Public API for the News Analyst Agent.

Per-ticker agent: headlines, analyst grades, price target direction.

Usage::

    from agents.news.service import analyze_ticker

    result = analyze_ticker("AAPL", "2026-06-01")
    print(result["signal"])
    print(result["priority_actions"])
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

import os

from .config import NewsSettings, load_settings
from .composite_client import load_composite_client
from .graph import build_graph
from .models import NewsRequest


def analyze_ticker(
    ticker: str,
    as_of_date: Optional[str] = None,
    settings: Optional[NewsSettings] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    News + analyst activity analysis for a single ticker at cutoff date.
    """
    resolved_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()
    tk = ticker.strip().upper()
    client = load_composite_client(api_key=api_key)
    try:
        cfg = settings or load_settings(api_key=api_key)
    except Exception:
        cfg = NewsSettings(api_key=os.getenv("FMP_API_KEY") or "unused")
    graph = build_graph(client, cfg)
    state = graph.invoke({"request": NewsRequest(ticker=tk, as_of_date=resolved_date)})
    evaluation = dict(state["evaluation"])
    evaluation["agent_id"] = "news"
    evaluation["ticker"] = tk
    evaluation["as_of_date"] = resolved_date.isoformat()
    return evaluation
