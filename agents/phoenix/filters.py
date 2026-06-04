"""
filters.py — Hard pre-filters for the Phoenix Agent pipeline.

The Phoenix Trader strategy has two mandatory hard prerequisites before any
pattern analysis is performed.  If either fails the ticker is immediately
rejected with an AVOID signal — no further computation is done.

Hard filters (in order):
  1. Price must be above the 200-day SMA          (trend filter)
  2. Price must be ≥50% above the 52-week low     (position of strength)

These are NOT soft scoring components — they are binary gates.  A stock that
fails filter 1 could score 0 or 100 on everything else; it still gets AVOID.

Public API
──────────
  apply_hard_filters(snapshot, settings) → FilterResult
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .config import PhoenixSettings
from .exceptions import HardFilterRejected
from .models import PhoenixSnapshot


# ─────────────────────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FilterResult:
    """Output of apply_hard_filters()."""

    passed: bool
    """True if all hard filters passed; False if any failed."""

    failure_reason: Optional[str]
    """Human-readable reason string when passed=False; None when passed=True."""

    checks: List[str]
    """All individual check results (for the report), pass or fail."""


# ─────────────────────────────────────────────────────────────────────────────
# Public function
# ─────────────────────────────────────────────────────────────────────────────

def apply_hard_filters(
    snapshot: PhoenixSnapshot,
    settings: Optional[PhoenixSettings] = None,
    raise_on_fail: bool = False,
) -> FilterResult:
    """
    Run the two mandatory Phoenix hard pre-filters against *snapshot*.

    Parameters
    ----------
    snapshot:       PhoenixSnapshot from the data client.
    settings:       PhoenixSettings; uses defaults if None.
    raise_on_fail:  If True, raises HardFilterRejected instead of returning
                    a FilterResult with passed=False.  The LangGraph node
                    uses this to short-circuit the graph.

    Returns
    -------
    FilterResult — always returned when raise_on_fail=False.

    Raises
    ------
    HardFilterRejected — only when raise_on_fail=True and a filter fails.
    """
    if settings is None:
        settings = PhoenixSettings()

    checks: List[str] = []
    price = snapshot.as_of_price
    sma200 = snapshot.smas.sma200
    low_52w = snapshot.low_52w
    ticker = snapshot.request.ticker

    # ── Filter 1: Price above 200-day SMA ────────────────────────────────
    if settings.above_200dma_required:
        if sma200 is None:
            reason = "SMA200 could not be computed (insufficient data)"
            checks.append(f"FAIL  200DMA: {reason}")
            return _fail(ticker, reason, checks, raise_on_fail)

        if price <= sma200:
            pct_below = (sma200 - price) / sma200 * 100
            reason = (
                f"Price ${price:.2f} is below 200-day SMA ${sma200:.2f} "
                f"({pct_below:.1f}% below)"
            )
            checks.append(f"FAIL  200DMA: {reason}")
            return _fail(ticker, reason, checks, raise_on_fail)

        pct_above = (price - sma200) / sma200 * 100
        checks.append(
            f"PASS  200DMA: Price ${price:.2f} is {pct_above:.1f}% above SMA200 ${sma200:.2f}"
        )

    # ── Filter 2: Price ≥50% above 52-week low ───────────────────────────
    if low_52w <= 0:
        reason = "52-week low is zero or negative — cannot compute filter"
        checks.append(f"FAIL  52w-low: {reason}")
        return _fail(ticker, reason, checks, raise_on_fail)

    pct_above_low = (price - low_52w) / low_52w
    required_pct = settings.above_52w_low_pct

    if pct_above_low < required_pct:
        reason = (
            f"Price ${price:.2f} is only {pct_above_low * 100:.1f}% above "
            f"52w-low ${low_52w:.2f}; need ≥{required_pct * 100:.0f}%"
        )
        checks.append(f"FAIL  52w-low: {reason}")
        return _fail(ticker, reason, checks, raise_on_fail)

    checks.append(
        f"PASS  52w-low: Price ${price:.2f} is {pct_above_low * 100:.1f}% above "
        f"52w-low ${low_52w:.2f} (≥{required_pct * 100:.0f}% required)"
    )

    # ── All filters passed ────────────────────────────────────────────────
    return FilterResult(passed=True, failure_reason=None, checks=checks)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fail(
    ticker: str,
    reason: str,
    checks: List[str],
    raise_on_fail: bool,
) -> FilterResult:
    if raise_on_fail:
        raise HardFilterRejected(ticker, reason)
    return FilterResult(passed=False, failure_reason=reason, checks=checks)
