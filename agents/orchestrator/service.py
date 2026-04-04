"""
service.py — Public API for the orchestrator agent.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .config import OrchestratorSettings
from .graph import build_graph
from .models import FusionResult


def analyze_ticker(
    ticker: str,
    as_of_date: Optional[str] = None,
    settings: Optional[OrchestratorSettings] = None,
) -> Dict[str, Any]:
    """
    Run both technical and fundamental analysis, then fuse the results.

    Returns a dict with keys:
        ticker, analysis_date, final_signal, final_confidence,
        orchestrator_score, conflict_detected, conflict_resolution,
        weights_applied, tech_output, fund_output, text_report
    """
    cfg = settings or OrchestratorSettings()
    graph = build_graph(cfg).compile()

    state = graph.invoke({
        "ticker": ticker,
        "analysis_date": as_of_date,
    })

    fusion: FusionResult = state["fusion"]
    return {
        "ticker": state["ticker"],
        "analysis_date": as_of_date,
        "final_signal": fusion.final_signal,
        "final_confidence": fusion.final_confidence,
        "orchestrator_score": fusion.orchestrator_score,
        "conflict_detected": fusion.conflict_detected,
        "conflict_resolution": fusion.conflict_resolution,
        "weights_applied": fusion.weights_applied,
        "tech_output": _agent_output_to_dict(fusion.tech_output),
        "fund_output": _agent_output_to_dict(fusion.fund_output),
        "tech_error": fusion.tech_error,
        "fund_error": fusion.fund_error,
        "note": fusion.note,
        "text_report": state.get("text_report", ""),
    }


def _agent_output_to_dict(out) -> Optional[Dict[str, Any]]:
    if out is None:
        return None
    return {
        "signal": out.signal,
        "score": out.score,
        "band": out.band,
        "confidence": out.confidence,
        "computed_confidence": out.computed_confidence,
        "subscores": out.subscores,
        "data_quality": out.data_quality,
        "adx_confidence": out.adx_confidence,
    }
