"""
agent_envelope.py — Build ``MULTI_AGENT_CONTRACT``-style dicts from native agent JSON.

Fusion still consumes :class:`~agents.orchestrator.models.AgentOutput`; these envelopes
support logging, manifests, dashboards, and future multi-agent tooling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.orchestrator.fusion import _extract_fund_output, _extract_tech_output
from agents.orchestrator.fusion_phoenix import _extract_phoenix_output


def envelope_from_technical(
    native: Dict[str, Any],
    *,
    thresholds: Optional[List[float]] = None,
    agent_id: str = "technical",
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    from .config import OrchestratorSettings

    t = thresholds
    if t is None:
        t = list(OrchestratorSettings().tech_thresholds)

    ao = _extract_tech_output(native, t)
    es = native.get("experimental_score") or {}
    abstain = not bool(es.get("available"))

    dq = native.get("data_quality")
    dq_label = "unknown"
    if isinstance(dq, dict) and dq.get("coverage_ratio") is not None:
        cr = float(dq["coverage_ratio"])
        dq_label = "good" if cr >= 0.8 else ("fair" if cr >= 0.5 else "poor")

    return {
        "agent_id": agent_id,
        "as_of_date": as_of_date,
        "signal": ao.signal,
        "score": ao.score,
        "confidence": ao.confidence,
        "band": ao.band,
        "abstain": abstain,
        "reason": es.get("warning"),
        "data_quality": dq_label,
        "warnings": list(native.get("warnings") or []),
        "extras": {"subscores": ao.subscores, "adx_confidence": ao.adx_confidence},
    }


def envelope_from_fundamental(
    native: Dict[str, Any],
    *,
    thresholds: Optional[List[float]] = None,
    agent_id: str = "fundamental",
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    from .config import OrchestratorSettings

    t = thresholds
    if t is None:
        t = list(OrchestratorSettings().fund_thresholds)

    ao = _extract_fund_output(native, t)
    es = native.get("experimental_score") or {}
    abstain = not bool(es.get("available"))
    dq = getattr(ao, "data_quality", None) or "unknown"

    return {
        "agent_id": agent_id,
        "as_of_date": as_of_date,
        "signal": ao.signal,
        "score": ao.score,
        "confidence": ao.confidence,
        "band": ao.band,
        "abstain": abstain,
        "reason": es.get("warning"),
        "data_quality": dq,
        "warnings": list(native.get("warnings") or []),
        "extras": {"subscores": ao.subscores},
    }


def envelope_from_phoenix(
    native: Dict[str, Any],
    *,
    thresholds: Optional[List[float]] = None,
    agent_id: str = "phoenix",
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    from .config import OrchestratorSettings

    t = thresholds
    if t is None:
        t = list(OrchestratorSettings().tech_thresholds)

    ao = _extract_phoenix_output(native, t)
    sig_raw = str(native.get("signal") or "WATCH").upper()

    return {
        "agent_id": agent_id,
        "as_of_date": as_of_date,
        "signal": ao.signal,
        "score": ao.score,
        "confidence": ao.confidence,
        "band": ao.band,
        "abstain": sig_raw == "WATCH",
        "reason": native.get("hard_filter_reason"),
        "data_quality": "good" if native.get("hard_filter_passed") else "poor",
        "warnings": list(native.get("warnings") or []),
        "extras": {
            "raw_signal": sig_raw,
            "subscores": ao.subscores,
            "pattern": native.get("pattern"),
            "stage": native.get("stage"),
            "chase_risk": (native.get("extension_guardrail") or {}).get("chase_risk"),
            "extension_metrics": (native.get("extension_guardrail") or {}).get("metrics"),
        },
    }


def envelope_from_macro(
    native: Dict[str, Any],
    *,
    agent_id: str = "macro",
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    score = float(native.get("score") or 50.0)
    return {
        "agent_id": agent_id,
        "as_of_date": as_of_date or native.get("as_of_date"),
        "signal": native.get("signal") or "neutral",
        "score": score,
        "confidence": native.get("confidence") or "medium",
        "band": native.get("band") or "mixed",
        "abstain": bool(native.get("abstain")),
        "reason": None,
        "data_quality": native.get("data_quality") or "unknown",
        "warnings": list(native.get("warnings") or []),
        "extras": {
            "bullets": list(native.get("bullets") or []),
            "metrics": native.get("metrics") or {},
            "subscores": native.get("subscores") or {},
            "data_sources": list(native.get("data_sources") or []),
        },
    }


def envelope_from_news(
    native: Dict[str, Any],
    *,
    agent_id: str = "news",
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    score = float(native.get("score") or 50.0)
    return {
        "agent_id": agent_id,
        "as_of_date": as_of_date or native.get("as_of_date"),
        "signal": native.get("signal") or "neutral",
        "score": score,
        "confidence": native.get("confidence") or "medium",
        "band": native.get("band") or "mixed",
        "abstain": bool(native.get("abstain")),
        "reason": None,
        "data_quality": native.get("data_quality") or "unknown",
        "warnings": list(native.get("warnings") or []),
        "extras": {
            "bullets": list(native.get("bullets") or []),
            "headline_count": native.get("headline_count"),
            "upgrades": native.get("upgrades"),
            "downgrades": native.get("downgrades"),
            "priority_actions": native.get("priority_actions") or [],
            "subscores": native.get("subscores") or {},
            "data_sources": list(native.get("data_sources") or []),
        },
    }


def envelope_from_insider(
    native: Dict[str, Any],
    *,
    agent_id: str = "insider",
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    score = float(native.get("score") or 50.0)
    return {
        "agent_id": agent_id,
        "as_of_date": as_of_date or native.get("as_of_date"),
        "signal": native.get("signal") or "neutral",
        "score": score,
        "confidence": native.get("confidence") or "medium",
        "band": native.get("band") or "mixed",
        "abstain": bool(native.get("abstain")),
        "reason": None,
        "data_quality": native.get("data_quality") or "unknown",
        "warnings": list(native.get("warnings") or []),
        "extras": {
            "bullets": list(native.get("bullets") or []),
            "metrics": native.get("metrics") or {},
            "subscores": native.get("subscores") or {},
            "data_sources": list(native.get("data_sources") or []),
        },
    }


def envelope_from_sentiment(
    native: Dict[str, Any],
    *,
    agent_id: str = "sentiment",
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    score = float(native.get("score") or 50.0)
    return {
        "agent_id": agent_id,
        "as_of_date": as_of_date or native.get("as_of_date"),
        "signal": native.get("signal") or "neutral",
        "score": score,
        "confidence": native.get("confidence") or "medium",
        "band": native.get("band") or "mixed",
        "abstain": bool(native.get("abstain")),
        "reason": None,
        "data_quality": native.get("data_quality") or "unknown",
        "warnings": list(native.get("warnings") or []),
        "extras": {
            "bullets": list(native.get("bullets") or []),
            "sentiment": native.get("sentiment"),
            "dimensions": native.get("dimensions") or {},
            "ohlcv_context": native.get("ohlcv_context"),
            "subscores": native.get("subscores") or {},
            "data_sources": list(native.get("data_sources") or []),
        },
    }


def envelope_from_geopolitics(
    native: Dict[str, Any],
    *,
    agent_id: str = "geopolitics",
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    score = float(native.get("score") or 50.0)
    return {
        "agent_id": agent_id,
        "as_of_date": as_of_date or native.get("as_of_date"),
        "signal": native.get("signal") or "neutral",
        "score": score,
        "confidence": native.get("confidence") or "medium",
        "band": native.get("band") or "mixed",
        "abstain": bool(native.get("abstain")),
        "reason": None,
        "data_quality": native.get("data_quality") or "unknown",
        "warnings": list(native.get("warnings") or []),
        "extras": {
            "bullets": list(native.get("bullets") or []),
            "geo_headline_count": native.get("geo_headline_count"),
            "sector_exposure": native.get("sector_exposure") or {},
            "llm_sentiment": native.get("llm_sentiment"),
            "subscores": native.get("subscores") or {},
            "data_sources": list(native.get("data_sources") or []),
        },
    }


def envelope_from_market_summary(
    native: Dict[str, Any],
    *,
    agent_id: str = "market_summary",
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "agent_id": agent_id,
        "as_of_date": as_of_date or native.get("as_of_date"),
        "signal": native.get("signal") or "neutral",
        "score": float(native.get("score") or 50.0),
        "confidence": native.get("confidence") or "medium",
        "band": native.get("band") or "mixed",
        "abstain": bool(native.get("abstain")),
        "reason": None,
        "data_quality": native.get("data_quality") or "unknown",
        "warnings": list(native.get("warnings") or []),
        "extras": {
            "bullets": list(native.get("bullets") or []),
            "market_wide_signal": native.get("market_wide_signal"),
            "vix": native.get("vix"),
            "vix_regime": native.get("vix_regime"),
            "sector_leaders": native.get("sector_leaders") or [],
            "sector_laggards": native.get("sector_laggards") or [],
            "macro": native.get("macro") or {},
            "subscores": native.get("subscores") or {},
            "data_sources": list(native.get("data_sources") or []),
        },
    }
