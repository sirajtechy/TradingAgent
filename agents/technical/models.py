"""
models.py — Immutable data containers for the technical analysis agent.

Every model is a frozen dataclass so that once data is loaded it cannot be
accidentally mutated as it flows through the LangGraph pipeline.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


# ----------------------------------------------------------------------- #
# Request                                                                   #
# ----------------------------------------------------------------------- #

@dataclass(frozen=True)
class TechnicalRequest:
    """Encapsulates what the caller wants analysed."""

    ticker: str
    as_of_date: date


# ----------------------------------------------------------------------- #
# Price bar                                                                 #
# ----------------------------------------------------------------------- #

@dataclass(frozen=True)
class OHLCVBar:
    """A single daily OHLCV bar exactly as returned by the data source."""

    bar_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


# ----------------------------------------------------------------------- #
# Pattern signal                                                            #
# ----------------------------------------------------------------------- #

@dataclass(frozen=True)
class PatternSignal:
    """
    Represents a single chart pattern detected within the lookback window.

    Attributes:
        pattern_name:        Human-readable name, e.g. "Bull Flag".
        direction:           "bullish" or "bearish".
        confidence:          0.0 – 1.0 composite quality metric.
        start_date:          First bar of the pattern formation.
        end_date:            Last bar of the pattern (or breakout bar).
        breakout_confirmed:  True if price broke past the key level.
        volume_confirmation: True if breakout bar volume > 1.5× 20-day avg.
        description:         One-line human-readable summary.
    """

    pattern_name: str
    direction: str  # "bullish" or "bearish"
    confidence: float  # 0.0 – 1.0
    start_date: date
    end_date: date
    breakout_confirmed: bool
    volume_confirmation: bool
    description: str


# ----------------------------------------------------------------------- #
# Snapshot                                                                  #
# ----------------------------------------------------------------------- #

@dataclass(frozen=True)
class RawTechnicalSnapshot:
    """
    All the raw OHLCV data the rules engine needs.

    Built by *data_client.py* in Node 1 of the graph.
    Bars are sorted in chronological order (oldest first).
    """

    request: TechnicalRequest
    company_name: str
    sector: str
    industry: str
    bars: List[OHLCVBar]
    as_of_price: float
    as_of_price_date: date
    warnings: List[str] = field(default_factory=list)
