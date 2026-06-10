"""News client: FMP when available, yfinance fallback (free)."""

from __future__ import annotations

import os
from datetime import date

from typing import Optional

from .config import NewsSettings, load_settings
from .fmp_client import FMPNewsClient
from .models import NewsSnapshot
from .yfinance_fallback import build_snapshot as yfinance_snapshot


class CompositeNewsClient:
    def __init__(self, settings: Optional[NewsSettings] = None) -> None:
        self._settings = settings
        self._fmp: FMPNewsClient | None = None
        if settings:
            self._fmp = FMPNewsClient(settings)

    def build_snapshot(self, ticker: str, as_of_date: date) -> NewsSnapshot:
        prefer = os.getenv("NEWS_DATA_SOURCE", "auto").strip().lower()

        if prefer == "yfinance":
            return yfinance_snapshot(ticker, as_of_date)

        if self._fmp and prefer in ("auto", "fmp"):
            try:
                snap = self._fmp.build_snapshot(ticker, as_of_date)
                if snap.headlines or snap.grades or snap.price_targets:
                    return snap
            except Exception:
                pass

        return yfinance_snapshot(ticker, as_of_date)


def load_composite_client(api_key: str | None = None) -> CompositeNewsClient:
    key = api_key or os.getenv("FMP_API_KEY")
    if key:
        try:
            return CompositeNewsClient(load_settings(api_key=key))
        except Exception:
            pass
    return CompositeNewsClient(None)
