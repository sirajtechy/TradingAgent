"""
modes.py — Enum + single entrypoint to run CWAF for supported orchestrator modes.

Keeps callers (CLI, backtests, future services) aligned with ``ORCHESTRATOR_MODES.md``
without branching on bare strings.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from .config import OrchestratorSettings
from .fusion import fuse_signals
from .fusion_phoenix import fuse_signals_phoenix
from .models import FusionResult


class FusionMode(Enum):
    """Fusion variants that share ``FusionResult`` output shape."""

    TECH_FUND = "tech_fund"
    PHOENIX_FUND = "phoenix_fund"


def fuse_by_mode(
    mode: FusionMode,
    *,
    fund_result: Optional[Dict[str, Any]] = None,
    fund_error: Optional[str] = None,
    tech_result: Optional[Dict[str, Any]] = None,
    tech_error: Optional[str] = None,
    phoenix_result: Optional[Dict[str, Any]] = None,
    phoenix_error: Optional[str] = None,
    settings: Optional[OrchestratorSettings] = None,
) -> FusionResult:
    """
    Dispatch to ``fuse_signals`` (TA + FA) or ``fuse_signals_phoenix``.

    Unused branch arguments must be omitted or ``None``.
    ``tech_*`` applies only to :attr:`FusionMode.TECH_FUND`;
    ``phoenix_*`` only to :attr:`FusionMode.PHOENIX_FUND`.
    """
    cfg = settings or OrchestratorSettings()

    if mode is FusionMode.TECH_FUND:
        return fuse_signals(
            tech_result=tech_result,
            tech_error=tech_error,
            fund_result=fund_result,
            fund_error=fund_error,
            settings=cfg,
        )

    if mode is FusionMode.PHOENIX_FUND:
        return fuse_signals_phoenix(
            phoenix_result=phoenix_result,
            phoenix_error=phoenix_error,
            fund_result=fund_result,
            fund_error=fund_error,
            settings=cfg,
        )

    raise AssertionError(f"Unhandled mode: {mode!r}")  # pragma: no cover
