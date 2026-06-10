"""Insider client: FMP when available, yfinance fallback (free)."""

from __future__ import annotations

import os
from datetime import date
from typing import Optional

from .config import InsiderSettings, load_settings
from .fmp_client import FMPInsiderClient
from .models import InsiderSnapshot
from .yfinance_fallback import build_snapshot as yfinance_snapshot


class CompositeInsiderClient:
    def __init__(self, settings: Optional[InsiderSettings] = None) -> None:
        self._settings = settings
        self._fmp: FMPInsiderClient | None = None
        if settings:
            self._fmp = FMPInsiderClient(settings)

    def build_snapshot(self, ticker: str, as_of_date: date) -> InsiderSnapshot:
        prefer = os.getenv("INSIDER_DATA_SOURCE", "auto").strip().lower()
        lookback = self._settings.lookback_days if self._settings else 90

        if prefer == "yfinance":
            return yfinance_snapshot(ticker, as_of_date, lookback_days=lookback)

        if self._fmp and prefer in ("auto", "fmp"):
            try:
                snap = self._fmp.build_snapshot(ticker, as_of_date)
                if snap.trades:
                    return snap
            except Exception:
                pass

        return yfinance_snapshot(ticker, as_of_date, lookback_days=lookback)


def load_composite_client(api_key: str | None = None) -> CompositeInsiderClient:
    key = api_key or os.getenv("FMP_API_KEY")
    if key:
        try:
            return CompositeInsiderClient(load_settings(api_key=key))
        except Exception:
            pass
    return CompositeInsiderClient(None)
