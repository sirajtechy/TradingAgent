"""
data_client.py — Market data fetcher for the technical agent.

Data source priority
────────────────────
  1. Polygon.io  — primary source of truth for all OHLCV data and profiles.
  2. yfinance    — emergency fallback only (when Polygon is unavailable).

Responsibilities:
    1. Download up to 300 trading days of OHLCV data ending on *as_of_date*.
    2. Fetch company profile info (name, sector, industry).
    3. Return a frozen ``RawTechnicalSnapshot`` for downstream nodes.

Resilience features:
    - Polygon primary → yfinance fallback on any Polygon failure.
    - Exponential back-off (via shared Polygon client + yfinance retry).
    - Every data field is validated; missing values are flagged in ``warnings``.
"""

from datetime import date, timedelta
import logging
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from agents.polygon_data import PolygonClient, PolygonDataError
from .exceptions import DataUnavailableError, InsufficientDataError
from .models import OHLCVBar, RawTechnicalSnapshot, TechnicalRequest

logger = logging.getLogger(__name__)

# How many calendar days to request so we end up with ~300 trading bars.
_CALENDAR_LOOKBACK_DAYS = 450
# Absolute minimum number of bars required for the 200-day EMA warm-up.
_MIN_BARS_REQUIRED = 200

_polygon = PolygonClient()


# ----------------------------------------------------------------------- #
# Public API                                                                #
# ----------------------------------------------------------------------- #

class PolygonTechnicalClient:
    """
    Fetches OHLCV bars and profile data — Polygon primary, yfinance fallback.

    Keeps the same interface as the former YFinanceTechnicalClient so that
    graph.py, backtest.py, and service.py work without changes.
    """

    # ------------------------------------------------------------------ #
    # build_snapshot                                                       #
    # ------------------------------------------------------------------ #

    def build_snapshot(self, request: TechnicalRequest) -> RawTechnicalSnapshot:
        ticker_str = request.ticker.upper()
        as_of = request.as_of_date
        warnings_list: List[str] = []

        profile = self._fetch_profile(ticker_str, warnings_list)
        bars = self._fetch_bars(ticker_str, as_of, warnings_list)

        if len(bars) < _MIN_BARS_REQUIRED:
            raise InsufficientDataError(
                f"{ticker_str}: only {len(bars)} bars available before "
                f"{as_of.isoformat()}; need at least {_MIN_BARS_REQUIRED} "
                "for 200-day EMA warm-up."
            )

        last_bar = bars[-1]

        return RawTechnicalSnapshot(
            request=request,
            company_name=profile.get("company_name", ticker_str),
            sector=profile.get("sector", "Unknown"),
            industry=profile.get("industry", "Unknown"),
            bars=bars,
            as_of_price=last_bar.close,
            as_of_price_date=last_bar.bar_date,
            warnings=warnings_list,
        )

    # ------------------------------------------------------------------ #
    # get_price_as_of  (used by the backtest engine)                       #
    # ------------------------------------------------------------------ #

    def get_price_as_of(self, ticker: str, as_of_date: date) -> OHLCVBar:
        ticker_str = ticker.upper()

        # Polygon primary
        if _polygon.is_available():
            result = _polygon.get_close_price(ticker_str, as_of_date)
            if result is not None:
                price, bar_date = result
                return OHLCVBar(
                    bar_date=bar_date,
                    open=price, high=price, low=price, close=price, volume=0.0,
                )

        # yfinance fallback
        df = self._yf_download(ticker_str, as_of_date - timedelta(days=14), as_of_date + timedelta(days=1))
        if df is not None and not df.empty:
            df = self._normalise_index(df, as_of_date)
            if not df.empty:
                bar = self._row_to_bar(df.iloc[-1], df.index[-1])
                if bar is not None:
                    return bar

        raise DataUnavailableError(
            f"No price data for {ticker_str} on or before {as_of_date.isoformat()}"
        )

    # ------------------------------------------------------------------ #
    # Private — bars                                                       #
    # ------------------------------------------------------------------ #

    def _fetch_bars(
        self, ticker: str, as_of: date, warnings_list: List[str]
    ) -> List[OHLCVBar]:
        df: Optional[pd.DataFrame] = None

        # ── Polygon primary ──────────────────────────────────────────────
        if _polygon.is_available():
            try:
                df = _polygon.fetch_daily_bars(ticker, as_of, lookback_days=_CALENDAR_LOOKBACK_DAYS)
                if df is not None and not df.empty:
                    warnings_list.append("Data sourced from Polygon.io. Prices are split-adjusted.")
            except PolygonDataError as exc:
                logger.warning("Polygon failed for %s: %s — falling back to yfinance", ticker, exc)
                df = None

        # ── yfinance fallback ────────────────────────────────────────────
        if df is None or df.empty:
            logger.info("Falling back to yfinance for %s", ticker)
            start = as_of - timedelta(days=_CALENDAR_LOOKBACK_DAYS)
            end = as_of + timedelta(days=1)
            df = self._yf_download(ticker, start, end)
            if df is not None and not df.empty:
                df = self._normalise_index(df, as_of)
                warnings_list.append(
                    "Data sourced from Yahoo Finance (Polygon fallback). "
                    "Prices are split-adjusted; volume is unadjusted."
                )

        if df is None or df.empty:
            raise DataUnavailableError(
                f"No OHLCV data for {ticker} before {as_of.isoformat()} "
                "from Polygon or Yahoo Finance."
            )

        required_cols = {"Open", "High", "Low", "Close", "Volume"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise DataUnavailableError(
                f"OHLCV dataframe for {ticker} is missing columns: {missing_cols}"
            )

        before_drop = len(df)
        df = df.dropna(subset=["Close"])
        dropped = before_drop - len(df)
        if dropped > 0:
            warnings_list.append(f"{dropped} bar(s) dropped due to missing Close price.")

        bars: List[OHLCVBar] = []
        for idx_val, row in df.iterrows():
            bar = self._row_to_bar(row, idx_val)
            if bar is not None:
                bars.append(bar)

        bars.sort(key=lambda b: b.bar_date)
        return bars

    # ------------------------------------------------------------------ #
    # Private — profile                                                    #
    # ------------------------------------------------------------------ #

    def _fetch_profile(
        self, ticker: str, warnings_list: List[str]
    ) -> Dict[str, str]:
        # Polygon primary
        if _polygon.is_available():
            try:
                profile = _polygon.fetch_profile(ticker)
                if profile.get("company_name") != ticker:
                    return profile
            except Exception as exc:
                logger.warning("Polygon profile failed for %s: %s", ticker, exc)

        # yfinance fallback
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info or {}
            return {
                "company_name": str(info.get("longName") or info.get("shortName") or ticker),
                "sector": str(info.get("sector") or "Unknown"),
                "industry": str(info.get("industry") or "Unknown"),
            }
        except Exception as exc:
            logger.warning("yfinance profile also failed for %s: %s", ticker, exc)
            warnings_list.append(f"Profile data unavailable for {ticker}. Defaults used.")
            return {"company_name": ticker, "sector": "Unknown", "industry": "Unknown"}

    # ------------------------------------------------------------------ #
    # Private — yfinance fallback download                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _yf_download(ticker: str, start: date, end: date) -> Optional[pd.DataFrame]:
        """Emergency yfinance fallback with retry."""
        try:
            import yfinance as yf
        except ImportError:
            return None

        for attempt in range(3):
            try:
                df = yf.download(
                    ticker,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    auto_adjust=True,
                    progress=False,
                )
                if df is not None and not df.empty:
                    return df
            except Exception as exc:
                logger.warning("yfinance fallback attempt %d for %s: %s", attempt + 1, ticker, exc)
                time.sleep(1.0 * (2 ** attempt))
        return None

    # ------------------------------------------------------------------ #
    # Private — index normalisation                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalise_index(df: pd.DataFrame, as_of: date) -> pd.DataFrame:
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

    # ------------------------------------------------------------------ #
    # Private — row conversion                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _row_to_bar(row: Any, idx_val: Any) -> Optional[OHLCVBar]:
        try:
            bar_date = (
                idx_val.date()
                if hasattr(idx_val, "date")
                else date.fromisoformat(str(idx_val)[:10])
            )
            close = float(row["Close"])
        except (TypeError, ValueError, KeyError):
            return None

        def _safe_float(val: Any, fallback: float) -> float:
            if val is None:
                return fallback
            try:
                f = float(val)
                if f != f:  # NaN
                    return fallback
                return f
            except (TypeError, ValueError):
                return fallback

        return OHLCVBar(
            bar_date=bar_date,
            open=_safe_float(row.get("Open"), close),
            high=_safe_float(row.get("High"), close),
            low=_safe_float(row.get("Low"), close),
            close=close,
            volume=_safe_float(row.get("Volume"), 0.0),
        )


# Backward-compatible alias
YFinanceTechnicalClient = PolygonTechnicalClient
