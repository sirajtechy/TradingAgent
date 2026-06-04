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
