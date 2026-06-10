"""
modes.py — Enum + single entrypoint to run CWAF for supported orchestrator modes.

Keeps callers (CLI, backtests, future services) aligned with ``ORCHESTRATOR_MODES.md``
without branching on bare strings.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from .config import OrchestratorSettings
from .fusion_phoenix import fuse_signals_phoenix
from .models import FusionResult


class FusionMode(Enum):
    """Fusion variants that share ``FusionResult`` output shape."""

    PHOENIX_FUND = "phoenix_fund"
    FULL_CONTEXT = "full_context"


def fuse_by_mode(
    mode: FusionMode,
    *,
    fund_result: Optional[Dict[str, Any]] = None,
    fund_error: Optional[str] = None,
    phoenix_result: Optional[Dict[str, Any]] = None,
    phoenix_error: Optional[str] = None,
    agent_envelopes: Optional[Dict[str, Dict[str, Any]]] = None,
    market_summary_native: Optional[Dict[str, Any]] = None,
    settings: Optional[OrchestratorSettings] = None,
) -> FusionResult:
    """
    Dispatch to Phoenix+FA or full-context fusion.

    ``FULL_CONTEXT`` requires ``agent_envelopes`` with intelligence agent outputs.
    """
    cfg = settings or OrchestratorSettings()

    if mode is FusionMode.PHOENIX_FUND:
        return fuse_signals_phoenix(
            phoenix_result=phoenix_result,
            phoenix_error=phoenix_error,
            fund_result=fund_result,
            fund_error=fund_error,
            settings=cfg,
        )

    if mode is FusionMode.FULL_CONTEXT:
        from .fusion_full import fuse_signals_full

        return fuse_signals_full(
            phoenix_result=phoenix_result or {},
            fund_result=fund_result or {},
            agent_envelopes=agent_envelopes or {},
            market_summary_native=market_summary_native,
            phoenix_error=phoenix_error,
            fund_error=fund_error,
            settings=cfg,
        )

    raise AssertionError(f"Unhandled mode: {mode!r}")  # pragma: no cover
