"""
service.py — Public API for the Geopolitics Agent.

Session-scoped agent: global geopolitical risk from FMP general/forex news.

Usage::

    from agents.geopolitics.service import analyze_market

    result = analyze_market("2026-06-01")
    print(result["signal"])
    print(result["sector_exposure"])
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from .composite_client import load_composite_client
from .config import GeopoliticsSettings, load_settings
from .graph import build_graph
from .models import GeopoliticsRequest


def analyze_market(
    as_of_date: Optional[str] = None,
    settings: Optional[GeopoliticsSettings] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Geopolitical risk analysis for US equity market at cutoff date.
    """
    resolved_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()
    cfg = settings
    if cfg is None and api_key:
        try:
            cfg = load_settings(api_key=api_key)
        except Exception:
            cfg = None
    client = load_composite_client(api_key=api_key or (cfg.api_key if cfg else None))
    if cfg is None:
        from .config import GeopoliticsSettings as GS

        cfg = GS(api_key="unused")
    graph = build_graph(client, cfg)
    state = graph.invoke({"request": GeopoliticsRequest(as_of_date=resolved_date)})
    evaluation = dict(state["evaluation"])
    evaluation["agent_id"] = "geopolitics"
    evaluation["as_of_date"] = resolved_date.isoformat()
    return evaluation
