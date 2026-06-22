"""Envelope adapter for unified Technical Agent native output."""

from __future__ import annotations

from typing import Any, Dict, Optional


def envelope_from_unified_technical(
    native: Dict[str, Any],
    *,
    agent_id: str = "technical",
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Map ``analyze_technical()`` output to MULTI_AGENT_CONTRACT envelope."""
    fusion = native.get("technical_fusion") or {}
    phoenix = native.get("phoenix") or {}
    abstain = not bool(fusion.get("pass_enrichment")) and native.get("signal") == "neutral"

    return {
        "agent_id": agent_id,
        "as_of_date": as_of_date or native.get("as_of_date"),
        "signal": native.get("signal") or "bearish",
        "score": float(native.get("score") or 0.0),
        "confidence": native.get("confidence") or "low",
        "band": _score_band(float(native.get("score") or 0.0)),
        "abstain": abstain,
        "reason": fusion.get("pass_reason"),
        "data_quality": native.get("data_quality") or "unknown",
        "warnings": list(native.get("warnings") or []),
        "extras": {
            "hard_gates_passed": native.get("hard_gates_passed"),
            "hard_gate_reason": native.get("hard_gate_reason"),
            "strategy_profile": native.get("strategy_profile"),
            "technical_fusion": fusion,
            "strategy_layers": {
                sid: {
                    "signal": layer.get("signal"),
                    "score": layer.get("score"),
                    "entry_trigger": layer.get("entry_trigger"),
                    "regime_ok": layer.get("regime_ok"),
                }
                for sid, layer in (native.get("strategy_layers") or {}).items()
            },
            "phoenix_signal": phoenix.get("signal"),
            "phoenix_score": phoenix.get("score"),
            "pattern": phoenix.get("pattern"),
            "stage": phoenix.get("stage"),
            "disqualifiers": list(native.get("disqualifiers") or []),
        },
    }


def _score_band(score: float) -> str:
    if score >= 75:
        return "strong"
    if score >= 55:
        return "good"
    if score >= 40:
        return "mixed"
    return "weak"
