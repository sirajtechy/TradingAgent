"""Point-in-time policy for intelligence agents during historical backtests."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional


def _parse_as_of(as_of_date: str) -> date:
    return date.fromisoformat(str(as_of_date)[:10])


def agent_pit_status(agent_id: str, as_of_date: str) -> Dict[str, Any]:
    """
    Return whether an agent may run for a historical as_of_date without lookahead bias.

    ``allowed`` — run the agent and include in confusion matrix.
    ``abstain`` — skip agent; matrix uses neutral/abstained bucket.
    """
    aid = agent_id.strip().lower()
    as_of = _parse_as_of(as_of_date)
    days_ago = (date.today() - as_of).days

    if aid in ("phoenix", "technical", "fundamental", "minervini", "moglen", "breitstein", "mcintosh"):
        return {"allowed": True, "reason": "Polygon/FA PIT path", "data_quality": "good"}

    if aid == "macro":
        ok = bool(os.environ.get("FRED_API_KEY"))
        return {
            "allowed": ok,
            "abstain": not ok,
            "reason": "FRED observation_end=as_of_date" if ok else "Missing FRED_API_KEY",
            "data_quality": "good" if ok else "unknown",
        }

    if aid == "market_summary":
        ok = bool(os.environ.get("POLYGON_API_KEY"))
        return {
            "allowed": ok,
            "abstain": not ok,
            "reason": "Polygon bars ≤ as_of_date" if ok else "Missing POLYGON_API_KEY",
            "data_quality": "good" if ok else "unknown",
        }

    if aid == "news":
        src = (os.environ.get("NEWS_DATA_SOURCE") or "auto").lower()
        finnhub = bool(os.environ.get("FINNHUB_API_KEY"))
        if src in ("finnhub", "auto") and finnhub:
            return {"allowed": True, "reason": "Finnhub date-range API", "data_quality": "good"}
        if days_ago <= 30 and src in ("fmp", "auto"):
            return {"allowed": True, "reason": "FMP recent fetch + client filter", "data_quality": "fair"}
        return {
            "allowed": False,
            "abstain": True,
            "reason": "Use FINNHUB_API_KEY + NEWS_DATA_SOURCE=finnhub for deep history",
            "data_quality": "poor",
        }

    if aid == "insider":
        src = (os.environ.get("INSIDER_DATA_SOURCE") or "auto").lower()
        edgar = bool(os.environ.get("SEC_EDGAR_USER_AGENT"))
        if src in ("edgar", "auto") and edgar:
            return {"allowed": True, "reason": "SEC Form 4 ≤ as_of_date", "data_quality": "good"}
        if days_ago <= 30:
            return {"allowed": True, "reason": "Recent insider snapshot only", "data_quality": "fair"}
        return {
            "allowed": False,
            "abstain": True,
            "reason": "Set INSIDER_DATA_SOURCE=edgar and SEC_EDGAR_USER_AGENT",
            "data_quality": "poor",
        }

    if aid == "sentiment":
        news = agent_pit_status("news", as_of_date)
        insider = agent_pit_status("insider", as_of_date)
        allowed = news.get("allowed") or insider.get("allowed")
        return {
            "allowed": allowed,
            "abstain": not allowed,
            "reason": "Inherited from news/insider PIT quality",
            "data_quality": news.get("data_quality") if allowed else "poor",
        }

    if aid == "geopolitics":
        if days_ago <= 30:
            return {"allowed": True, "reason": "Recent FMP/yfinance headlines", "data_quality": "fair"}
        return {
            "allowed": False,
            "abstain": True,
            "reason": "No archival geopolitics feed for old dates",
            "data_quality": "poor",
        }

    if aid == "fusion_full":
        return {"allowed": True, "reason": "Computed from PIT-gated envelopes", "data_quality": "mixed"}

    return {"allowed": False, "abstain": True, "reason": f"Unknown agent {aid}", "data_quality": "unknown"}


def pit_manifest_for_date(as_of_date: str) -> Dict[str, Any]:
    """Manifest block stored on ingested runs."""
    agents = (
        "macro",
        "market_summary",
        "news",
        "insider",
        "sentiment",
        "geopolitics",
        "fusion_full",
    )
    return {
        "as_of_date": as_of_date,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "agents": {aid: agent_pit_status(aid, as_of_date) for aid in agents},
    }
