from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from .config import NewsSettings
from .exceptions import NewsDataError
from .models import AnalystGrade, Headline, NewsSnapshot, PriceTarget


class FMPNewsClient:
    """Agent-local FMP client for stock news, analyst grades, and price targets."""

    def __init__(self, settings: NewsSettings) -> None:
        self._settings = settings
        self._session = requests.Session()

    def build_snapshot(self, ticker: str, as_of_date: date) -> NewsSnapshot:
        sources: List[str] = []
        warnings: List[str] = []

        headlines = self._fetch_headlines(ticker, as_of_date)
        if headlines:
            sources.append("fmp:/news/stock")
        else:
            warnings.append(f"No FMP headlines for {ticker}")

        grades = self._fetch_grades(ticker, as_of_date)
        if grades:
            sources.append("fmp:/grades")

        price_targets = self._fetch_price_targets(ticker, as_of_date)
        if price_targets:
            sources.append("fmp:/price-target")

        return NewsSnapshot(
            ticker=ticker,
            as_of_date=as_of_date,
            headlines=headlines,
            grades=grades,
            price_targets=price_targets,
            data_sources=sources,
            warnings=warnings,
        )

    def _fetch_headlines(self, ticker: str, as_of_date: date) -> List[Headline]:
        cutoff = as_of_date - timedelta(days=self._settings.headline_lookback_days)
        data = self._get_json("news/stock", {"symbols": ticker, "limit": self._settings.news_limit})
        out: List[Headline] = []
        for item in data or []:
            pub = _parse_datetime_to_date(item.get("publishedDate"))
            if pub is None or pub > as_of_date or pub < cutoff:
                continue
            out.append(Headline(
                title=str(item.get("title") or ""),
                published_date=pub,
                source=str(item.get("site") or ""),
                url=str(item.get("url") or ""),
            ))
        return out

    def _fetch_grades(self, ticker: str, as_of_date: date) -> List[AnalystGrade]:
        data = self._get_json("grades", {"symbol": ticker})
        out: List[AnalystGrade] = []
        lookback = as_of_date - timedelta(days=self._settings.headline_lookback_days)
        for item in data or []:
            pub = _parse_datetime_to_date(item.get("date"))
            if pub is None or pub > as_of_date or pub < lookback:
                continue
            out.append(AnalystGrade(
                grading_company=str(item.get("gradingCompany") or ""),
                grade=str(item.get("newGrade") or ""),
                previous_grade=item.get("previousGrade"),
                action=str(item.get("gradeAction") or "").lower(),
                published_date=pub,
            ))
        return out

    def _fetch_price_targets(self, ticker: str, as_of_date: date) -> List[PriceTarget]:
        data = self._get_json("price-target", {"symbol": ticker})
        out: List[PriceTarget] = []
        lookback = as_of_date - timedelta(days=self._settings.headline_lookback_days)
        for item in data or []:
            pub = _parse_datetime_to_date(item.get("publishedDate"))
            if pub is None or pub > as_of_date or pub < lookback:
                continue
            pt = item.get("priceTarget")
            if pt is None:
                continue
            out.append(PriceTarget(
                analyst_company=str(item.get("analystCompany") or item.get("analystName") or ""),
                price_target=float(pt),
                published_date=pub,
            ))
        return out

    def _get_json(self, path: str, params: Dict[str, Any]) -> Any:
        url = f"{self._settings.base_url.rstrip('/')}/{path.lstrip('/')}"
        request_params = dict(params)
        request_params["apikey"] = self._settings.api_key

        last_error: Optional[Exception] = None
        for attempt in range(self._settings.max_retries):
            try:
                resp = self._session.get(url, params=request_params, timeout=self._settings.timeout_seconds)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"Retryable response {resp.status_code}")
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt == self._settings.max_retries - 1:
                    break
                time.sleep(self._settings.retry_backoff_seconds * (attempt + 1))

        raise NewsDataError(f"Failed to fetch {url}: {last_error}")


def _parse_datetime_to_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).split(" ")[0][:10], "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return None
