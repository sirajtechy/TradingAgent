"""
polygon_data — Shared Polygon.io market-data client for ALL agents.

This is the single source of truth for fetching OHLCV bars and company
profile information from Polygon.io.  Every agent (technical, fundamental,
orchestrator, O'Neil, prediction engine) imports from here.

Polygon endpoints used
─────────────────────
  /v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}   — daily bars
  /v2/aggs/ticker/{ticker}/range/1/week/{from}/{to}  — weekly bars
  /v3/reference/tickers/{ticker}                      — company profile

Configuration
─────────────
  Requires POLYGON_API_KEY in the project .env file
  (auto-loaded from the project root).
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

# ─────────────────────────────────────────────────────────────────────────────
# .env loader
# ─────────────────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_env_path = _PROJECT_ROOT / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

POLYGON_API_KEY: str = os.environ.get("POLYGON_API_KEY", "")
BASE_URL = "https://api.polygon.io"

_MAX_RETRIES = 3
_RETRY_SLEEP = 1.5  # seconds, doubled per attempt


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class PolygonDataError(RuntimeError):
    """Raised when Polygon cannot provide data after retries."""


# ─────────────────────────────────────────────────────────────────────────────
# HTTP session
# ─────────────────────────────────────────────────────────────────────────────

_SESSION: Optional[requests.Session] = None


def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers["Authorization"] = f"Bearer {POLYGON_API_KEY}"
    return _SESSION


def _get(path: str, params: Optional[Dict] = None, retries: int = _MAX_RETRIES) -> Optional[Dict]:
    """HTTP GET with retry / rate-limit back-off.  Returns None on soft failure."""
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        try:
            r = _session().get(url, params=params or {}, timeout=15)
            if r.status_code == 403:
                raise PolygonDataError(f"Polygon auth error (403) for {url}. Check POLYGON_API_KEY.")
            if r.status_code == 429:
                time.sleep(_RETRY_SLEEP * (2 ** attempt))
                continue
            r.raise_for_status()
            return r.json()
        except PolygonDataError:
            raise
        except Exception:
            time.sleep(_RETRY_SLEEP * (2 ** attempt))
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public client
# ─────────────────────────────────────────────────────────────────────────────

class PolygonClient:
    """
    Shared Polygon.io OHLCV + profile fetcher used by all agents.

    Usage::
        client = PolygonClient()
        if client.is_available():
            df = client.fetch_daily_bars("AAPL", as_of=date(2026, 3, 1), lookback_days=450)
    """

    def is_available(self) -> bool:
        return bool(POLYGON_API_KEY)

    # ── Daily OHLCV bars (pandas DataFrame) ─────────────────────────────

    def fetch_daily_bars(
        self,
        ticker: str,
        as_of: date,
        lookback_days: int = 450,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch daily adjusted OHLCV bars up to *as_of* (inclusive).

        Returns a DataFrame with columns [Open, High, Low, Close, Volume]
        and a DatetimeIndex, sorted oldest-first.  Returns None on failure.
        """
        ticker = ticker.upper()
        from_date = (as_of - timedelta(days=lookback_days)).isoformat()
        to_date = as_of.isoformat()

        data = _get(
            f"/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}",
            {"adjusted": "true", "sort": "asc", "limit": 50000},
        )
        if not data or "results" not in data:
            return None

        return self._parse_df(data["results"], as_of)

    # ── Weekly OHLCV bars (pandas DataFrame) ────────────────────────────

    def fetch_weekly_bars(
        self,
        ticker: str,
        as_of: date,
        lookback_days: int = 1100,
    ) -> Optional[pd.DataFrame]:
        """Fetch weekly adjusted OHLCV bars up to *as_of*."""
        ticker = ticker.upper()
        from_date = (as_of - timedelta(days=lookback_days)).isoformat()
        to_date = as_of.isoformat()

        data = _get(
            f"/v2/aggs/ticker/{ticker}/range/1/week/{from_date}/{to_date}",
            {"adjusted": "true", "sort": "asc", "limit": 5000},
        )
        if not data or "results" not in data:
            return None

        return self._parse_df(data["results"], as_of)

    # ── Single closing price (for backtest evaluation) ──────────────────

    def get_close_price(
        self,
        ticker: str,
        target_date: date,
    ) -> Optional[Tuple[float, date]]:
        """
        Return (closing_price, actual_bar_date) for the bar on or just
        before *target_date*.  Returns None on failure.
        """
        ticker = ticker.upper()
        from_date = (target_date - timedelta(days=10)).isoformat()
        to_date = target_date.isoformat()

        data = _get(
            f"/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}",
            {"adjusted": "true", "sort": "asc", "limit": 50},
        )
        if not data or "results" not in data or not data["results"]:
            return None

        # Take the last bar (closest to target_date)
        last = data["results"][-1]
        try:
            import datetime
            bar_date = datetime.date.fromtimestamp(last["t"] / 1000.0)
            return float(last["c"]), bar_date
        except (KeyError, TypeError, ValueError):
            return None

    # ── Company profile ─────────────────────────────────────────────────

    def fetch_profile(self, ticker: str) -> Dict[str, str]:
        """
        Return {company_name, sector, industry} from Polygon reference data.
        Falls back to ticker symbol on failure.
        """
        ticker = ticker.upper()
        data = _get(f"/v3/reference/tickers/{ticker}")
        if not data:
            return {"company_name": ticker, "sector": "Unknown", "industry": "Unknown"}

        info = data.get("results", {})
        return {
            "company_name": info.get("name") or ticker,
            "sector": info.get("sic_description") or "Unknown",
            "industry": info.get("sic_description") or "Unknown",
        }

    # ── Parallel daily + weekly fetch (for O'Neil and similar) ──────────

    def fetch_daily_weekly(
        self,
        ticker: str,
        as_of: date,
        daily_lookback: int = 760,
        weekly_lookback: int = 1100,
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Fetch daily and weekly bars in parallel.  Returns (daily_df, weekly_df)."""
        with ThreadPoolExecutor(max_workers=2) as pool:
            d_fut = pool.submit(self.fetch_daily_bars, ticker, as_of, daily_lookback)
            w_fut = pool.submit(self.fetch_weekly_bars, ticker, as_of, weekly_lookback)
        return d_fut.result(), w_fut.result()

    # ── Internal ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_df(results: List[Dict], as_of: date) -> pd.DataFrame:
        """Convert Polygon agg results to a OHLCV DataFrame matching yfinance column names."""
        import datetime as _dt

        rows = []
        for r in results:
            try:
                bar_date = _dt.date.fromtimestamp(r["t"] / 1000.0)
                if bar_date > as_of:
                    continue
                rows.append({
                    "Open": float(r["o"]),
                    "High": float(r["h"]),
                    "Low": float(r["l"]),
                    "Close": float(r["c"]),
                    "Volume": float(r.get("v", 0)),
                    "_date": bar_date,
                })
            except (KeyError, TypeError, ValueError):
                continue

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df.index = pd.DatetimeIndex(df["_date"])
        df.index.name = None
        df = df.drop(columns=["_date"])
        df = df.sort_index()
        return df
