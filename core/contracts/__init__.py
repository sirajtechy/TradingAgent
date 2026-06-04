"""Multi-agent contracts — see ``docs/MULTI_AGENT_CONTRACT.md`` and ``specs/ADR-001.md``."""

from core.contracts.envelope import (
    envelope_from_fundamental,
    envelope_from_phoenix,
    envelope_from_technical,
)
from core.contracts.fusion import FusionMode, fuse_by_mode

__all__ = [
    "FusionMode",
    "fuse_by_mode",
    "envelope_from_phoenix",
    "envelope_from_fundamental",
    "envelope_from_technical",
]
