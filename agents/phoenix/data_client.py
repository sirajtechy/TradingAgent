"""
data_client.py — Polygon OHLCV wrapper for the Phoenix Agent.

Responsibilities:
  1. Fetch 500+ daily bars ending on as_of_date from Polygon.io.
  2. Compute SMA10, SMA20, SMA50, SMA200 (and prior-period values for slopes).
  3. Compute 20-bar average volume.
  4. Derive 52-week high/low from the last 252 trading bars.
  5. Return a PhoenixSnapshot ready for the pipeline.

Data source: Polygon.io (primary), yfinance (emergency fallback).
The shared PolygonClient from agents/polygon_data/ handles rate-limiting,
retries, and auth.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import date, timedelta
from typing import List, Optional

import pandas as pd

from agents.polygon_data import PolygonClient, PolygonDataError
from .config import PhoenixSettings
from .exceptions import DataUnavailableError, InsufficientDataError
from .models import OHLCVBar, PhoenixRequest, PhoenixSnapshot, SMABundle

logger = logging.getLogger(__name__)

_CALENDAR_LOOKBACK_DAYS = 800   # ~550 trading bars (500 + warm-up buffer)
_MIN_BARS_REQUIRED = 210        # need 200 for SMA200 warm-up + small buffer
_52W_BARS = 252                 # trading bars in one calendar year

_polygon = PolygonClient()

# yfinance is not thread-safe — serialise all downloads
_YF_DOWNLOAD_LOCK = threading.Lock()

# If set, Phoenix will never use yfinance fallback.
# This guarantees OHLCV data provenance is Polygon-only.
_POLYGON_ONLY = os.environ.get("PHOENIX_POLYGON_ONLY", "").strip().lower() in {"1", "true", "yes", "y"}


# ─────────────────────────────────────────────────────────────────────────────
# SMA helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sma_series(values: List[float], period: int) -> List[Optional[float]]:
    """Compute a full SMA series (oldest-first). Returns None where insufficient data."""
    n = len(values)
    result: List[Optional[float]] = [None] * n
    if period <= 0 or n < period:
        return result
    window_sum = sum(values[:period])
    result[period - 1] = window_sum / period
    for i in range(period, n):
        window_sum += values[i] - values[i - period]
        result[i] = window_sum / period
    return result


def _last_valid(series: List[Optional[float]]) -> Optional[float]:
    """Return the most-recent non-None value from a series."""
    for v in reversed(series):
        if v is not None:
            return v
    return None


def _prior_valid(series: List[Optional[float]], lookback: int = 5) -> Optional[float]:
    """Return the value `lookback` positions before the last valid entry."""
    valid = [(i, v) for i, v in enumerate(series) if v is not None]
    if len(valid) <= lookback:
        return valid[0][1] if valid else None
    return valid[-(lookback + 1)][1]


# ─────────────────────────────────────────────────────────────────────────────
# Public client
# ─────────────────────────────────────────────────────────────────────────────

class PhoenixDataClient:
    """
    Fetches and prepares all market data needed by the Phoenix Agent pipeline.

    Usage::
        client = PhoenixDataClient()
        snap = client.build_snapshot("CRWD", "2026-04-10")
        # snap is a PhoenixSnapshot ready for filters.apply_hard_filters()
    """

    def build_snapshot(
        self,
        ticker: str,
        as_of_date: str | date,
        settings: Optional[PhoenixSettings] = None,
    ) -> PhoenixSnapshot:
        """
        Build a complete PhoenixSnapshot for *ticker* as of *as_of_date*.

        Parameters
        ----------
        ticker:       Stock symbol (case-insensitive).
        as_of_date:   ISO date string or date object.  No future data is used.
        settings:     Optional PhoenixSettings; defaults are used if None.

        Raises
        ------
        DataUnavailableError    — Polygon and yfinance both failed.
        InsufficientDataError   — Fewer bars than _MIN_BARS_REQUIRED returned.
        """
        if settings is None:
            settings = PhoenixSettings()

        ticker = ticker.upper()
        as_of = date.fromisoformat(str(as_of_date)) if isinstance(as_of_date, str) else as_of_date

        warnings: list[str] = []
        bars = self._fetch_bars(ticker, as_of, warnings)

        if len(bars) < _MIN_BARS_REQUIRED:
            raise InsufficientDataError(
                f"{ticker}: only {len(bars)} bars available before "
                f"{as_of.isoformat()}; need at least {_MIN_BARS_REQUIRED} "
                "for SMA200 warm-up."
            )

        # Limit to most recent 500 bars for pattern detection
        bars_for_analysis = bars[-500:] if len(bars) > 500 else bars
        closes = [b.close for b in bars_for_analysis]
        volumes = [b.volume for b in bars_for_analysis]

        # ── Compute SMAs ─────────────────────────────────────────────────
        sma10_series  = _sma_series(closes, settings.ma_short)   # 10
        sma20_series  = _sma_series(closes, settings.ma_mid)     # 20
        sma50_series  = _sma_series(closes, settings.ma_long)    # 50
        sma200_series = _sma_series(closes, settings.ma_trend)   # 200

        sma10  = _last_valid(sma10_series)
        sma20  = _last_valid(sma20_series)
        sma50  = _last_valid(sma50_series)
        sma200 = _last_valid(sma200_series)

        # Prior values (5 bars ago) used for slope computation in stage classifier
        sma10_prior  = _prior_valid(sma10_series, 5)
        sma20_prior  = _prior_valid(sma20_series, 5)
        sma50_prior  = _prior_valid(sma50_series, 5)
        sma200_prior = _prior_valid(sma200_series, 5)

        # 40-week SMA uses the same 200-bar period (40w ≈ 200 trading days)
        sma40w = sma200

        smas = SMABundle(
            sma10=sma10,
            sma20=sma20,
            sma50=sma50,
            sma200=sma200,
            sma40w=sma40w,
            sma10_prior=sma10_prior,
            sma20_prior=sma20_prior,
            sma50_prior=sma50_prior,
            sma200_prior=sma200_prior,
        )

        # ── 20-bar average volume ─────────────────────────────────────────
        recent_vols = volumes[-settings.volume_lookback_bars:]
        vol_avg_20 = sum(recent_vols) / len(recent_vols) if recent_vols else 0.0

        # ── 52-week high/low ─────────────────────────────────────────────
        bars_52w = bars_for_analysis[-_52W_BARS:] if len(bars_for_analysis) >= _52W_BARS else bars_for_analysis
        high_52w = max(b.high for b in bars_52w)
        low_52w  = min(b.low  for b in bars_52w)

        last_bar = bars_for_analysis[-1]

        return PhoenixSnapshot(
            request=PhoenixRequest(ticker=ticker, as_of_date=as_of),
            bars=bars_for_analysis,
            smas=smas,
            vol_avg_20=vol_avg_20,
            high_52w=high_52w,
            low_52w=low_52w,
            as_of_price=last_bar.close,
            as_of_price_date=last_bar.bar_date,
            warnings=warnings,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Private — bar fetching
    # ─────────────────────────────────────────────────────────────────────

    def _fetch_bars(
        self, ticker: str, as_of: date, warnings: list[str]
    ) -> List[OHLCVBar]:
        df: Optional[pd.DataFrame] = None

        if _POLYGON_ONLY and not _polygon.is_available():
            raise DataUnavailableError(
                "PHOENIX_POLYGON_ONLY is set but POLYGON_API_KEY is missing. "
                "Set POLYGON_API_KEY (and ensure Polygon has access) to run."
            )

        # Polygon primary
        if _polygon.is_available():
            try:
                df = _polygon.fetch_daily_bars(ticker, as_of, lookback_days=_CALENDAR_LOOKBACK_DAYS)
                if df is not None and not df.empty:
                    warnings.append("Data sourced from Polygon.io (split-adjusted).")
            except PolygonDataError as exc:
                if _POLYGON_ONLY:
                    raise DataUnavailableError(
                        f"{ticker}: Polygon failed and PHOENIX_POLYGON_ONLY is enabled: {exc}"
                    ) from exc
                logger.warning("Polygon failed for %s: %s — falling back to yfinance", ticker, exc)
                df = None

        # yfinance fallback
        if (df is None or df.empty) and not _POLYGON_ONLY:
            logger.info("Falling back to yfinance for %s", ticker)
            start = as_of - timedelta(days=_CALENDAR_LOOKBACK_DAYS)
            df = self._yf_download(ticker, start, as_of)
            if df is not None and not df.empty:
                df = self._normalise_df(df, as_of)
                warnings.append("Data sourced from Yahoo Finance (Polygon fallback).")

        if df is None or df.empty:
            raise DataUnavailableError(
                f"No OHLCV data for {ticker} on or before {as_of.isoformat()} "
                + ("from Polygon (POLYGON_ONLY)." if _POLYGON_ONLY else "from Polygon or Yahoo Finance.")
            )

        # Drop rows without Close
        df = df.dropna(subset=["Close"])
        if df.empty:
            raise DataUnavailableError(f"All bars for {ticker} had null Close prices.")

        bars: List[OHLCVBar] = []
        for idx_val, row in df.iterrows():
            bar = self._row_to_bar(row, idx_val)
            if bar is not None:
                bars.append(bar)

        bars.sort(key=lambda b: b.bar_date)
        return bars

    # ─────────────────────────────────────────────────────────────────────
    # Private — yfinance fallback
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _yf_download(ticker: str, start: date, end: date) -> Optional[pd.DataFrame]:
        try:
            import yfinance as yf  # lazy import
        except ImportError:
            return None

        for attempt in range(3):
            try:
                with _YF_DOWNLOAD_LOCK:
                    df = yf.download(
                        ticker,
                        start=start.isoformat(),
                        end=(end + timedelta(days=1)).isoformat(),
                        auto_adjust=True,
                        progress=False,
                    )
                if df is not None and not df.empty:
                    return df
            except Exception as exc:
                logger.debug("yfinance attempt %d for %s: %s", attempt + 1, ticker, exc)
                time.sleep(1.0 * (2 ** attempt))
        return None

    @staticmethod
    def _normalise_df(df: pd.DataFrame, as_of: date) -> pd.DataFrame:
        idx = df.index
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_convert(None)
        cutoff = pd.Timestamp(as_of)
        mask = idx <= cutoff
        result = df.loc[mask].copy()
        result.index = idx[mask]
        if isinstance(result.columns, pd.MultiIndex):
            result.columns = result.columns.get_level_values(0)
        return result

    @staticmethod
    def _row_to_bar(row, idx_val) -> Optional[OHLCVBar]:
        try:
            bar_date = (
                idx_val.date()
                if hasattr(idx_val, "date")
                else date.fromisoformat(str(idx_val)[:10])
            )
            close = float(row["Close"])
        except (TypeError, ValueError, KeyError):
            return None

        def _sf(val, fallback: float) -> float:
            try:
                f = float(val)
                return fallback if f != f else f  # guard NaN
            except (TypeError, ValueError):
                return fallback

        return OHLCVBar(
            bar_date=bar_date,
            open=_sf(row.get("Open"), close),
            high=_sf(row.get("High"), close),
            low=_sf(row.get("Low"), close),
            close=close,
            volume=_sf(row.get("Volume"), 0.0),
        )
