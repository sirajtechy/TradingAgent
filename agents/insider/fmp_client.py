from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from .config import InsiderSettings
from .exceptions import InsiderDataError
from .models import InsiderSnapshot, InsiderTrade


class FMPInsiderClient:
    """Agent-local FMP client for insider trading activity."""

    def __init__(self, settings: InsiderSettings) -> None:
        self._settings = settings
        self._session = requests.Session()

    def build_snapshot(self, ticker: str, as_of_date: date) -> InsiderSnapshot:
        sources: List[str] = []
        warnings: List[str] = []

        trades = self._fetch_insider_trades(ticker, as_of_date)
        if trades:
            sources.append("fmp:/insider-trading")
        else:
            warnings.append(f"No FMP insider trades for {ticker} in the last {self._settings.lookback_days}d")

        return InsiderSnapshot(
            ticker=ticker,
            as_of_date=as_of_date,
            trades=trades,
            data_sources=sources,
            warnings=warnings,
        )

    def _fetch_insider_trades(self, ticker: str, as_of_date: date) -> List[InsiderTrade]:
        cutoff = as_of_date - timedelta(days=self._settings.lookback_days)
        data = self._get_json("insider-trading", {"symbol": ticker, "limit": self._settings.trade_limit})
        out: List[InsiderTrade] = []
        for item in data or []:
            filing = _parse_date(item.get("filingDate"))
            if filing is None or filing > as_of_date or filing < cutoff:
                continue
            tx_date = _parse_date(item.get("transactionDate"))
            shares = float(item.get("securitiesTransacted") or 0)
            price = _safe_float(item.get("price"))
            value = float(item.get("value") or 0)
            out.append(InsiderTrade(
                filing_date=filing,
                transaction_date=tx_date,
                owner_name=str(item.get("reportingName") or ""),
                title=str(item.get("typeOfOwner") or ""),
                transaction_type=str(item.get("transactionType") or "").lower(),
                shares=shares,
                price=price,
                value=abs(value),
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

        raise InsiderDataError(f"Failed to fetch {url}: {last_error}")


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).split(" ")[0][:10], "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return None


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
