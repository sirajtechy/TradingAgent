from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MacroRequest:
    as_of_date: date


@dataclass
class MacroSeriesPoint:
    series_id: str
    observation_date: date
    value: float


@dataclass
class MacroSnapshot:
    as_of_date: date
    fed_funds: Optional[MacroSeriesPoint] = None
    cpi_level: Optional[MacroSeriesPoint] = None
    cpi_yoy_pct: Optional[float] = None
    unemployment: Optional[MacroSeriesPoint] = None
    yield_spread: Optional[MacroSeriesPoint] = None
    prior_fed_funds: Optional[MacroSeriesPoint] = None
    prior_cpi_yoy_pct: Optional[float] = None
    data_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class MacroEvaluation:
    signal: str
    score: float
    band: str
    confidence: str
    subscores: Dict[str, float]
    metrics: Dict[str, Any]
    data_quality: str
    warnings: List[str]
    data_sources: List[str]
    bullets: List[str] = field(default_factory=list)
