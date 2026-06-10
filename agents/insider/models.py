from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass(frozen=True)
class InsiderRequest:
    ticker: str
    as_of_date: date


@dataclass
class InsiderTrade:
    filing_date: date
    transaction_date: Optional[date]
    owner_name: str
    title: str
    transaction_type: str
    shares: float
    price: Optional[float]
    value: float


@dataclass
class InsiderSnapshot:
    ticker: str
    as_of_date: date
    trades: List[InsiderTrade] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
