"""Free market summary data via yfinance (no Polygon API key required)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional, Tuple

import pandas as pd

from .config import MarketSummarySettings
from .models import MarketDataSnapshot, TickerPerformance


def build_snapshot(
    as_of_date: date,
    settings: Optional[MarketSummarySettings] = None,
) -> MarketDataSnapshot:
    import yfinance as yf

    cfg = settings or MarketSummarySettings()
    sources: List[str] = ["yfinance:history"]
    warnings: List[str] = [
        "Market summary via yfinance — Polygon/Massive not used. VIX from ^VIX."
    ]

    start = as_of_date - timedelta(days=cfg.lookback_days + 10)
    end = as_of_date + timedelta(days=1)

    vix_close, vix_warn = _fetch_close(yf, "^VIX", as_of_date, start, end, lookback=10)
    warnings.extend(vix_warn)
    vix_regime = _vix_regime(vix_close, cfg)

    spy_perf, spy_warn = _fetch_performance(
        yf,
        cfg.benchmark_ticker,
        "S&P 500",
        as_of_date,
        start,
        end,
        cfg,
        vs_spy_20d=None,
    )
    warnings.extend(spy_warn)

    sectors: List[TickerPerformance] = []
    spy_20d = spy_perf.change_20d_pct if spy_perf else None
    for ticker in cfg.sector_etfs:
        label = cfg.sector_labels.get(ticker, ticker)
        perf, sector_warn = _fetch_performance(
            yf,
            ticker,
            label,
            as_of_date,
            start,
            end,
            cfg,
            vs_spy_20d=spy_20d,
        )
        warnings.extend(sector_warn)
        if perf is not None:
            sectors.append(perf)

    if vix_close is not None:
        sources.append("yfinance:^VIX")
    if spy_perf is not None:
        sources.append(f"yfinance:{cfg.benchmark_ticker}")

    return MarketDataSnapshot(
        as_of_date=as_of_date,
        vix=vix_close,
        vix_regime=vix_regime,
        spy=spy_perf,
        sectors=sectors,
        data_sources=sources,
        warnings=warnings,
    )


def _fetch_close(
    yf_module,
    symbol: str,
    as_of_date: date,
    start: date,
    end: date,
    *,
    lookback: int,
) -> Tuple[Optional[float], List[str]]:
    warnings: List[str] = []
    df = _history(yf_module, symbol, start, end, as_of_date)
    if df is None or df.empty:
        warnings.append(f"No yfinance bars for {symbol}")
        return None, warnings
    return round(float(df["Close"].iloc[-1]), 2), warnings


def _fetch_performance(
    yf_module,
    ticker: str,
    label: str,
    as_of_date: date,
    start: date,
    end: date,
    settings: MarketSummarySettings,
    *,
    vs_spy_20d: Optional[float],
) -> Tuple[Optional[TickerPerformance], List[str]]:
    warnings: List[str] = []
    df = _history(yf_module, ticker, start, end, as_of_date)
    if df is None or df.empty:
        warnings.append(f"No yfinance bars for {ticker}")
        return None, warnings

    close = round(float(df["Close"].iloc[-1]), 2)
    change_5d = _pct_change_over_bars(df, settings.short_window)
    change_20d = _pct_change_over_bars(df, settings.long_window)
    vs_spy = None
    if change_20d is not None and vs_spy_20d is not None:
        vs_spy = round(change_20d - vs_spy_20d, 2)

    return (
        TickerPerformance(
            ticker=ticker,
            label=label,
            close=close,
            change_5d_pct=change_5d,
            change_20d_pct=change_20d,
            vs_spy_20d_pct=vs_spy,
        ),
        warnings,
    )


def _history(yf_module, symbol: str, start: date, end: date, as_of_date: date) -> Optional[pd.DataFrame]:
    try:
        df = yf_module.Ticker(symbol).history(start=start.isoformat(), end=end.isoformat())
        if df is None or df.empty:
            return None
        df = df[df.index.date <= as_of_date]
        return df if not df.empty else None
    except Exception:
        return None


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
