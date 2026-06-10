"""
service.py — Public API for the Sentiment Agent.

Per-ticker aggregator: News + Insider + Macro dimensions.

Usage::

    from agents.sentiment.service import analyze_ticker

    result = analyze_ticker("AAPL", "2026-06-01")
    print(result["sentiment"])
    print(result["dimensions"])
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from .config import SentimentSettings
from .graph import build_graph
from .models import SentimentRequest


def analyze_ticker(
    ticker: str,
    as_of_date: Optional[str] = None,
    settings: Optional[SentimentSettings] = None,
) -> Dict[str, Any]:
    """
    Multi-dimension sentiment analysis for a single ticker at cutoff date.
    """
    resolved_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()
    tk = ticker.strip().upper()
    cfg = settings or SentimentSettings()
    graph = build_graph(cfg)
    state = graph.invoke({"request": SentimentRequest(ticker=tk, as_of_date=resolved_date)})
    evaluation = dict(state["evaluation"])
    evaluation["agent_id"] = "sentiment"
    evaluation["ticker"] = tk
    evaluation["as_of_date"] = resolved_date.isoformat()
    return evaluation
