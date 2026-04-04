from datetime import date, datetime, timedelta
import time
from typing import Any, Dict, List, Optional

import requests

from .config import Settings
from .exceptions import DataUnavailableError
from .models import (
    AnalysisRequest,
    DividendEvent,
    PricePoint,
    Profile,
    RawFundamentalSnapshot,
    StatementEntry,
)


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    candidate = value.split(" ")[0]
    return datetime.strptime(candidate, "%Y-%m-%d").date()


class FMPClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()

    def build_snapshot(self, request: AnalysisRequest) -> RawFundamentalSnapshot:
        profile = self.get_profile(request.ticker)
        income_statements = self._filter_by_as_of(
            self.get_statements("income-statement", request.ticker, limit=5),
            request.as_of_date,
        )
        balance_statements = self._filter_by_as_of(
            self.get_statements("balance-sheet-statement", request.ticker, limit=5),
            request.as_of_date,
        )
        cashflow_statements = self._filter_by_as_of(
            self.get_statements("cash-flow-statement", request.ticker, limit=5),
            request.as_of_date,
        )
        dividend_events = self._filter_dividends_by_as_of(
            self.get_dividends_safe(request.ticker, limit=5),
            request.as_of_date,
        )
        price_point = self.get_price_as_of(request.ticker, request.as_of_date)

        warnings: List[str] = [
            "Sector and industry are sourced from the current company profile endpoint.",
            "The Shariah impure revenue screen uses interest income as a proxy for non-compliant income.",
        ]
        if not dividend_events:
            warnings.append("Dividend data is unavailable on this API plan. Graham dividend continuity and Lynch yield inputs will be skipped.")
        if len(income_statements) < 2:
            warnings.append("Less than two annual income statements are available as of the requested date.")
        if len(balance_statements) < 2:
            warnings.append("Less than two annual balance sheets are available as of the requested date.")
        if len(cashflow_statements) < 2:
            warnings.append("Less than two annual cash flow statements are available as of the requested date.")

        return RawFundamentalSnapshot(
            request=request,
            profile=profile,
            price_point=price_point,
            income_statements=income_statements,
            balance_statements=balance_statements,
            cashflow_statements=cashflow_statements,
            dividend_events=dividend_events,
            warnings=warnings,
        )

    def get_profile(self, ticker: str) -> Profile:
        items = self._get_json(
            "profile",
            {
                "symbol": ticker,
            },
        )
        if not items:
            raise DataUnavailableError(f"No profile data available for {ticker}")
        item = items[0]
        return Profile(
            ticker=ticker.upper(),
            company_name=str(item.get("companyName") or item.get("name") or ticker.upper()),
            sector=str(item.get("sector") or "Unknown"),
            industry=str(item.get("industry") or "Unknown"),
            description=str(item.get("description") or ""),
        )

    def get_statements(self, endpoint: str, ticker: str, limit: int) -> List[StatementEntry]:
        items = self._get_json(
            endpoint,
            {
                "symbol": ticker,
                "period": "annual",
                "limit": limit,
            },
        )
        statements: List[StatementEntry] = []
        for item in items:
            report_date = _parse_date(item.get("date"))
            filing_date = _parse_date(item.get("filingDate")) or report_date
            if not report_date or not filing_date:
                continue
            statements.append(
                StatementEntry(
                    report_date=report_date,
                    filing_date=filing_date,
                    fiscal_year=str(item.get("fiscalYear") or ""),
                    period=str(item.get("period") or "FY"),
                    values=dict(item),
                )
            )
        statements.sort(key=lambda entry: (entry.filing_date, entry.report_date), reverse=True)
        return statements

    def get_dividends_safe(self, ticker: str, limit: int) -> List[DividendEvent]:
        """Returns an empty list if the dividends endpoint is blocked (402/403) on the current plan."""
        try:
            return self.get_dividends(ticker, limit)
        except DataUnavailableError:
            return []

    def get_dividends(self, ticker: str, limit: int) -> List[DividendEvent]:
        items = self._get_json(
            "dividends",
            {
                "symbol": ticker,
                "limit": limit,
            },
        )
        dividends: List[DividendEvent] = []
        for item in items:
            event_date = _parse_date(item.get("date"))
            if not event_date:
                continue
            dividend = item.get("dividend")
            if dividend is None:
                continue
            dividends.append(
                DividendEvent(
                    event_date=event_date,
                    dividend=float(dividend),
                    adjusted_dividend=float(item["adjDividend"]) if item.get("adjDividend") is not None else None,
                    frequency=item.get("frequency"),
                )
            )
        dividends.sort(key=lambda entry: entry.event_date, reverse=True)
        return dividends

    def get_price_as_of(self, ticker: str, as_of_date: date) -> PricePoint:
        from_date = as_of_date - timedelta(days=14)
        items = self._get_json(
            "historical-price-eod/light",
            {
                "symbol": ticker,
                "from": from_date.isoformat(),
                "to": as_of_date.isoformat(),
            },
        )
        price_points: List[PricePoint] = []
        for item in items:
            price_date = _parse_date(item.get("date"))
            price = item.get("price")
            if not price_date or price is None:
                continue
            if price_date > as_of_date:
                continue
            price_points.append(
                PricePoint(
                    price_date=price_date,
                    price=float(price),
                    volume=float(item["volume"]) if item.get("volume") is not None else None,
                )
            )
        price_points.sort(key=lambda point: point.price_date, reverse=True)
        if not price_points:
            raise DataUnavailableError(f"No historical price available for {ticker} on or before {as_of_date.isoformat()}")
        return price_points[0]

    def _filter_by_as_of(self, entries: List[StatementEntry], as_of_date: date) -> List[StatementEntry]:
        filtered = [entry for entry in entries if entry.filing_date <= as_of_date]
        filtered.sort(key=lambda entry: (entry.filing_date, entry.report_date), reverse=True)
        return filtered

    def _filter_dividends_by_as_of(self, entries: List[DividendEvent], as_of_date: date) -> List[DividendEvent]:
        filtered = [entry for entry in entries if entry.event_date <= as_of_date]
        filtered.sort(key=lambda entry: entry.event_date, reverse=True)
        return filtered

    def _get_json(self, path: str, params: Dict[str, Any]) -> Any:
        url = f"{self.settings.base_url.rstrip('/')}/{path.lstrip('/')}"
        request_params = dict(params)
        request_params["apikey"] = self.settings.api_key

        last_error: Optional[Exception] = None
        for attempt in range(self.settings.max_retries):
            try:
                response = self.session.get(url, params=request_params, timeout=self.settings.timeout_seconds)
                if response.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"Retryable response {response.status_code}")
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as error:
                last_error = error
                if attempt == self.settings.max_retries - 1:
                    break
                time.sleep(self.settings.retry_backoff_seconds * (attempt + 1))

        raise DataUnavailableError(f"Failed to fetch {url}: {last_error}")
