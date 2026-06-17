"""Insider client: SEC EDGAR Form 4 primary, FMP/yfinance fallbacks."""

from __future__ import annotations

import os
from datetime import date
from typing import Optional

from .config import InsiderSettings, load_settings
from .edgar_client import build_snapshot as edgar_snapshot
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

        if prefer in ("auto", "edgar"):
            try:
                snap = edgar_snapshot(ticker, as_of_date, lookback_days=lookback)
                if snap.trades or prefer == "edgar":
                    return snap
            except Exception as exc:
                if prefer == "edgar":
                    snap = InsiderSnapshot(
                        ticker=ticker.upper(),
                        as_of_date=as_of_date,
                        trades=[],
                        data_sources=[],
                        warnings=[f"SEC EDGAR failed: {exc}"],
                    )
                    return snap

        if self._fmp and prefer in ("auto", "fmp"):
            try:
                snap = self._fmp.build_snapshot(ticker, as_of_date)
                if snap.trades:
                    return snap
            except Exception as exc:
                msg = str(exc)
                if "402" in msg or "Payment Required" in msg:
                    yf = yfinance_snapshot(ticker, as_of_date, lookback_days=lookback)
                    yf.warnings.insert(0, "FMP insider endpoint requires paid tier (402) — using yfinance.")
                    return yf

        yf = yfinance_snapshot(ticker, as_of_date, lookback_days=lookback)
        if prefer in ("auto", "edgar") and not yf.trades:
            yf.warnings.insert(0, "No SEC Form 4 trades parsed — fell back to yfinance.")
        return yf


def load_composite_client(api_key: str | None = None) -> CompositeInsiderClient:
    key = api_key or os.getenv("FMP_API_KEY")
    if key:
        try:
            return CompositeInsiderClient(load_settings(api_key=key))
        except Exception:
            pass
    return CompositeInsiderClient(None)
