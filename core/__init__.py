"""
Shared utilities for MyTradingSpace — agent-agnostic paths, contracts, and I/O.

Agents and pipelines import from ``core``; ``core`` must not import from ``agents``.
"""

from core.paths import ROOT, TRADING_RUNS_DIR, ensure_dirs

__all__ = ["ROOT", "TRADING_RUNS_DIR", "ensure_dirs"]
