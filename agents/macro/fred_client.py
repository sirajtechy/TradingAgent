from __future__ import annotations

import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import MacroSettings
from .exceptions import MacroDataError
from .models import MacroSeriesPoint


class FREDClient:
    """Agent-local FRED API client — point-in-time via observation_end."""

    def __init__(self, settings: MacroSettings) -> None:
        self._settings = settings
        self._session = requests.Session()

    def fetch_latest_observation(
        self,
        series_id: str,
        as_of_date: date,
        *,
        limit: int = 1,
    ) -> Optional[MacroSeriesPoint]:
        rows = self._fetch_observations(series_id, as_of_date, limit=limit)
        return rows[0] if rows else None

    def fetch_observations(
        self,
        series_id: str,
        as_of_date: date,
        *,
        limit: int = 14,
    ) -> List[MacroSeriesPoint]:
        return self._fetch_observations(series_id, as_of_date, limit=limit)

    def build_snapshot(self, as_of_date: date) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """
        Fetch macro series as of cutoff date.

        Returns (metrics_dict, data_sources, warnings).
        """
        sources: List[str] = []
        warnings: List[str] = []
        metrics: Dict[str, Any] = {"as_of_date": as_of_date.isoformat()}

        fed = self.fetch_latest_observation(self._settings.series_fed_funds, as_of_date, limit=2)
        if fed:
            metrics["fed_funds"] = fed.value
            metrics["fed_funds_date"] = fed.observation_date.isoformat()
            sources.append(f"fred:{self._settings.series_fed_funds}")
        else:
            warnings.append(f"Missing FRED series {self._settings.series_fed_funds}")

        fed_prior = None
        fed_rows = self._fetch_observations(self._settings.series_fed_funds, as_of_date, limit=45)
        if len(fed_rows) >= 2:
            fed_prior = fed_rows[1]
            metrics["prior_fed_funds"] = fed_prior.value

        cpi_rows = self._fetch_observations(self._settings.series_cpi, as_of_date, limit=14)
        cpi_yoy = _cpi_yoy_pct(cpi_rows)
        if cpi_yoy is not None:
            metrics["cpi_yoy_pct"] = round(cpi_yoy, 2)
            if cpi_rows:
                metrics["cpi_observation_date"] = cpi_rows[0].observation_date.isoformat()
            sources.append(f"fred:{self._settings.series_cpi}")
        else:
            warnings.append(f"Insufficient CPI history for YoY ({self._settings.series_cpi})")

        cpi_prior_yoy = None
        if len(cpi_rows) >= 14:
            cpi_prior_yoy = _cpi_yoy_pct(cpi_rows[1:])
            if cpi_prior_yoy is not None:
                metrics["prior_cpi_yoy_pct"] = round(cpi_prior_yoy, 2)

        unemp = self.fetch_latest_observation(self._settings.series_unemployment, as_of_date)
        if unemp:
            metrics["unemployment"] = unemp.value
            metrics["unemployment_date"] = unemp.observation_date.isoformat()
            sources.append(f"fred:{self._settings.series_unemployment}")
        else:
            warnings.append(f"Missing FRED series {self._settings.series_unemployment}")

        spread = self.fetch_latest_observation(self._settings.series_yield_spread, as_of_date)
        if spread:
            metrics["yield_spread_10y2y"] = spread.value
            metrics["yield_spread_date"] = spread.observation_date.isoformat()
            sources.append(f"fred:{self._settings.series_yield_spread}")
        else:
            warnings.append(f"Missing FRED series {self._settings.series_yield_spread}")

        return metrics, sources, warnings

    def _fetch_observations(
        self,
        series_id: str,
        as_of_date: date,
        *,
        limit: int,
    ) -> List[MacroSeriesPoint]:
        params = {
            "series_id": series_id,
            "api_key": self._settings.api_key,
            "file_type": "json",
            "observation_end": as_of_date.isoformat(),
            "sort_order": "desc",
            "limit": limit,
        }
        url = f"{self._settings.base_url}/series/observations"
        last_error: Optional[Exception] = None
        for attempt in range(self._settings.max_retries):
            try:
                resp = self._session.get(url, params=params, timeout=self._settings.timeout_seconds)
                resp.raise_for_status()
                payload = resp.json()
                return _parse_observations(series_id, payload)
            except Exception as exc:
                last_error = exc
                time.sleep(self._settings.retry_backoff_seconds * (attempt + 1))
        raise MacroDataError(f"FRED fetch failed for {series_id}: {last_error}")


def _parse_observations(series_id: str, payload: Dict[str, Any]) -> List[MacroSeriesPoint]:
    out: List[MacroSeriesPoint] = []
    for row in payload.get("observations") or []:
        raw_val = row.get("value")
        raw_date = row.get("date")
        if raw_val in (None, ".", ""):
            continue
        try:
            out.append(
                MacroSeriesPoint(
                    series_id=series_id,
                    observation_date=date.fromisoformat(str(raw_date)),
                    value=float(raw_val),
                )
            )
        except (TypeError, ValueError):
            continue
    return out


def _cpi_yoy_pct(rows: List[MacroSeriesPoint]) -> Optional[float]:
    """YoY % change using latest CPI level vs ~12 months prior."""
    if len(rows) < 13:
        return None
    latest = rows[0].value
    prior = rows[12].value
    if prior == 0:
        return None
    return ((latest - prior) / abs(prior)) * 100.0
