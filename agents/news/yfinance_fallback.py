"""Free news headlines via yfinance (no FMP API key required)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List

from .models import Headline, NewsSnapshot


def build_snapshot(ticker: str, as_of_date: date, lookback_days: int = 30) -> NewsSnapshot:
    import yfinance as yf

    cutoff = as_of_date - timedelta(days=lookback_days)
    headlines: List[Headline] = []
    warnings: List[str] = [
        "News via yfinance — analyst grades and price targets unavailable without FMP."
    ]

    try:
        raw = yf.Ticker(ticker).news or []
    except Exception as exc:
        return NewsSnapshot(
            ticker=ticker,
            as_of_date=as_of_date,
            headlines=[],
            data_sources=[],
            warnings=[f"yfinance news failed: {exc}"],
        )

    for item in raw[:30]:
        content = item.get("content") if isinstance(item.get("content"), dict) else item
        title = str((content or {}).get("title") or item.get("title") or "")
        if not title:
            continue
        pub = _parse_pub_date((content or {}).get("pubDate") or item.get("providerPublishTime"))
        if pub is None or pub > as_of_date or pub < cutoff:
            continue
        provider = (content or {}).get("provider") or {}
        source = str(provider.get("displayName") or item.get("publisher") or "yfinance")
        url = str(
            (content or {}).get("canonicalUrl")
            or (content or {}).get("clickThroughUrl")
            or item.get("link")
            or item.get("url")
            or ""
        )
        headlines.append(Headline(
            title=title,
            published_date=pub,
            source=source,
            url=url,
        ))

    sources = ["yfinance:news"] if headlines else []
    if not headlines:
        warnings.append(f"No yfinance headlines for {ticker} in lookback window")

    return NewsSnapshot(
        ticker=ticker,
        as_of_date=as_of_date,
        headlines=headlines,
        data_sources=sources,
        warnings=warnings,
    )


def _parse_pub_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value)).date()
        except (TypeError, ValueError, OSError):
            return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None
