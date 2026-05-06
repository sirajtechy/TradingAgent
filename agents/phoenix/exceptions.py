"""
exceptions.py — Custom exceptions for the Phoenix Agent.

Hierarchy
─────────
  PhoenixAgentError          — base for all Phoenix errors
    ├── HardFilterRejected   — ticker failed 200DMA or 52w-low filter (not an error, expected path)
    ├── StageFilterRejected  — ticker is Stage 1, 3, or 4 (expected path when stage2_only=True)
    ├── DataUnavailableError — Polygon returned no bars or too few bars
    └── InsufficientDataError — fewer bars than required for SMA warm-up
"""

from __future__ import annotations


class PhoenixAgentError(RuntimeError):
    """Base exception for all Phoenix Agent errors."""


class HardFilterRejected(PhoenixAgentError):
    """
    Raised when a ticker fails one of the two mandatory hard pre-filters:
      1. Price not above the 200-day SMA
      2. Price less than 50% above the 52-week low

    This is an expected, non-exceptional outcome — it is raised so the
    LangGraph pipeline can fast-exit cleanly without running downstream nodes.
    """

    def __init__(self, ticker: str, reason: str) -> None:
        self.ticker = ticker
        self.reason = reason
        super().__init__(f"{ticker}: hard filter rejected — {reason}")


class StageFilterRejected(PhoenixAgentError):
    """
    Raised when stage2_only=True and the ticker is classified as Stage 1, 3, or 4.

    Like HardFilterRejected, this is an expected pipeline exit — not a bug.
    """

    def __init__(self, ticker: str, stage: int, label: str) -> None:
        self.ticker = ticker
        self.stage = stage
        self.label = label
        super().__init__(
            f"{ticker}: stage filter rejected — Stage {stage} ({label}); only Stage 2 tradeable"
        )


class DataUnavailableError(PhoenixAgentError):
    """Raised when Polygon (and any fallback) cannot return OHLCV data."""


class InsufficientDataError(PhoenixAgentError):
    """Raised when fewer bars are returned than required for SMA warm-up (need ≥200)."""
