"""
Agent envelope builders — re-export from orchestrator (implementation unchanged).

New code should import from ``core.contracts.envelope``; orchestrator keeps the source.
"""

from agents.orchestrator.agent_envelope import (
    envelope_from_fundamental,
    envelope_from_geopolitics,
    envelope_from_insider,
    envelope_from_macro,
    envelope_from_market_summary,
    envelope_from_news,
    envelope_from_phoenix,
    envelope_from_sentiment,
    envelope_from_technical,
)

__all__ = [
    "envelope_from_phoenix",
    "envelope_from_fundamental",
    "envelope_from_technical",
    "envelope_from_macro",
    "envelope_from_market_summary",
    "envelope_from_news",
    "envelope_from_insider",
    "envelope_from_sentiment",
    "envelope_from_geopolitics",
]
