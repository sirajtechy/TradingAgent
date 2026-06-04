"""
polygon_client.py — Polygon.io API client for the O'Neil Technical Analysis Agent.

Fetches weekly + daily OHLCV bars AND server-side pre-computed indicators
(EMA 10/21/50, SMA 30, RSI 14, MACD 12-26-9, EMA 200d) in parallel.

Polygon endpoints used
─────────────────────
Bars (OHLCV):
  /v2/aggs/ticker/{ticker}/range/1/week/{from}/{to}  — weekly bars
  /v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}   — daily bars

Server-side indicators — weekly timeframe:
  /v1/indicators/ema/{ticker}?timespan=week&window=10|21|50
  /v1/indicators/sma/{ticker}?timespan=week&window=30
  /v1/indicators/rsi/{ticker}?timespan=week&window=14
  /v1/indicators/macd/{ticker}?timespan=week&short_window=12&long_window=26&signal_window=9

Server-side indicators — daily timeframe:
  /v1/indicators/ema/{ticker}?timespan=day&window=200

Reference:
  /v3/reference/tickers/{ticker}  — company name

Key behaviours
──────────────
- Only supports US exchange tickers (Polygon does not cover NSE).
  Caller should check request.exchange == "NSE" and skip this client.
- Fires all indicator calls concurrently via ThreadPoolExecutor.
- Loads API key from .env in the package directory (same pattern as KGC explorer).
- Raises PolygonDataError on auth failure or persistent network errors.
- Returns None indicator values gracefully so callers can fall back to
  locally-computed values from indicators.compute_weekly().
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from .models import DailyBar, ONeilRequest, WeeklyBar


# ─────────────────────────────────────────────────────────────────────────────
# Load POLYGON_API_KEY from .env  (same lightweight loader as polygon_kgc_explorer)
# ─────────────────────────────────────────────────────────────────────────────

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "")
BASE_URL        = "https://api.polygon.io"

_WEEKLY_LOOKBACK_DAYS = 3 * 365 + 14   # ~3 yr weekly bars
_DAILY_LOOKBACK_DAYS  = 2 * 365 + 30   # ~2 yr daily bars (covers EMA-200d warm-up)
_MAX_RETRIES          = 3
_RETRY_SLEEP          = 1.5             # seconds, doubled per attempt


# ─────────────────────────────────────────────────────────────────────────────
# Exception
# ─────────────────────────────────────────────────────────────────────────────

class PolygonDataError(RuntimeError):
    """Raised when Polygon cannot provide data after retries."""


# ─────────────────────────────────────────────────────────────────────────────
# HTTP session + low-level GET
# ─────────────────────────────────────────────────────────────────────────────

_SESSION: Optional[requests.Session] = None


def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers["Authorization"] = f"Bearer {POLYGON_API_KEY}"
    return _SESSION


def _get(path: str, params: Optional[Dict] = None, retries: int = _MAX_RETRIES) -> Optional[Dict]:
    """HTTP GET with retry / rate-limit back-off. Returns None on failure."""
    url = f"{BASE_URL}{path}"
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            r = _session().get(url, params=params or {}, timeout=12)
            if r.status_code == 403:
                raise PolygonDataError(f"Polygon auth error (403) for {url}. Check POLYGON_API_KEY.")
            if r.status_code == 429:
                time.sleep(_RETRY_SLEEP * (2 ** attempt))
                continue
            r.raise_for_status()
            return r.json()
        except PolygonDataError:
            raise
        except Exception as exc:
            last_err = exc
            time.sleep(_RETRY_SLEEP * (2 ** attempt))
    # Soft fail — return None so caller can fall back
    return None


# ─────────────────────────────────────────────────────────────────────────────
# OHLCV bar converters
# ─────────────────────────────────────────────────────────────────────────────

def _parse_weekly_bars(data: Optional[Dict]) -> List[WeeklyBar]:
    if not data or "results" not in data:
        return []
    bars = []
    for r in data["results"]:
        try:
            ts_sec = r["t"] / 1000.0
            import datetime
            bar_date = datetime.date.fromtimestamp(ts_sec)
            bars.append(WeeklyBar(
                bar_date=bar_date,
                open=float(r["o"]),
                high=float(r["h"]),
                low=float(r["l"]),
                close=float(r["c"]),
                volume=float(r.get("v", 0)),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    bars.sort(key=lambda b: b.bar_date)
    return bars


def _parse_daily_bars(data: Optional[Dict]) -> List[DailyBar]:
    if not data or "results" not in data:
        return []
    bars = []
    for r in data["results"]:
        try:
            ts_sec = r["t"] / 1000.0
            import datetime
            bar_date = datetime.date.fromtimestamp(ts_sec)
            bars.append(DailyBar(
                bar_date=bar_date,
                open=float(r["o"]),
                high=float(r["h"]),
                low=float(r["l"]),
                close=float(r["c"]),
                volume=float(r.get("v", 0)),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    bars.sort(key=lambda b: b.bar_date)
    return bars


# ─────────────────────────────────────────────────────────────────────────────
# Indicator value parsers
# ─────────────────────────────────────────────────────────────────────────────

def _ind_values(data: Optional[Dict]) -> List[Dict]:
    """Extract the 'values' list from a Polygon indicator response."""
    if not data:
        return []
    return data.get("results", {}).get("values", []) or []


def _latest_value(data: Optional[Dict]) -> Optional[float]:
    """Return the most recent indicator value (index 0 in desc-ordered response)."""
    vals = _ind_values(data)
    return float(vals[0]["value"]) if vals else None


def _prev_value(data: Optional[Dict]) -> Optional[float]:
    """Return the second-most-recent indicator value (index 1)."""
    vals = _ind_values(data)
    return float(vals[1]["value"]) if len(vals) >= 2 else None


def _latest_macd(data: Optional[Dict]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Return (macd_line, signal_line, histogram) for most recent bar."""
    vals = _ind_values(data)
    if not vals:
        return None, None, None
    v = vals[0]
    return (
        float(v.get("value")) if v.get("value") is not None else None,
        float(v.get("signal")) if v.get("signal") is not None else None,
        float(v.get("histogram")) if v.get("histogram") is not None else None,
    )


def _prev_macd_histogram(data: Optional[Dict]) -> Optional[float]:
    vals = _ind_values(data)
    if len(vals) < 2:
        return None
    v = vals[1]
    return float(v.get("histogram")) if v.get("histogram") is not None else None


# ─────────────────────────────────────────────────────────────────────────────
# Public Polygon client class
# ─────────────────────────────────────────────────────────────────────────────

class PolygonONeilClient:
    """
    Fetches weekly + daily OHLCV bars AND pre-computed indicator values from
    Polygon.io for the O'Neil Technical Analysis Agent.

    Usage (bars only — for backtesting, the pipeline does its own compute)::

        client = PolygonONeilClient()
        weekly_bars, daily_bars, name = client.fetch_bars(request)

    Usage (bars + live indicators — for live analysis)::

        weekly_bars, daily_bars, polygon_inds, name = client.fetch_with_indicators(request)
        # polygon_inds overrides locally-computed indicator values

    Note: Only US exchange tickers are supported by Polygon.
    For NSE stocks (exchange="NSE"), use the yfinance data_client instead.
    """

    def is_available(self) -> bool:
        """True if the Polygon API key is configured."""
        return bool(POLYGON_API_KEY)

    # ── OHLCV only (used for backtesting) ────────────────────────────────

    def fetch_bars(
        self,
        request: ONeilRequest,
    ) -> Tuple[List[WeeklyBar], List[DailyBar], str]:
        """
        Download weekly + daily OHLCV bars from Polygon.

        Returns (weekly_bars, daily_bars, company_name).
        Raises PolygonDataError on auth failure.
        Returns empty lists on network failure (caller should fallback).
        """
        if not self.is_available():
            raise PolygonDataError("POLYGON_API_KEY not set in .env")

        ticker = request.ticker.upper()
        as_of  = request.as_of_date
        w_from = (as_of - timedelta(days=_WEEKLY_LOOKBACK_DAYS)).isoformat()
        d_from = (as_of - timedelta(days=_DAILY_LOOKBACK_DAYS)).isoformat()
        to_str  = as_of.isoformat()

        weekly_data, daily_data, ref_data = None, None, None

        def _fetch_weekly():
            return _get(
                f"/v2/aggs/ticker/{ticker}/range/1/week/{w_from}/{to_str}",
                {"adjusted": "true", "sort": "asc", "limit": 200},
            )

        def _fetch_daily():
            return _get(
                f"/v2/aggs/ticker/{ticker}/range/1/day/{d_from}/{to_str}",
                {"adjusted": "true", "sort": "asc", "limit": 600},
            )

        def _fetch_ref():
            return _get(f"/v3/reference/tickers/{ticker}")

        jobs = [("weekly", _fetch_weekly), ("daily", _fetch_daily), ("ref", _fetch_ref)]
        results: Dict[str, Any] = {}

        with ThreadPoolExecutor(max_workers=3) as pool:
            fut_map = {pool.submit(fn): label for label, fn in jobs}
            for fut in as_completed(fut_map):
                results[fut_map[fut]] = fut.result()

        weekly_bars = _parse_weekly_bars(results.get("weekly"))
        daily_bars  = _parse_daily_bars(results.get("daily"))
        company_name = ticker
        ref = results.get("ref")
        if ref:
            info = ref.get("results", {})
            company_name = info.get("name") or ticker

        return weekly_bars, daily_bars, company_name

    # ── OHLCV + pre-computed indicators (used for live analysis) ─────────

    def fetch_with_indicators(
        self,
        request: ONeilRequest,
    ) -> Tuple[List[WeeklyBar], List[DailyBar], Dict[str, Any], str]:
        """
        Download OHLCV bars AND latest indicator values in parallel.

        The returned *polygon_inds* dict has the same keys as
        ``compute_weekly()`` in indicators.py:
            ema_10w, ema_21w, ema_50w, sma_30w, rsi_14w,
            macd_line, macd_signal_line, macd_histogram, macd_histogram_prev

        These values come directly from Polygon's server-side computation
        (higher accuracy than locally-recomputed values).

        Returns (weekly_bars, daily_bars, polygon_inds, company_name).
        """
        ticker = request.ticker.upper()
        as_of  = request.as_of_date
        to_str  = as_of.isoformat()
        w_from  = (as_of - timedelta(days=_WEEKLY_LOOKBACK_DAYS)).isoformat()
        d_from  = (as_of - timedelta(days=_DAILY_LOOKBACK_DAYS)).isoformat()

        _w = "week"
        _d = "day"
        _sc = "close"
        _lim2 = "2"   # get last 2 values for prev-bar trend detection, newest first

        jobs: List[Tuple[str, str, Dict]] = [
            # OHLCV bars
            ("weekly_bars",  f"/v2/aggs/ticker/{ticker}/range/1/week/{w_from}/{to_str}",
             {"adjusted": "true", "sort": "asc", "limit": 200}),
            ("daily_bars",   f"/v2/aggs/ticker/{ticker}/range/1/day/{d_from}/{to_str}",
             {"adjusted": "true", "sort": "asc", "limit": 600}),
            # Weekly indicators
            ("ema_10w",  f"/v1/indicators/ema/{ticker}",
             {"timespan": _w, "window": 10, "series_type": _sc, "order": "desc", "limit": _lim2, "timestamp.lte": to_str}),
            ("ema_21w",  f"/v1/indicators/ema/{ticker}",
             {"timespan": _w, "window": 21, "series_type": _sc, "order": "desc", "limit": _lim2, "timestamp.lte": to_str}),
            ("ema_50w",  f"/v1/indicators/ema/{ticker}",
             {"timespan": _w, "window": 50, "series_type": _sc, "order": "desc", "limit": _lim2, "timestamp.lte": to_str}),
            ("sma_30w",  f"/v1/indicators/sma/{ticker}",
             {"timespan": _w, "window": 30, "series_type": _sc, "order": "desc", "limit": "12", "timestamp.lte": to_str}),
            ("rsi_14w",  f"/v1/indicators/rsi/{ticker}",
             {"timespan": _w, "window": 14, "series_type": _sc, "order": "desc", "limit": _lim2, "timestamp.lte": to_str}),
            ("macd_w",   f"/v1/indicators/macd/{ticker}",
             {"timespan": _w, "short_window": 12, "long_window": 26, "signal_window": 9,
              "series_type": _sc, "order": "desc", "limit": _lim2, "timestamp.lte": to_str}),
            # Daily EMA-200
            ("ema_200d", f"/v1/indicators/ema/{ticker}",
             {"timespan": _d, "window": 200, "series_type": _sc, "order": "desc", "limit": "1", "timestamp.lte": to_str}),
            # Reference
            ("ref",      f"/v3/reference/tickers/{ticker}", {}),
        ]

        raw: Dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=10) as pool:
            fut_map = {pool.submit(_get, path, params): label for label, path, params in jobs}
            for fut in as_completed(fut_map):
                raw[fut_map[fut]] = fut.result()

        weekly_bars = _parse_weekly_bars(raw.get("weekly_bars"))
        daily_bars  = _parse_daily_bars(raw.get("daily_bars"))

        # latest + 10-bars-ago SMA-30 for stage-slope
        sma30_vals  = _ind_values(raw.get("sma_30w"))
        sma30_latest = float(sma30_vals[0]["value"]) if sma30_vals else None
        sma30_prev10 = float(sma30_vals[-1]["value"]) if len(sma30_vals) >= 10 else None

        macd_line, macd_sig, macd_hist = _latest_macd(raw.get("macd_w"))
        macd_hist_prev = _prev_macd_histogram(raw.get("macd_w"))

        polygon_inds: Dict[str, Any] = {
            "ema_10w":             _latest_value(raw.get("ema_10w")),
            "ema_21w":             _latest_value(raw.get("ema_21w")),
            "ema_50w":             _latest_value(raw.get("ema_50w")),
            "sma_30w":             sma30_latest,
            "sma_30w_prev10":      sma30_prev10,
            "rsi_14w":             _latest_value(raw.get("rsi_14w")),
            "rsi_14w_prev":        _prev_value(raw.get("rsi_14w")),
            "macd_line":           macd_line,
            "macd_signal_line":    macd_sig,
            "macd_histogram":      macd_hist,
            "macd_histogram_prev": macd_hist_prev,
            # volume_ratio_10w is not a Polygon native endpoint — computed locally
            "volume_ratio_10w":    None,
            "ema_200d":            _latest_value(raw.get("ema_200d")),
        }

        company_name = ticker
        ref = raw.get("ref")
        if ref:
            info = ref.get("results", {})
            company_name = info.get("name") or ticker

        return weekly_bars, daily_bars, polygon_inds, company_name
