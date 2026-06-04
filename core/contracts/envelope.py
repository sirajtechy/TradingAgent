"""
Agent envelope builders — re-export from orchestrator (implementation unchanged).

New code should import from ``core.contracts.envelope``; orchestrator keeps the source.
"""

from agents.orchestrator.agent_envelope import (
    envelope_from_fundamental,
    envelope_from_phoenix,
    envelope_from_technical,
)

__all__ = [
    "envelope_from_phoenix",
    "envelope_from_fundamental",
    "envelope_from_technical",
]
