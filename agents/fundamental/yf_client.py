"""
yfinance data client — mirrors the same interface as FMPClient.build_snapshot()
so the graph, rules, and backtest engine need zero changes.

Data source priority for PRICES:
  1. Polygon.io — primary source of truth for OHLCV / price data.
  2. yfinance   — emergency fallback.

Financial statements (income, balance, cashflow, dividends) still use
yfinance because Polygon.io does not serve fundamental data.
"""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
import logging
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import yfinance as yf

from agents.polygon_data import PolygonClient, PolygonDataError
from .exceptions import DataUnavailableError
from .models import (
    AnalysisRequest,
    DividendEvent,
    PricePoint,
    Profile,
    RawFundamentalSnapshot,
    StatementEntry,
)

logger = logging.getLogger(__name__)
_polygon = PolygonClient()


class YFinanceClient:
    """
    Fetches data from Yahoo Finance via yfinance.
    Provides the same build_snapshot() interface as FMPClient so it can be
    swapped in without touching the graph, rules, or backtest layers.

    Point-in-time note: yfinance does not support filing-date filtering.
    All statements returned are against the actual fiscal-year-end dates.
    For backtesting we include statements whose period-end date is before
    the as_of_date, which is a reasonable approximation.
    """

    def build_snapshot(self, request: AnalysisRequest) -> RawFundamentalSnapshot:
        ticker_obj = yf.Ticker(request.ticker)
        info = self._safe_info(ticker_obj, request.ticker)

        profile = self._build_profile(request.ticker, info)
        income_statements = self._build_income_statements(ticker_obj, request.as_of_date)
        balance_statements = self._build_balance_statements(ticker_obj, request.as_of_date)
        cashflow_statements = self._build_cashflow_statements(ticker_obj, request.as_of_date)
        dividend_events = self._build_dividend_events(ticker_obj, request.as_of_date)
        price_point = self._build_price_point(ticker_obj, request.ticker, request.as_of_date)

        warnings_list: List[str] = [
            "Data sourced from Yahoo Finance via yfinance. Filing dates are approximated from fiscal-year-end dates.",
            "The Shariah impure revenue screen uses interest income as a proxy for non-compliant income.",
        ]
        if not dividend_events:
            warnings_list.append("No dividend history found for this ticker on Yahoo Finance.")
        if len(income_statements) < 2:
            warnings_list.append("Less than two annual income statements are available as of the requested date.")

        return RawFundamentalSnapshot(
            request=request,
            profile=profile,
            price_point=price_point,
            income_statements=income_statements,
            balance_statements=balance_statements,
            cashflow_statements=cashflow_statements,
            dividend_events=dividend_events,
            warnings=warnings_list,
        )

    # ------------------------------------------------------------------ #
    # Price — Polygon primary, yfinance fallback                           #
    # ------------------------------------------------------------------ #

    def _build_price_point(self, ticker_obj: yf.Ticker, ticker: str, as_of_date: date) -> PricePoint:
        # ── Polygon primary ──────────────────────────────────────────────
        if _polygon.is_available():
            try:
                result = _polygon.get_close_price(ticker, as_of_date)
                if result is not None:
                    price, bar_date = result
                    return PricePoint(price_date=bar_date, price=price, volume=None)
            except PolygonDataError as exc:
                logger.warning("Polygon price failed for %s: %s — falling back to yfinance", ticker, exc)

        # ── yfinance fallback ────────────────────────────────────────────
        from_date = as_of_date - timedelta(days=14)
        try:
            hist = ticker_obj.history(
                start=from_date.isoformat(),
                end=(as_of_date + timedelta(days=1)).isoformat(),
                auto_adjust=True,
            )
        except Exception:
            hist = None

        if hist is None or (hasattr(hist, "empty") and hist.empty):
            try:
                import yfinance as _yf
                hist = _yf.download(
                    ticker,
                    start=from_date.isoformat(),
                    end=(as_of_date + timedelta(days=1)).isoformat(),
                    auto_adjust=True,
                    progress=False,
                )
            except Exception as exc:
                raise DataUnavailableError(
                    f"No historical price data available for {ticker} on or before {as_of_date.isoformat()}: {exc}"
                )

        if hist is None or (hasattr(hist, "empty") and hist.empty):
            raise DataUnavailableError(
                f"No historical price data available for {ticker} on or before {as_of_date.isoformat()}"
            )

        # Strip timezone info so comparison with a plain date works regardless
        # of whether yfinance returns a tz-aware or tz-naive DatetimeIndex.
        # Use .tz (the pandas DatetimeIndex attribute) rather than .tzinfo
        # (.tzinfo is a Python datetime attribute; on a DatetimeIndex it is
        # always None even when the index IS tz-aware, producing a wrong branch).
        try:
            if getattr(hist.index, "tz", None) is not None:
                idx = hist.index.tz_convert(None)
            else:
                idx = hist.index
        except Exception:
            idx = hist.index

        import pandas as pd
        cutoff = pd.Timestamp(as_of_date)
        mask = idx <= cutoff
        hist = hist[mask]

        if hist.empty:
            raise DataUnavailableError(
                f"No historical price data available for {ticker} on or before {as_of_date.isoformat()}"
            )

        # Handle both single-ticker (simple columns) and multi-ticker (MultiIndex) download results
        try:
            close_col = hist["Close"]
            if hasattr(close_col, "iloc"):
                price = float(close_col.iloc[-1])
            else:
                price = float(close_col)
            vol_col = hist.get("Volume")
            volume = float(vol_col.iloc[-1]) if vol_col is not None and hasattr(vol_col, "iloc") else None
        except Exception:
            price = float(hist.iloc[-1]["Close"])
            volume = None

        price_date = idx[mask][-1].date()
        return PricePoint(price_date=price_date, price=price, volume=volume)

    def get_price_as_of(self, ticker: str, as_of_date: date) -> PricePoint:
        # Polygon primary
        if _polygon.is_available():
            try:
                result = _polygon.get_close_price(ticker, as_of_date)
                if result is not None:
                    price, bar_date = result
                    return PricePoint(price_date=bar_date, price=price, volume=None)
            except PolygonDataError:
                pass
        # yfinance fallback
        ticker_obj = yf.Ticker(ticker)
        return self._build_price_point(ticker_obj, ticker, as_of_date)

    # ------------------------------------------------------------------ #
    # Profile                                                              #
    # ------------------------------------------------------------------ #

    def _build_profile(self, ticker: str, info: Dict[str, Any]) -> Profile:
        # Try Polygon for company name if available
        polygon_name = None
        if _polygon.is_available():
            try:
                p = _polygon.fetch_profile(ticker)
                polygon_name = p.get("company_name")
            except Exception:
                pass

        return Profile(
            ticker=ticker.upper(),
            company_name=str(polygon_name or info.get("longName") or info.get("shortName") or ticker.upper()),
            sector=str(info.get("sector") or "Unknown"),
            industry=str(info.get("industry") or "Unknown"),
            description=str(info.get("longBusinessSummary") or ""),
        )

    # ------------------------------------------------------------------ #
    # Financials                                                           #
    # ------------------------------------------------------------------ #

    def _build_income_statements(self, ticker_obj: yf.Ticker, as_of_date: date) -> List[StatementEntry]:
        try:
            df = ticker_obj.financials  # annual income statement
        except Exception:
            return []
        return self._df_to_statements(df, as_of_date, "income")

    def _build_balance_statements(self, ticker_obj: yf.Ticker, as_of_date: date) -> List[StatementEntry]:
        try:
            df = ticker_obj.balance_sheet
        except Exception:
            return []
        return self._df_to_statements(df, as_of_date, "balance")

    def _build_cashflow_statements(self, ticker_obj: yf.Ticker, as_of_date: date) -> List[StatementEntry]:
        try:
            df = ticker_obj.cashflow
        except Exception:
            return []
        return self._df_to_statements(df, as_of_date, "cashflow")

    def _df_to_statements(self, df: Any, as_of_date: date, kind: str) -> List[StatementEntry]:
        if df is None or df.empty:
            return []

        field_map = _get_field_map(kind)
        results: List[StatementEntry] = []

        for col in df.columns:
            try:
                # yfinance may return tz-aware Timestamps; normalize to plain date
                raw_col = col
                if hasattr(raw_col, "tz_localize") or hasattr(raw_col, "tz"):
                    try:
                        raw_col = raw_col.tz_localize(None) if raw_col.tzinfo is None else raw_col.tz_convert(None)
                    except Exception:
                        pass
                period_end = raw_col.date() if hasattr(raw_col, "date") else date.fromisoformat(str(raw_col)[:10])
            except Exception:
                continue

            # Approximate: assume filed ~45 days after fiscal year-end
            filing_date = period_end + timedelta(days=45)
            if filing_date > as_of_date:
                continue

            values: Dict[str, Any] = {}
            for yf_key, our_key in field_map.items():
                try:
                    raw = df.loc[yf_key, col] if yf_key in df.index else None
                    if raw is not None and str(raw) not in ("nan", "None", "<NA>"):
                        values[our_key] = float(raw)
                except Exception:
                    pass

            results.append(
                StatementEntry(
                    report_date=period_end,
                    filing_date=filing_date,
                    fiscal_year=str(period_end.year),
                    period="FY",
                    values=values,
                )
            )

        results.sort(key=lambda e: e.report_date, reverse=True)
        return results

    # ------------------------------------------------------------------ #
    # Dividends                                                            #
    # ------------------------------------------------------------------ #

    def _build_dividend_events(self, ticker_obj: yf.Ticker, as_of_date: date) -> List[DividendEvent]:
        try:
            divs = ticker_obj.dividends
        except Exception:
            return []
        if divs is None or divs.empty:
            return []

        events: List[DividendEvent] = []
        for ts, amount in divs.items():
            try:
                ev_date = ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])
            except Exception:
                continue
            if ev_date > as_of_date:
                continue
            events.append(
                DividendEvent(
                    event_date=ev_date,
                    dividend=float(amount),
                    adjusted_dividend=float(amount),
                    frequency=None,
                )
            )
        events.sort(key=lambda e: e.event_date, reverse=True)
        return events

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _safe_info(ticker_obj: yf.Ticker, ticker: str) -> Dict[str, Any]:
        try:
            info = ticker_obj.info or {}
            if not isinstance(info, dict):
                return {}
            return info
        except Exception:
            return {}


def _to_ts(d: date):
    import pandas as pd
    return pd.Timestamp(d)


def _get_field_map(kind: str) -> Dict[str, str]:
    if kind == "income":
        return {
            "Total Revenue": "revenue",
            "Gross Profit": "grossProfit",
            "Net Income": "netIncome",
            "Operating Income": "ebit",
            "Diluted EPS": "epsDiluted",
            "Basic EPS": "eps",
            "Diluted Average Shares": "weightedAverageShsOutDil",
            "Basic Average Shares": "weightedAverageShsOut",
            "Interest Income": "interestIncome",
            "Net Interest Income": "netInterestIncome",
        }
    if kind == "balance":
        return {
            "Total Assets": "totalAssets",
            "Current Assets": "totalCurrentAssets",
            "Current Liabilities": "totalCurrentLiabilities",
            "Long Term Debt": "longTermDebt",
            "Total Debt": "totalDebt",
            "Total Liabilities Net Minority Interest": "totalLiabilities",
            "Stockholders Equity": "totalStockholdersEquity",
            "Retained Earnings": "retainedEarnings",
            "Cash And Cash Equivalents": "cashAndCashEquivalents",
            "Other Short Term Investments": "shortTermInvestments",
            "Net PPE": "propertyPlantEquipmentNet",
        }
    if kind == "cashflow":
        return {
            "Operating Cash Flow": "operatingCashFlow",
            "Cash Flow From Continuing Operating Activities": "operatingCashFlow",
        }
    return {}
