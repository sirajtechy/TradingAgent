"""Optional Finnhub company news (free tier: 60 calls/min)."""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import List

import requests

from .models import Headline, NewsSnapshot


def is_available() -> bool:
    return bool(os.getenv("FINNHUB_API_KEY", "").strip())


def build_snapshot(ticker: str, as_of_date: date, lookback_days: int = 30) -> NewsSnapshot:
    api_key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not api_key:
        return NewsSnapshot(
            ticker=ticker,
            as_of_date=as_of_date,
            headlines=[],
            data_sources=[],
            warnings=["FINNHUB_API_KEY not set"],
        )

    start = (as_of_date - timedelta(days=lookback_days)).isoformat()
    end = as_of_date.isoformat()
    url = "https://finnhub.io/api/v1/company-news"
    resp = requests.get(
        url,
        params={"symbol": ticker.upper(), "from": start, "to": end, "token": api_key},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json() or []

    headlines: List[Headline] = []
    for item in data[:30]:
        title = str(item.get("headline") or "").strip()
        if not title:
            continue
        ts = item.get("datetime")
        pub = as_of_date
        if isinstance(ts, (int, float)):
            from datetime import datetime

            pub = datetime.fromtimestamp(int(ts)).date()
        if pub > as_of_date or pub < (as_of_date - timedelta(days=lookback_days)):
            continue
        headlines.append(
            Headline(
                title=title,
                published_date=pub,
                source=str(item.get("source") or "finnhub"),
                url=str(item.get("url") or ""),
            )
        )

    return NewsSnapshot(
        ticker=ticker,
        as_of_date=as_of_date,
        headlines=headlines[:10],
        data_sources=["finnhub:company-news"] if headlines else [],
        warnings=[] if headlines else [f"No Finnhub headlines for {ticker}"],
    )
