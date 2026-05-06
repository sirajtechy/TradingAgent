"""
models.py — Immutable data contracts for the Phoenix Agent pipeline.

Every model is a frozen dataclass so that once data flows into a LangGraph
node it cannot be accidentally mutated.  The models progress through the
8-node pipeline in the order they are defined here.

Pipeline flow:
  PhoenixRequest
    → PhoenixSnapshot  (after fetch_data)
    → StageResult      (after classify_stage)
    → PatternMatch     (after detect_patterns)
    → EntrySetup       (after evaluate_entry)
    → RiskLevels       (after compute_risk)
    → PhoenixSignal    (final output, after build_score + render_report)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Input
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PhoenixRequest:
    """What the caller wants analysed."""

    ticker: str
    as_of_date: date


# ─────────────────────────────────────────────────────────────────────────────
# OHLCV bar (reused from technical agent conventions)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OHLCVBar:
    """A single daily OHLCV bar as returned by the data source."""

    bar_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


# ─────────────────────────────────────────────────────────────────────────────
# SMA bundle
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SMABundle:
    """The most-recent SMA values for the snapshot date."""

    sma10: Optional[float]
    sma20: Optional[float]
    sma50: Optional[float]
    sma200: Optional[float]
    sma40w: Optional[float]
    """40-week SMA ≈ 200-bar rolling average (macro trend context)."""

    # Prior-period values used for slope computation
    sma10_prior: Optional[float] = None
    sma20_prior: Optional[float] = None
    sma50_prior: Optional[float] = None
    sma200_prior: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# Market snapshot
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PhoenixSnapshot:
    """
    Full market data snapshot for one ticker at one point in time.

    This is the primary data carrier through nodes 1–7 of the pipeline.
    Mutable (not frozen) so nodes can attach derived data cheaply without
    copying 500 bars repeatedly.
    """

    request: PhoenixRequest
    bars: List[OHLCVBar]
    """500 daily bars, oldest-first, ending on or before as_of_date."""

    smas: SMABundle
    """Most-recent SMA values computed from the bar series."""

    vol_avg_20: float
    """20-bar simple moving average of volume (Phoenix volume baseline)."""

    high_52w: float
    """Highest high over the past 252 trading bars (~1 year)."""

    low_52w: float
    """Lowest low over the past 252 trading bars (~1 year)."""

    as_of_price: float
    """Closing price on the as_of_date bar."""

    as_of_price_date: date
    """Actual date of the last bar (may differ from request.as_of_date on weekends/holidays)."""

    warnings: List[str] = field(default_factory=list)
    """Non-fatal data quality notes accumulated by the data client."""


# ─────────────────────────────────────────────────────────────────────────────
# Stage classification
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StageResult:
    """Output of the stage classifier node."""

    stage: int
    """1, 2, 3, or 4 (Weinstein / Phoenix stage)."""

    label: str
    """Human-readable stage label: 'Accumulation' / 'Momentum' / 'Exhaustion' / 'Decline'."""

    action: str
    """Recommended action: 'WATCH' / 'TRADE' / 'REDUCE' / 'AVOID'."""

    ma_alignment: bool
    """True when price > SMA20 > SMA50 > SMA200 (full bull alignment)."""

    ma_slopes: Dict[str, str]
    """Slope of each SMA: {'sma20': 'rising', 'sma50': 'flat', 'sma200': 'rising'}."""

    notes: List[str]
    """Human-readable notes explaining the stage classification."""


# ─────────────────────────────────────────────────────────────────────────────
# Pattern detection
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PatternMatch:
    """Output of the pattern detector node (best match)."""

    pattern_name: str
    """'VCP' / 'Flat Base' / 'Tight Flag' / 'Shakeout' / 'Pullback' / 'None'."""

    confirmed: bool
    """True when both price breakout AND volume confirmation are satisfied."""

    volume_confirmed: bool
    """True when breakout-bar volume >= 2× 20-bar average volume."""

    pivot_price: float
    """The structural breakout / pivot price level."""

    confidence: float
    """Overall pattern quality: 0.0 (weak) – 1.0 (textbook)."""

    vcp_contractions: int
    """For VCP: number of contractions detected (1–3). Zero for non-VCP patterns."""

    base_depth_pct: float
    """Depth of the base as a percentage of the peak price."""

    description: str
    """One-line human-readable summary of the pattern."""


# ─────────────────────────────────────────────────────────────────────────────
# Entry setup
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EntrySetup:
    """Output of the entry evaluator node."""

    entry_type: str
    """'standard_breakout' / 'pivot_breakout' / 'shakeout' / 'pullback' / 'none'."""

    entry_price: float
    """Recommended entry price (pivot / breakout level or current MA value)."""

    trigger_description: str
    """One-line description of the entry trigger condition."""


# ─────────────────────────────────────────────────────────────────────────────
# Risk levels
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RiskLevels:
    """Output of the risk computation node."""

    stop_price: float
    """Hard stop = low of breakout candle (LOC) minus stop_buffer_pct."""

    stop_pct: float
    """Percentage risk from entry to stop (e.g. 0.05 = 5% below entry)."""

    target_1: float
    """First price target: entry + 1× measured base height."""

    target_2: float
    """Second price target: entry + 1.5× measured base height."""

    reward_risk: float
    """Reward/risk ratio: (target_1 - entry) / (entry - stop)."""

    position_size_shares: Optional[float]
    """Shares to buy so that 1% of account capital is at risk. None if uncalculable."""

    trail_stop_ma: str
    """Which MA to use as trailing stop right now: 'MA10' or 'MA20'."""


# ─────────────────────────────────────────────────────────────────────────────
# Final signal (pipeline output)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PhoenixSignal:
    """
    The complete output of one Phoenix Agent analysis run.

    This is what service.py returns (as a dict) and what the orchestrator
    will consume as a 4th signal source.
    """

    ticker: str
    as_of_date: date

    signal: str
    """'BUY' / 'WATCH' / 'AVOID'."""

    stage: StageResult
    pattern: Optional[PatternMatch]
    entry: Optional[EntrySetup]
    risk: Optional[RiskLevels]

    score: float
    """Phoenix composite score: 0–100."""

    score_breakdown: Dict[str, float]
    """Component scores: {'volume': x, 'structure': y, 'pattern': z, 'stage': w}."""

    hard_filter_passed: bool
    hard_filter_reason: Optional[str]
    """Non-None only when hard_filter_passed=False."""

    report: str
    """Human-readable multi-line text report."""

    warnings: List[str]
    """Non-fatal data quality notes from the data client."""
