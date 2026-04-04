"""
models.py — Data structures for the orchestrator agent.

Uses TypedDict for LangGraph state and frozen dataclasses for output.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# LangGraph state schema
# ---------------------------------------------------------------------------

class OrchestratorState(TypedDict, total=False):
    """Mutable state threaded through the LangGraph pipeline."""

    ticker: str
    analysis_date: str

    # Sub-agent raw outputs
    tech_result: Optional[Dict[str, Any]]
    tech_error: Optional[str]
    fund_result: Optional[Dict[str, Any]]
    fund_error: Optional[str]

    # Fusion outputs
    fusion: Optional["FusionResult"]

    # Final report
    text_report: Optional[str]


# ---------------------------------------------------------------------------
# Frozen result objects
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class AgentOutput:
    """Normalised wrapper around a sub-agent's evaluation dict."""

    signal: str           # "bullish" | "neutral" | "bearish"
    score: float          # 0–100 composite/experimental score
    band: str             # "strong" | "good" | "mixed_positive" | "mixed" | "weak"
    confidence: str       # "high" | "medium" | "low"  (agent-reported)
    computed_confidence: float  # 0.0–1.0 from agent_confidence()
    subscores: Dict[str, Any] = dataclasses.field(default_factory=dict)
    data_quality: Optional[str] = None  # "good" | "fair" | "poor" (fund only)
    adx_confidence: Optional[str] = None  # "high"| "medium"| "low" (tech only)


BAND_TO_SIGNAL = {
    "strong": "bullish",
    "good": "bullish",
    "mixed_positive": "bullish",
    "mixed": "neutral",
    "weak": "bearish",
}


@dataclasses.dataclass(frozen=True)
class FusionResult:
    """Output of the CWAF fusion engine."""

    final_signal: str           # "bullish" | "neutral" | "bearish"
    final_confidence: float     # 0.0–1.0
    orchestrator_score: float   # 0–100
    conflict_detected: bool
    conflict_resolution: Optional[str]
    weights_applied: Dict[str, float]  # {"tech": w, "fund": w}

    tech_output: Optional[AgentOutput] = None
    fund_output: Optional[AgentOutput] = None
    tech_error: Optional[str] = None
    fund_error: Optional[str] = None
    note: Optional[str] = None
