"""Models for the unified Technical Agent (Phoenix + trader strategies)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TechnicalFusion:
    """Fused technical gate output."""

    blend_signal: str
    blend_score: float
    consensus_entry_triggers: int
    consensus_total: int
    high_conviction_swing: bool
    resilience_score: float
    pass_enrichment: bool
    pass_reason: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        out = dict(self.meta)
        out.update(
            {
                "blend_signal": self.blend_signal,
                "blend_score": round(self.blend_score, 2),
                "consensus_entry_triggers": self.consensus_entry_triggers,
                "consensus_total": self.consensus_total,
                "high_conviction_swing": self.high_conviction_swing,
                "resilience_score": round(self.resilience_score, 2),
                "pass_enrichment": self.pass_enrichment,
                "pass_reason": self.pass_reason,
            }
        )
        return out


@dataclass
class TechnicalResult:
    """Native output from analyze_technical()."""

    ok: bool
    ticker: str
    as_of_date: str
    signal: str
    score: float
    confidence: str
    hard_gates_passed: bool
    hard_gate_reason: Optional[str]
    phoenix: Dict[str, Any]
    strategy_layers: Dict[str, Dict[str, Any]]
    strategy_profile: str
    technical_fusion: TechnicalFusion
    disqualifiers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data_quality: str = "good"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "agent_id": "technical",
            "ticker": self.ticker,
            "as_of_date": self.as_of_date,
            "signal": self.signal,
            "score": round(self.score, 2),
            "confidence": self.confidence,
            "hard_gates_passed": self.hard_gates_passed,
            "hard_gate_reason": self.hard_gate_reason,
            "phoenix": self.phoenix,
            "strategy_layers": self.strategy_layers,
            "strategy_profile": self.strategy_profile,
            "technical_fusion": self.technical_fusion.to_dict(),
            "disqualifiers": list(self.disqualifiers),
            "warnings": list(self.warnings),
            "data_quality": self.data_quality,
            "error": self.error,
        }
