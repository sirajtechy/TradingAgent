"""Swing overlay stub — 2–5 day timing (intraday upgrade path)."""

from __future__ import annotations

from datetime import date
from typing import Dict

from agents.portfolio.config import PortfolioRules


def should_defer_entry(
    ticker: str,
    as_of: date,
    rules: PortfolioRules,
    context: Dict | None = None,
) -> bool:
    """
    Placeholder for Breitstein/LTF entry deferral.

    Returns False until intraday bars are wired (Phase C).
    """
    if not rules.swing_overlay_enabled:
        return False
    return False


def should_early_exit(
    ticker: str,
    as_of: date,
    entry_date: date,
    rules: PortfolioRules,
    context: Dict | None = None,
) -> bool:
    """Placeholder for swing time-stop / LTF breakdown exit."""
    if not rules.swing_overlay_enabled:
        return False
    return False
