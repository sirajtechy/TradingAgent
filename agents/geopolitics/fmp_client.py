from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from .config import GeopoliticsSettings
from .exceptions import GeopoliticsDataError
from .models import GeoHeadline, GeopoliticsSnapshot


class FMPGeopoliticsClient:
    """Agent-local FMP client for general/forex news scanning."""

    def __init__(self, settings: GeopoliticsSettings) -> None:
        self._settings = settings
        self._session = requests.Session()

    def build_snapshot(self, as_of_date: date) -> GeopoliticsSnapshot:
        sources: List[str] = []
        warnings: List[str] = []

        general_headlines = self._fetch_and_filter("news/general-latest", as_of_date)
        forex_headlines = self._fetch_and_filter("news/forex-latest", as_of_date)
        all_headlines = general_headlines + forex_headlines
        total_scanned = len(general_headlines) + len(forex_headlines)

        if general_headlines:
            sources.append("fmp:/news/general-latest")
        if forex_headlines:
            sources.append("fmp:/news/forex-latest")
        if not all_headlines:
            warnings.append("No geopolitical headlines found in scan")

        geo_filtered = [h for h in all_headlines if h.matched_keywords]

        return GeopoliticsSnapshot(
            as_of_date=as_of_date,
            headlines=geo_filtered,
            total_scanned=total_scanned,
            data_sources=sources,
            warnings=warnings,
        )

    def _fetch_and_filter(self, path: str, as_of_date: date) -> List[GeoHeadline]:
        cutoff = as_of_date - timedelta(days=self._settings.lookback_days)
        data = self._get_json(path, {"limit": self._settings.news_limit})
        out: List[GeoHeadline] = []
        for item in data or []:
            pub = _parse_datetime_to_date(item.get("publishedDate"))
            if pub is None or pub > as_of_date or pub < cutoff:
                continue
            title = str(item.get("title") or "")
            matched = _match_keywords(title, self._settings.geo_keywords)
            out.append(GeoHeadline(
                title=title,
                published_date=pub,
                source=str(item.get("site") or ""),
                url=str(item.get("url") or ""),
                matched_keywords=matched,
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

        raise GeopoliticsDataError(f"Failed to fetch {url}: {last_error}")


def _parse_datetime_to_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).split(" ")[0][:10], "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return None


def _match_keywords(text: str, keywords: tuple) -> List[str]:
    lower = text.lower()
    return [kw for kw in keywords if kw in lower]
