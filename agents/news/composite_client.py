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
            except Exception as exc:
                msg = str(exc)
                if "402" in msg or "Payment Required" in msg:
                    finnhub = _try_finnhub(ticker, as_of_date)
                    if finnhub.headlines:
                        return finnhub
                    yf = yfinance_snapshot(ticker, as_of_date)
                    yf.warnings.insert(
                        0,
                        "FMP news/grades endpoint requires paid tier (402) — using yfinance headlines.",
                    )
                    return yf

        finnhub = _try_finnhub(ticker, as_of_date)
        if finnhub.headlines:
            return finnhub

        return yfinance_snapshot(ticker, as_of_date)


def _try_finnhub(ticker: str, as_of_date: date) -> NewsSnapshot:
    from .finnhub_client import build_snapshot as finnhub_snapshot, is_available

    if not is_available():
        return NewsSnapshot(ticker=ticker, as_of_date=as_of_date, headlines=[], data_sources=[], warnings=[])
    try:
        return finnhub_snapshot(ticker, as_of_date)
    except Exception:
        return NewsSnapshot(ticker=ticker, as_of_date=as_of_date, headlines=[], data_sources=[], warnings=[])


def load_composite_client(api_key: str | None = None) -> CompositeNewsClient:
    key = api_key or os.getenv("FMP_API_KEY")
    if key:
        try:
            return CompositeNewsClient(load_settings(api_key=key))
        except Exception:
            pass
    return CompositeNewsClient(None)
