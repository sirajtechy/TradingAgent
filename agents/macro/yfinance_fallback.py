"""Free macro proxy data via yfinance (no FRED API key required)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple


def build_snapshot(as_of_date: date) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """
    Approximate macro metrics from market proxies:
      ^TNX  — 10-year Treasury yield
      ^IRX  — 13-week T-bill (short-rate proxy)
      spread = T10Y - short (yield curve proxy)
    """
    import yfinance as yf

    sources: List[str] = []
    warnings: List[str] = [
        "Macro via yfinance proxy (^TNX, ^IRX) — FRED not used. CPI/unemployment unavailable."
    ]
    metrics: Dict[str, Any] = {"as_of_date": as_of_date.isoformat()}

    start = as_of_date - timedelta(days=90)
    end = as_of_date + timedelta(days=1)

    def _last_close(symbol: str) -> Tuple[Optional[float], Optional[date]]:
        try:
            hist = yf.Ticker(symbol).history(start=start.isoformat(), end=end.isoformat())
            if hist is None or hist.empty:
                return None, None
            hist = hist[hist.index.date <= as_of_date]
            if hist.empty:
                return None, None
            row = hist.iloc[-1]
            return float(row["Close"]), hist.index[-1].date()
        except Exception:
            return None, None

    t10, t10_date = _last_close("^TNX")
    short, short_date = _last_close("^IRX")

    if t10 is not None:
        metrics["fed_funds"] = round(t10 / 10.0, 3)  # rough long-rate proxy label
        metrics["fed_funds_date"] = t10_date.isoformat() if t10_date else None
        sources.append("yfinance:^TNX")

    if t10 is not None and short is not None:
        spread = round(t10 - short, 2)
        metrics["yield_spread"] = spread
        metrics["yield_spread_date"] = as_of_date.isoformat()
        sources.append("yfinance:yield_spread_proxy")

    if t10 is not None and len(sources) >= 1:
        rows = yf.Ticker("^TNX").history(start=(as_of_date - timedelta(days=60)).isoformat(), end=end.isoformat())
        if rows is not None and len(rows) >= 2:
            rows = rows[rows.index.date <= as_of_date]
            if len(rows) >= 2:
                prior = float(rows.iloc[-2]["Close"])
                metrics["prior_fed_funds"] = round(prior / 10.0, 3)

    if not sources:
        warnings.append("yfinance macro proxy unavailable")

    return metrics, sources, warnings
