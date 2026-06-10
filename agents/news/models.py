from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class NewsRequest:
    ticker: str
    as_of_date: date


@dataclass
class Headline:
    title: str
    published_date: date
    source: str
    url: str


@dataclass
class AnalystGrade:
    grading_company: str
    grade: str
    previous_grade: Optional[str]
    action: str
    published_date: date


@dataclass
class PriceTarget:
    analyst_company: str
    price_target: float
    published_date: date


@dataclass
class NewsSnapshot:
    ticker: str
    as_of_date: date
    headlines: List[Headline] = field(default_factory=list)
    grades: List[AnalystGrade] = field(default_factory=list)
    price_targets: List[PriceTarget] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
