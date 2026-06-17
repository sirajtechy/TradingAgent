"""Fetch and cache OHLCV panels for portfolio scoring."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Dict, List, Optional

import pandas as pd

from agents.polygon_data import PolygonClient


class PriceDataProvider:
    """Point-in-time daily bars with in-memory cache for backtest loops."""

    def __init__(self, client: Optional[PolygonClient] = None) -> None:
        self._client = client or PolygonClient()
        self._cache: Dict[str, pd.DataFrame] = {}

    @property
    def available(self) -> bool:
        return self._client.is_available()

    def get_daily(self, ticker: str, as_of: date, lookback_days: int = 400) -> Optional[pd.DataFrame]:
        key = f"{ticker.upper()}:{as_of.isoformat()}:{lookback_days}"
        if key in self._cache:
            return self._cache[key]
        df = self._client.fetch_daily_bars(ticker, as_of, lookback_days=lookback_days)
        if df is not None and not df.empty:
            self._cache[key] = df
        return df

    def get_weekly(self, ticker: str, as_of: date, lookback_days: int = 1100) -> Optional[pd.DataFrame]:
        key = f"W:{ticker.upper()}:{as_of.isoformat()}"
        if key in self._cache:
            return self._cache[key]
        df = self._client.fetch_weekly_bars(ticker, as_of, lookback_days=lookback_days)
        if df is not None and not df.empty:
            self._cache[key] = df
        return df

    def get_close_on(self, ticker: str, as_of: date) -> Optional[float]:
        df = self.get_daily(ticker, as_of, lookback_days=30)
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[-1])

    def batch_daily(
        self,
        tickers: List[str],
        as_of: date,
        *,
        lookback_days: int = 400,
        max_workers: int = 8,
    ) -> Dict[str, pd.DataFrame]:
        out: Dict[str, pd.DataFrame] = {}
        if not tickers:
            return out

        def _fetch(sym: str) -> tuple[str, Optional[pd.DataFrame]]:
            return sym, self.get_daily(sym, as_of, lookback_days=lookback_days)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futs = {pool.submit(_fetch, t): t for t in tickers}
            for fut in as_completed(futs):
                sym, df = fut.result()
                if df is not None and not df.empty:
                    out[sym.upper()] = df
        return out
