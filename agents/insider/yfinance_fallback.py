"""Free insider activity via yfinance (no FMP API key required)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

from .models import InsiderSnapshot, InsiderTrade


def build_snapshot(
    ticker: str,
    as_of_date: date,
    *,
    lookback_days: int = 90,
) -> InsiderSnapshot:
    import yfinance as yf

    cutoff = as_of_date - timedelta(days=lookback_days)
    warnings: List[str] = [
        "Insider via yfinance — transaction detail may be less complete than FMP/SEC Form 4."
    ]
    trades: List[InsiderTrade] = []

    try:
        df = yf.Ticker(ticker).insider_transactions
    except Exception as exc:
        return InsiderSnapshot(
            ticker=ticker,
            as_of_date=as_of_date,
            trades=[],
            data_sources=[],
            warnings=[f"yfinance insider failed: {exc}"],
        )

    if df is None or df.empty:
        warnings.append(f"No yfinance insider transactions for {ticker} in lookback window")
        return InsiderSnapshot(
            ticker=ticker,
            as_of_date=as_of_date,
            trades=[],
            data_sources=[],
            warnings=warnings,
        )

    for _, row in df.iterrows():
        tx_date = _parse_row_date(row.get("Start Date"))
        if tx_date is None or tx_date > as_of_date or tx_date < cutoff:
            continue

        text = str(row.get("Text") or "")
        tx_type = _transaction_type(text, row.get("Transaction"))
        shares = _safe_float(row.get("Shares")) or 0.0
        value = abs(_safe_float(row.get("Value")) or 0.0)
        price = round(value / shares, 4) if shares else None

        trades.append(
            InsiderTrade(
                filing_date=tx_date,
                transaction_date=tx_date,
                owner_name=str(row.get("Insider") or ""),
                title=str(row.get("Position") or ""),
                transaction_type=tx_type,
                shares=shares,
                price=price,
                value=value,
            )
        )

    sources = ["yfinance:insider_transactions"] if trades else []
    if not trades:
        warnings.append(f"No yfinance insider trades for {ticker} in last {lookback_days}d")

    return InsiderSnapshot(
        ticker=ticker,
        as_of_date=as_of_date,
        trades=trades,
        data_sources=sources,
        warnings=warnings,
    )


def _parse_row_date(value: object) -> Optional[date]:
    if value is None:
        return None
    try:
        if hasattr(value, "date"):
            return value.date()
        return datetime.strptime(str(value).split(" ")[0][:10], "%Y-%m-%d").date()
    except (ValueError, TypeError, AttributeError):
        return None


def _transaction_type(text: str, raw: object) -> str:
    combined = f"{text} {raw}".lower()
    if "purchase" in combined or "buy" in combined or "acquisition" in combined:
        return "purchase"
    if "sale" in combined or "sell" in combined or "sold" in combined:
        return "sale"
    return str(raw or "other").lower()


def _safe_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
