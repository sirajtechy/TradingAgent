"""
data_client.py — Market data fetcher for the O'Neil Technical Analysis Agent.

Data source priority
────────────────────
  1. Polygon.io OHLCV bars  — US tickers only; higher data quality.
     Loaded from oneil_agent/polygon_client.py.  Requires POLYGON_API_KEY in .env.
  2. Yahoo Finance (yfinance) fallback — all tickers including NSE.

Timeframes:
  Weekly  : 3 years of weekly bars (~156 bars)
             — primary O'Neil timeframe for base patterns + stage analysis
  Daily   : 2 years of daily bars (~504 bars)
             — secondary timeframe used only for the 200-day EMA

NSE support:
  Pass exchange="NSE" to automatically append ".NS" to the ticker symbol
  (e.g. RELIANCE → RELIANCE.NS, TCS → TCS.NS).
  If the ticker already contains "." it is used as-is.

Error handling:
  Raises DataError on fetch failure after up to 3 retries with exponential
  backoff. Callers should wrap analyze_ticker() in try/except DataError.
"""

from __future__ import annotations

import time
import warnings
from datetime import date, timedelta
from typing import List, Optional, Tuple

# yfinance emits FutureWarning/DeprecationWarning on newer pandas versions
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import yfinance as yf

from .models import DailyBar, ONeilRequest, WeeklyBar


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class DataError(RuntimeError):
    """Raised when market data cannot be fetched after retries."""


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_WEEKLY_LOOKBACK_YEARS   = 3      # 3 yr → ~156 weekly bars (stage + patterns)
_DAILY_LOOKBACK_YEARS    = 2      # 2 yr → ~504 daily bars  (200d EMA needs 200)
_MIN_WEEKLY_BARS         = 30     # Minimum for any meaningful analysis
_MIN_DAILY_BARS          = 210    # Enough for 200-day EMA
_MAX_RETRIES             = 3
_RETRY_BASE_SLEEP        = 1.5    # seconds — doubles each attempt


# ─────────────────────────────────────────────────────────────────────────────
# Helper: resolve ticker symbol
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_ticker(ticker: str, exchange: str) -> str:
    """
    Return the yfinance-compatible ticker symbol.

    For NSE (India) stocks: if the ticker has no "." suffix, append ".NS".
    For US stocks: pass through unchanged.
    """
    ticker = ticker.strip().upper()
    if exchange.upper() == "NSE" and "." not in ticker:
        return f"{ticker}.NS"
    return ticker


# ─────────────────────────────────────────────────────────────────────────────
# Helper: safe yfinance history call (with retry)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_history(
    ticker_obj: yf.Ticker,
    symbol: str,
    start: str,
    end: str,
    interval: str,
) -> "pd.DataFrame":  # type: ignore[name-defined]
    """
    Download OHLCV history with up to _MAX_RETRIES on transient failures.
    Returns a pandas DataFrame with DatetimeIndex and columns
    [Open, High, Low, Close, Volume].
    """
    import pandas as pd  # lazy import to avoid hard dependency at module level

    last_exc: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES):
        try:
            df = ticker_obj.history(
                start=start,
                end=end,
                interval=interval,
                auto_adjust=True,
                prepost=False,
                repair=False,
            )
            if df is not None and not df.empty:
                return df
            # Empty frame counts as a soft-fail; wait and retry
            last_exc = ValueError(f"Empty history for {symbol} ({interval})")
        except Exception as exc:
            last_exc = exc

        sleep = _RETRY_BASE_SLEEP * (2 ** attempt)
        time.sleep(sleep)

    raise DataError(
        f"Unable to fetch {interval} data for '{symbol}' after {_MAX_RETRIES} attempts: {last_exc}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Converters: DataFrame row → typed dataclass
# ─────────────────────────────────────────────────────────────────────────────

def _df_to_weekly(df: "pd.DataFrame") -> List[WeeklyBar]:  # type: ignore[name-defined]
    """Convert a yfinance weekly DataFrame to List[WeeklyBar], oldest-first."""
    bars: List[WeeklyBar] = []
    for ts, row in df.iterrows():
        bar_date = ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])
        try:
            bars.append(WeeklyBar(
                bar_date=bar_date,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row.get("Volume", 0)),
            ))
        except (KeyError, TypeError, ValueError):
            continue  # skip malformed rows
    # Sort oldest-first (yfinance is already ascending, but be defensive)
    bars.sort(key=lambda b: b.bar_date)
    return bars


def _df_to_daily(df: "pd.DataFrame") -> List[DailyBar]:  # type: ignore[name-defined]
    """Convert a yfinance daily DataFrame to List[DailyBar], oldest-first."""
    bars: List[DailyBar] = []
    for ts, row in df.iterrows():
        bar_date = ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])
        try:
            bars.append(DailyBar(
                bar_date=bar_date,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row.get("Volume", 0)),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    bars.sort(key=lambda b: b.bar_date)
    return bars


# ─────────────────────────────────────────────────────────────────────────────
# Public data client
# ─────────────────────────────────────────────────────────────────────────────

class ONeilDataClient:
    """
    Fetches weekly and daily OHLCV data for a given ONeilRequest.

    For US tickers, tries Polygon.io first (parallel indicator-grade bars),
    then falls back to yfinance.  NSE tickers always use yfinance.

    Usage::

        client = ONeilDataClient()
        weekly_bars, daily_bars, company_name = client.fetch(request)
    """

    def fetch(
        self,
        request: ONeilRequest,
    ) -> Tuple[List[WeeklyBar], List[DailyBar], str]:
        """
        Download weekly + daily bars for *request.ticker*.

        For US tickers Polygon.io is tried first; yfinance is the fallback
        and the only source for NSE stocks.

        Returns
        -------
        weekly_bars  : List[WeeklyBar]  — 3 years of weekly OHLCV, oldest-first
        daily_bars   : List[DailyBar]   — 2 years of daily OHLCV, oldest-first
        company_name : str              — human-readable company name (or ticker)
        """
        # ── Polygon primary path (US only) ────────────────────────────────
        if request.exchange.upper() == "US":
            try:
                from .polygon_client import PolygonONeilClient, PolygonDataError
                poly = PolygonONeilClient()
                if poly.is_available():
                    weekly_bars, daily_bars, company_name = poly.fetch_bars(request)
                    if len(weekly_bars) >= _MIN_WEEKLY_BARS:
                        return weekly_bars, daily_bars, company_name
            except Exception:
                pass   # fall through to yfinance

        # ── yfinance fallback (all markets) ──────────────────────────────
        symbol = _resolve_ticker(request.ticker, request.exchange)

        # Date ranges, anchored to as_of_date
        end_date  = request.as_of_date + timedelta(days=1)          # yf excludes end
        weekly_start = request.as_of_date - timedelta(days=_WEEKLY_LOOKBACK_YEARS * 365 + 7)
        daily_start  = request.as_of_date - timedelta(days=_DAILY_LOOKBACK_YEARS  * 365 + 30)

        ticker_obj = yf.Ticker(symbol)

        # ── Weekly bars ──────────────────────────────────────────────────
        weekly_df = _fetch_history(
            ticker_obj,
            symbol,
            start=weekly_start.isoformat(),
            end=end_date.isoformat(),
            interval="1wk",
        )
        weekly_bars = _df_to_weekly(weekly_df)

        if len(weekly_bars) < _MIN_WEEKLY_BARS:
            raise DataError(
                f"Insufficient weekly data for '{symbol}': "
                f"got {len(weekly_bars)}, need ≥ {_MIN_WEEKLY_BARS} bars"
            )

        # ── Daily bars ────────────────────────────────────────────────────
        daily_df = _fetch_history(
            ticker_obj,
            symbol,
            start=daily_start.isoformat(),
            end=end_date.isoformat(),
            interval="1d",
        )
        daily_bars = _df_to_daily(daily_df)

        if len(daily_bars) < _MIN_DAILY_BARS:
            # Not a fatal error — EMA-200d will simply return None
            pass

        # ── Company name ─────────────────────────────────────────────────
        company_name = symbol  # safe fallback
        try:
            info = ticker_obj.info or {}
            company_name = info.get("longName") or info.get("shortName") or symbol
        except Exception:
            pass

        return weekly_bars, daily_bars, company_name
