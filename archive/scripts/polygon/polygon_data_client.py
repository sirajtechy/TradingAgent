"""
polygon_data_client.py — Reusable Polygon.io data client with Excel caching.

Fetches daily + weekly OHLCV bars for any US ticker, caches to Excel
in data/polygon_cache/ for future ML training.
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
import requests

# ─────────────────────────────────────────────────────────────────────────────
# Load .env
# ─────────────────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
import paths

_env_path = paths.ENV_FILE
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

API_KEY = os.environ.get("POLYGON_API_KEY", "")
BASE_URL = "https://api.polygon.io"
CACHE_DIR = paths.POLYGON_CACHE
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class PolygonDataClient:
    """Reusable Polygon.io data client with caching."""

    def __init__(self, api_key: str = ""):
        self._key = api_key or API_KEY
        if not self._key:
            raise RuntimeError("POLYGON_API_KEY not set")
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {self._key}"

    # ── HTTP ─────────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict = None, retries: int = 3) -> Optional[dict]:
        url = f"{BASE_URL}{path}"
        for attempt in range(retries):
            try:
                r = self._session.get(url, params=params or {}, timeout=15)
                if r.status_code == 429:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                r.raise_for_status()
                return r.json()
            except Exception:
                if attempt == retries - 1:
                    return None
                time.sleep(0.5 * (attempt + 1))
        return None

    # ── OHLCV bars ───────────────────────────────────────────────────────

    def fetch_bars(
        self, ticker: str, timespan: str = "day",
        from_date: str = "", to_date: str = "",
        lookback_days: int = 730,
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV bars. timespan = 'day' or 'week'."""
        to_d = to_date or date.today().isoformat()
        from_d = from_date or (date.fromisoformat(to_d) - timedelta(days=lookback_days)).isoformat()

        data = self._get(
            f"/v2/aggs/ticker/{ticker}/range/1/{timespan}/{from_d}/{to_d}",
            {"adjusted": "true", "sort": "asc", "limit": 50000},
        )
        if not data or "results" not in data:
            return None

        df = pd.DataFrame(data["results"])
        df = df.rename(columns={
            "o": "open", "h": "high", "l": "low", "c": "close",
            "v": "volume", "vw": "vwap", "t": "timestamp",
        })
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.date
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def fetch_daily_weekly(
        self, ticker: str, to_date: str = "", lookback_days: int = 730,
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Fetch daily + weekly bars in parallel."""
        with ThreadPoolExecutor(max_workers=2) as pool:
            d_fut = pool.submit(self.fetch_bars, ticker, "day", "", to_date, lookback_days)
            w_fut = pool.submit(self.fetch_bars, ticker, "week", "", to_date, lookback_days)
        return d_fut.result(), w_fut.result()

    # ── Indicators from Polygon ──────────────────────────────────────────

    def fetch_indicators(
        self, ticker: str, timespan: str = "day",
    ) -> Dict[str, Optional[float]]:
        """Fetch SMA/EMA/RSI/MACD from Polygon indicator endpoints."""
        jobs = {
            "sma_20": (f"/v1/indicators/sma/{ticker}", {"timespan": timespan, "window": 20, "limit": 1}),
            "sma_50": (f"/v1/indicators/sma/{ticker}", {"timespan": timespan, "window": 50, "limit": 1}),
            "sma_200": (f"/v1/indicators/sma/{ticker}", {"timespan": timespan, "window": 200, "limit": 1}),
            "ema_9": (f"/v1/indicators/ema/{ticker}", {"timespan": timespan, "window": 9, "limit": 1}),
            "ema_21": (f"/v1/indicators/ema/{ticker}", {"timespan": timespan, "window": 21, "limit": 1}),
            "rsi_14": (f"/v1/indicators/rsi/{ticker}", {"timespan": timespan, "window": 14, "limit": 1}),
            "macd": (f"/v1/indicators/macd/{ticker}", {"timespan": timespan, "short_window": 12, "long_window": 26, "signal_window": 9, "limit": 1}),
        }

        results = {}
        with ThreadPoolExecutor(max_workers=7) as pool:
            futures = {pool.submit(self._get, path, params): name for name, (path, params) in jobs.items()}
            for fut in futures:
                name = futures[fut]
                data = fut.result()
                vals = (data or {}).get("results", {}).get("values", [])
                if name == "macd" and vals:
                    v = vals[0]
                    results["macd_line"] = v.get("value")
                    results["macd_signal"] = v.get("signal")
                    results["macd_hist"] = v.get("histogram")
                elif vals:
                    results[name] = vals[0].get("value")
                else:
                    if name == "macd":
                        results["macd_line"] = None
                        results["macd_signal"] = None
                        results["macd_hist"] = None
                    else:
                        results[name] = None
        return results

    # ── Excel persistence ────────────────────────────────────────────────

    def save_to_excel(self, ticker: str, daily_df: pd.DataFrame, weekly_df: pd.DataFrame = None) -> Path:
        """Save OHLCV dataframes to Excel for ML training."""
        path = CACHE_DIR / f"{ticker}_polygon_data.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            if daily_df is not None and not daily_df.empty:
                daily_df.to_excel(writer, sheet_name="daily", index=False)
            if weekly_df is not None and not weekly_df.empty:
                weekly_df.to_excel(writer, sheet_name="weekly", index=False)
        return path

    def load_cached(self, ticker: str, sheet: str = "daily") -> Optional[pd.DataFrame]:
        """Load cached data from Excel if available."""
        path = CACHE_DIR / f"{ticker}_polygon_data.xlsx"
        if not path.exists():
            return None
        try:
            return pd.read_excel(path, sheet_name=sheet)
        except Exception:
            return None
