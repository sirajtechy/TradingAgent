"""Convert agent envelopes to AgentOutput for orchestrator fusion."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import OrchestratorSettings
from .fusion import agent_confidence
from .models import AgentOutput, BAND_TO_SIGNAL


def envelope_to_agent_output(
    envelope: Dict[str, Any],
    *,
    thresholds: Optional[List[float]] = None,
) -> AgentOutput:
    """Map a MULTI_AGENT_CONTRACT envelope to AgentOutput."""
    cfg = OrchestratorSettings()
    t = thresholds or list(cfg.tech_thresholds)

    score = float(envelope.get("score") or 50.0)
    signal = str(envelope.get("signal") or "neutral").lower()
    if signal not in ("bullish", "neutral", "bearish"):
        signal = "neutral"

    band = str(envelope.get("band") or "mixed")
    if band not in BAND_TO_SIGNAL:
        band = "mixed_positive" if signal == "bullish" else ("weak" if signal == "bearish" else "mixed")

    conf_label = str(envelope.get("confidence") or "medium")
    computed = agent_confidence(score, t)
    dq = envelope.get("data_quality")

    return AgentOutput(
        signal=signal,
        score=score,
        band=band,
        confidence=conf_label,
        computed_confidence=computed,
        subscores=(envelope.get("extras") or {}).get("subscores") or {},
        data_quality=dq if isinstance(dq, str) else None,
    )
