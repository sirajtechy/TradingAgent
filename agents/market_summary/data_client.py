from __future__ import annotations

import os
from datetime import date
from typing import List, Optional, Tuple

import pandas as pd

from agents.polygon_data import PolygonClient

from .config import MarketSummarySettings
from .models import MarketDataSnapshot, TickerPerformance
from .yfinance_fallback import build_snapshot as yfinance_snapshot


class MarketSummaryDataClient:
    """Market-wide OHLCV: Polygon when available, yfinance fallback (free)."""

    def __init__(self, settings: Optional[MarketSummarySettings] = None) -> None:
        self._settings = settings or MarketSummarySettings()
        self._polygon = PolygonClient()

    def is_available(self) -> bool:
        return self._polygon.is_available()

    def build_snapshot(self, as_of_date: date) -> MarketDataSnapshot:
        prefer = os.getenv("MARKET_DATA_SOURCE", "auto").strip().lower()

        if prefer == "yfinance":
            return yfinance_snapshot(as_of_date, self._settings)

        if self.is_available() and prefer in ("auto", "polygon"):
            try:
                snap = self._build_polygon_snapshot(as_of_date)
                if snap.vix is not None or snap.spy is not None:
                    return snap
            except Exception:
                pass

        return yfinance_snapshot(as_of_date, self._settings)

    def _build_polygon_snapshot(self, as_of_date: date) -> MarketDataSnapshot:
        sources: List[str] = ["polygon:/v2/aggs"]
        warnings: List[str] = []

        vix_close, vix_warn = self._fetch_vix(as_of_date)
        warnings.extend(vix_warn)
        vix_regime = _vix_regime(vix_close, self._settings)

        spy_perf, spy_warn = self._fetch_performance(
            self._settings.benchmark_ticker,
            "S&P 500",
            as_of_date,
            vs_spy_20d=None,
        )
        warnings.extend(spy_warn)

        sectors: List[TickerPerformance] = []
        spy_20d = spy_perf.change_20d_pct if spy_perf else None
        for ticker in self._settings.sector_etfs:
            label = self._settings.sector_labels.get(ticker, ticker)
            perf, sector_warn = self._fetch_performance(
                ticker,
                label,
                as_of_date,
                vs_spy_20d=spy_20d,
            )
            warnings.extend(sector_warn)
            if perf is not None:
                sectors.append(perf)

        return MarketDataSnapshot(
            as_of_date=as_of_date,
            vix=vix_close,
            vix_regime=vix_regime,
            spy=spy_perf,
            sectors=sectors,
            data_sources=sources,
            warnings=warnings,
        )

    def _fetch_vix(self, as_of_date: date) -> Tuple[Optional[float], List[str]]:
        warnings: List[str] = []
        for ticker in (self._settings.vix_ticker, "VIX"):
            df = self._polygon.fetch_daily_bars(ticker, as_of_date, lookback_days=10)
            if df is not None and not df.empty:
                return float(df["Close"].iloc[-1]), warnings
        warnings.append("VIX data unavailable from Polygon")
        return None, warnings

    def _fetch_performance(
        self,
        ticker: str,
        label: str,
        as_of_date: date,
        *,
        vs_spy_20d: Optional[float],
    ) -> Tuple[Optional[TickerPerformance], List[str]]:
        warnings: List[str] = []
        df = self._polygon.fetch_daily_bars(ticker, as_of_date, lookback_days=self._settings.lookback_days)
        if df is None or df.empty:
            warnings.append(f"No Polygon bars for {ticker}")
            return None, warnings

        close = float(df["Close"].iloc[-1])
        change_5d = _pct_change_over_bars(df, self._settings.short_window)
        change_20d = _pct_change_over_bars(df, self._settings.long_window)
        vs_spy = None
        if change_20d is not None and vs_spy_20d is not None:
            vs_spy = round(change_20d - vs_spy_20d, 2)

        return (
            TickerPerformance(
                ticker=ticker,
                label=label,
                close=round(close, 2),
                change_5d_pct=change_5d,
                change_20d_pct=change_20d,
                vs_spy_20d_pct=vs_spy,
            ),
            warnings,
        )


def _pct_change_over_bars(df: pd.DataFrame, bars_back: int) -> Optional[float]:
    if len(df) <= bars_back:
        return None
    latest = float(df["Close"].iloc[-1])
    prior = float(df["Close"].iloc[-1 - bars_back])
    if prior == 0:
        return None
    return round(((latest - prior) / abs(prior)) * 100.0, 2)


def _vix_regime(vix: Optional[float], settings: MarketSummarySettings) -> str:
    if vix is None:
        return "unknown"
    if vix < settings.vix_low:
        return "low"
    if vix < settings.vix_normal:
        return "normal"
    if vix < settings.vix_fear:
        return "fear"
    return "extreme"
