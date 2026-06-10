from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MarketSummaryRequest:
    as_of_date: date


@dataclass
class TickerPerformance:
    ticker: str
    label: str
    close: Optional[float]
    change_5d_pct: Optional[float]
    change_20d_pct: Optional[float]
    vs_spy_20d_pct: Optional[float]


@dataclass
class MarketDataSnapshot:
    as_of_date: date
    vix: Optional[float]
    vix_regime: str
    spy: Optional[TickerPerformance]
    sectors: List[TickerPerformance]
    data_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
