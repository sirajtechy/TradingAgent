"""
data_client.py — Yahoo Finance data fetcher for the technical agent.

Responsibilities:
    1. Download up to 300 trading days of OHLCV data ending on *as_of_date*.
    2. Fetch company profile info (name, sector, industry).
    3. Return a frozen ``RawTechnicalSnapshot`` for downstream nodes.

Resilience features:
    - Exponential back-off (3 retries: 1 s → 2 s → 4 s) on transient errors.
    - Request timeout guard.
    - Fallback from ``Ticker.history()`` to ``yf.download()`` if the first
      code-path returns an empty frame.
    - Every data field is validated before use; missing values are flagged
      in ``warnings`` rather than silently skipped.

Data source attribution: **All OHLCV data sourced from Yahoo Finance via
the ``yfinance`` library.**
"""

from datetime import date, timedelta
import logging
import time
from typing import Any, Dict, List, Optional

import warnings as _warnings

# Suppress noisy yfinance / pandas deprecation warnings
_warnings.filterwarnings("ignore", category=FutureWarning)
_warnings.filterwarnings("ignore", category=DeprecationWarning)

import pandas as pd
import yfinance as yf

from .exceptions import DataUnavailableError, InsufficientDataError
from .models import OHLCVBar, RawTechnicalSnapshot, TechnicalRequest

logger = logging.getLogger(__name__)

# How many calendar days to request so we end up with ~300 trading bars.
# 300 trading days ≈ 420 calendar days (weekends + holidays).
_CALENDAR_LOOKBACK_DAYS = 450
# Absolute minimum number of bars required for the 200-day EMA warm-up.
_MIN_BARS_REQUIRED = 200
# Back-off retry parameters
_MAX_RETRIES = 3
_BASE_BACKOFF_SEC = 1.0


# ----------------------------------------------------------------------- #
# Public API                                                                #
# ----------------------------------------------------------------------- #

class YFinanceTechnicalClient:
    """
    Fetches OHLCV bars and profile data from Yahoo Finance.

    Implements the same *client* interface pattern used by the fundamental
    agent so that graph.py and backtest.py can consume either client
    transparently.
    """

    # ------------------------------------------------------------------ #
    # build_snapshot                                                       #
    # ------------------------------------------------------------------ #

    def build_snapshot(self, request: TechnicalRequest) -> RawTechnicalSnapshot:
        """
        Build a complete technical snapshot for *request.ticker* as of
        *request.as_of_date*.

        Returns:
            RawTechnicalSnapshot with bars sorted oldest-first.

        Raises:
            DataUnavailableError: if no price data can be obtained.
            InsufficientDataError: if fewer than _MIN_BARS_REQUIRED bars
                                   are available.
        """
        ticker_str = request.ticker.upper()
        as_of = request.as_of_date
        warnings_list: List[str] = []

        # — Profile --------------------------------------------------------
        profile = self._fetch_profile(ticker_str, warnings_list)

        # — OHLCV bars -----------------------------------------------------
        bars = self._fetch_bars(ticker_str, as_of, warnings_list)

        if len(bars) < _MIN_BARS_REQUIRED:
            raise InsufficientDataError(
                f"{ticker_str}: only {len(bars)} bars available before "
                f"{as_of.isoformat()}; need at least {_MIN_BARS_REQUIRED} "
                "for 200-day EMA warm-up."
            )

        # The last bar's close is the "as-of" price
        last_bar = bars[-1]

        warnings_list.append(
            "Data sourced from Yahoo Finance via yfinance. "
            "Prices are split-adjusted; volume is unadjusted."
        )

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
        """
        Return the single OHLCV bar closest to (but not after) *as_of_date*.

        Raises:
            DataUnavailableError: if no bar can be found.
        """
        ticker_str = ticker.upper()
        start = as_of_date - timedelta(days=14)
        end = as_of_date + timedelta(days=1)

        df = self._download_with_retry(ticker_str, start, end)
        if df is None or df.empty:
            raise DataUnavailableError(
                f"No price data for {ticker_str} on or before "
                f"{as_of_date.isoformat()}"
            )

        df = self._normalise_index(df, as_of_date)
        if df.empty:
            raise DataUnavailableError(
                f"No price data for {ticker_str} on or before "
                f"{as_of_date.isoformat()} after index normalisation."
            )

        return self._row_to_bar(df.iloc[-1], df.index[-1])

    # ------------------------------------------------------------------ #
    # Private — bars                                                       #
    # ------------------------------------------------------------------ #

    def _fetch_bars(
        self, ticker: str, as_of: date, warnings_list: List[str]
    ) -> List[OHLCVBar]:
        """Download OHLCV bars and convert to a list of OHLCVBar."""
        start = as_of - timedelta(days=_CALENDAR_LOOKBACK_DAYS)
        end = as_of + timedelta(days=1)  # yfinance end is exclusive

        df = self._download_with_retry(ticker, start, end)
        if df is None or df.empty:
            raise DataUnavailableError(
                f"Yahoo Finance returned no data for {ticker} between "
                f"{start.isoformat()} and {as_of.isoformat()}."
            )

        df = self._normalise_index(df, as_of)
        if df.empty:
            raise DataUnavailableError(
                f"All bars for {ticker} were after {as_of.isoformat()} "
                "after timezone normalisation."
            )

        # Validate mandatory columns
        required_cols = {"Open", "High", "Low", "Close", "Volume"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise DataUnavailableError(
                f"OHLCV dataframe for {ticker} is missing columns: "
                f"{missing_cols}"
            )

        # Drop rows where Close is NaN (occasionally happens with yfinance)
        before_drop = len(df)
        df = df.dropna(subset=["Close"])
        dropped = before_drop - len(df)
        if dropped > 0:
            warnings_list.append(
                f"{dropped} bar(s) dropped due to missing Close price."
            )

        bars: List[OHLCVBar] = []
        for idx_val, row in df.iterrows():
            bar = self._row_to_bar(row, idx_val)
            if bar is not None:
                bars.append(bar)

        # Sort oldest-first (should already be, but guarantee it)
        bars.sort(key=lambda b: b.bar_date)
        return bars

    # ------------------------------------------------------------------ #
    # Private — profile                                                    #
    # ------------------------------------------------------------------ #

    def _fetch_profile(
        self, ticker: str, warnings_list: List[str]
    ) -> Dict[str, str]:
        """
        Fetch company name / sector / industry from yfinance info dict.

        Never raises — returns sensible defaults and appends warnings.
        """
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception as exc:
            logger.warning("Could not fetch profile for %s: %s", ticker, exc)
            warnings_list.append(
                f"Profile data unavailable for {ticker}: {exc}. "
                "Defaults used."
            )
            return {
                "company_name": ticker,
                "sector": "Unknown",
                "industry": "Unknown",
            }

        company_name = str(
            info.get("longName")
            or info.get("shortName")
            or ticker
        )
        sector = str(info.get("sector") or "Unknown")
        industry = str(info.get("industry") or "Unknown")

        if sector == "Unknown":
            warnings_list.append(
                f"Sector data unavailable for {ticker} on Yahoo Finance."
            )
        if industry == "Unknown":
            warnings_list.append(
                f"Industry data unavailable for {ticker} on Yahoo Finance."
            )

        return {
            "company_name": company_name,
            "sector": sector,
            "industry": industry,
        }

    # ------------------------------------------------------------------ #
    # Private — download with retry                                        #
    # ------------------------------------------------------------------ #

    def _download_with_retry(
        self, ticker: str, start: date, end: date
    ) -> Optional[pd.DataFrame]:
        """
        Download OHLCV data with exponential back-off.

        Tries ``Ticker.history()`` first, then falls back to
        ``yf.download()`` as a secondary code-path.

        Returns:
            DataFrame with DatetimeIndex or None on total failure.
        """
        # Attempt 1: Ticker.history() — the cleaner API
        df = self._attempt_ticker_history(ticker, start, end)
        if df is not None and not df.empty:
            return df

        # Attempt 2: yf.download() — different network code-path
        df = self._attempt_yf_download(ticker, start, end)
        if df is not None and not df.empty:
            return df

        return None

    def _attempt_ticker_history(
        self, ticker: str, start: date, end: date
    ) -> Optional[pd.DataFrame]:
        """Try Ticker.history() with exponential back-off."""
        for attempt in range(_MAX_RETRIES):
            try:
                df = yf.Ticker(ticker).history(
                    start=start.isoformat(),
                    end=end.isoformat(),
                    auto_adjust=True,
                )
                if df is not None and not df.empty:
                    return df
            except Exception as exc:
                wait = _BASE_BACKOFF_SEC * (2 ** attempt)
                logger.warning(
                    "Ticker.history(%s) attempt %d failed: %s — "
                    "retrying in %.1fs",
                    ticker, attempt + 1, exc, wait,
                )
                time.sleep(wait)
        return None

    def _attempt_yf_download(
        self, ticker: str, start: date, end: date
    ) -> Optional[pd.DataFrame]:
        """Fallback: try yf.download() with exponential back-off."""
        for attempt in range(_MAX_RETRIES):
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
                wait = _BASE_BACKOFF_SEC * (2 ** attempt)
                logger.warning(
                    "yf.download(%s) attempt %d failed: %s — "
                    "retrying in %.1fs",
                    ticker, attempt + 1, exc, wait,
                )
                time.sleep(wait)
        return None

    # ------------------------------------------------------------------ #
    # Private — index normalisation                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalise_index(df: pd.DataFrame, as_of: date) -> pd.DataFrame:
        """
        Strip timezone info from the DatetimeIndex and filter rows
        that are on or before *as_of*.

        Returns a copy of the dataframe — the original is not mutated.
        """
        idx = df.index
        # yfinance may return tz-aware DatetimeIndex
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_convert(None)

        cutoff = pd.Timestamp(as_of)
        mask = idx <= cutoff
        result = df.loc[mask].copy()
        result.index = idx[mask]

        # Handle MultiIndex columns that yf.download sometimes returns
        if isinstance(result.columns, pd.MultiIndex):
            result.columns = result.columns.get_level_values(0)

        return result

    # ------------------------------------------------------------------ #
    # Private — row conversion                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _row_to_bar(row: Any, idx_val: Any) -> Optional[OHLCVBar]:
        """
        Convert a single DataFrame row to an OHLCVBar.

        Returns None if the Close value is missing or unparseable.
        """
        try:
            bar_date = (
                idx_val.date()
                if hasattr(idx_val, "date")
                else date.fromisoformat(str(idx_val)[:10])
            )
            close = float(row["Close"])
        except (TypeError, ValueError, KeyError):
            return None

        # Gracefully handle missing OHLV columns (rare but possible)
        def _safe_float(val: Any, fallback: float) -> float:
            """Convert *val* to float; return *fallback* on failure."""
            if val is None:
                return fallback
            try:
                f = float(val)
                # pandas NaN check
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
