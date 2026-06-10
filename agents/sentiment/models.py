from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SentimentRequest:
    ticker: str
    as_of_date: date


@dataclass
class DimensionScore:
    dimension: str
    score: float
    signal: str
    available: bool


@dataclass
class SentimentSnapshot:
    ticker: str
    as_of_date: date
    news_eval: Optional[Dict[str, Any]] = None
    insider_eval: Optional[Dict[str, Any]] = None
    macro_eval: Optional[Dict[str, Any]] = None
    geopolitics_eval: Optional[Dict[str, Any]] = None
    ohlcv_context: Optional[Dict[str, Any]] = None
    data_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
