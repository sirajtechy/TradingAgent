"""Shared models for trader strategy modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agents.phoenix.models import OHLCVBar, PhoenixSnapshot


@dataclass
class StrategyContext:
    """Point-in-time inputs shared across strategy analyzers."""

    ticker: str
    as_of_date: str
    snapshot: Optional[PhoenixSnapshot] = None
    spy_snapshot: Optional[PhoenixSnapshot] = None
    phoenix_result: Optional[Dict[str, Any]] = None
    fund_result: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class StrategySignal:
    """Normalized output contract for all trader playbooks."""

    strategy_id: str
    ticker: str
    as_of_date: str
    regime_ok: bool
    setup_detected: bool
    setup_type: str
    entry_trigger: bool
    stop_logic: Dict[str, Any]
    position_tier: str
    confidence: float
    score: float
    signal: str
    disqualifiers: List[str] = field(default_factory=list)
    subscores: Dict[str, Any] = field(default_factory=dict)
    explanation: List[str] = field(default_factory=list)
    data_quality: str = "good"
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "ticker": self.ticker,
            "as_of_date": self.as_of_date,
            "regime_ok": self.regime_ok,
            "setup_detected": self.setup_detected,
            "setup_type": self.setup_type,
            "entry_trigger": self.entry_trigger,
            "stop_logic": self.stop_logic,
            "position_tier": self.position_tier,
            "confidence": round(self.confidence, 2),
            "score": round(self.score, 2),
            "signal": self.signal,
            "disqualifiers": list(self.disqualifiers),
            "subscores": dict(self.subscores),
            "explanation": list(self.explanation),
            "data_quality": self.data_quality,
            "warnings": list(self.warnings),
        }


def bars_from_closes(closes: List[float], *, start_date=None) -> List[OHLCVBar]:
    """Build minimal OHLCV bars for unit tests."""
    from datetime import date, timedelta

    base = start_date or date(2025, 1, 1)
    out: List[OHLCVBar] = []
    for i, c in enumerate(closes):
        d = base + timedelta(days=i)
        out.append(OHLCVBar(bar_date=d, open=c, high=c * 1.01, low=c * 0.99, close=c, volume=1_000_000))
    return out
