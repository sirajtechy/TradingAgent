from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AnalysisRequest:
    ticker: str
    as_of_date: date
    shariah_standard: str = "aaoifi"
    include_experimental_score: bool = True


@dataclass(frozen=True)
class Profile:
    ticker: str
    company_name: str
    sector: str
    industry: str
    description: str


@dataclass(frozen=True)
class StatementEntry:
    report_date: date
    filing_date: date
    fiscal_year: str
    period: str
    values: Dict[str, Any]

    def number(self, *keys: str) -> Optional[float]:
        for key in keys:
            value = self.values.get(key)
            if value is None:
                continue
            if isinstance(value, bool):
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None


@dataclass(frozen=True)
class PricePoint:
    price_date: date
    price: float
    volume: Optional[float]


@dataclass(frozen=True)
class DividendEvent:
    event_date: date
    dividend: float
    adjusted_dividend: Optional[float]
    frequency: Optional[str]


@dataclass(frozen=True)
class RawFundamentalSnapshot:
    request: AnalysisRequest
    profile: Profile
    price_point: PricePoint
    income_statements: List[StatementEntry]
    balance_statements: List[StatementEntry]
    cashflow_statements: List[StatementEntry]
    dividend_events: List[DividendEvent]
    warnings: List[str]
