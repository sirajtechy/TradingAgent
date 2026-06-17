"""Free geopolitics scan via yfinance market news keyword matching."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, List, Sequence, Tuple

from .config import GeopoliticsSettings
from .models import GeoHeadline, GeopoliticsSnapshot

_DEFAULT_SCAN_TICKERS: Tuple[str, ...] = ("SPY", "QQQ", "XLE", "GLD", "UUP")


def build_snapshot(
    as_of_date: date,
    *,
    settings: GeopoliticsSettings | None = None,
    scan_tickers: Sequence[str] = _DEFAULT_SCAN_TICKERS,
) -> GeopoliticsSnapshot:
    import yfinance as yf

    cfg = settings or _default_settings()
    cutoff = as_of_date - timedelta(days=cfg.lookback_days)
    warnings: List[str] = [
        "Geopolitics via yfinance market news scan — FMP general/forex feeds not used."
    ]

    all_headlines: List[GeoHeadline] = []
    total_scanned = 0

    for ticker in scan_tickers:
        try:
            raw_items = yf.Ticker(ticker).news or []
        except Exception:
            continue

        for item in raw_items[: cfg.news_limit]:
            title, pub, source, url = _normalize_news_item(item)
            if not title:
                continue
            total_scanned += 1
            if pub is None or pub > as_of_date or pub < cutoff:
                continue
            matched = _match_keywords(title, cfg.geo_keywords)
            all_headlines.append(
                GeoHeadline(
                    title=title,
                    published_date=pub,
                    source=source or f"yfinance:{ticker}",
                    url=url,
                    matched_keywords=matched,
                )
            )

    geo_filtered = [h for h in all_headlines if h.matched_keywords]
    # Include top market headlines for context even when keywords do not match
    context_headlines = sorted(
        [h for h in all_headlines if h.title and not h.matched_keywords],
        key=lambda h: h.published_date,
        reverse=True,
    )[:5]
    display_headlines = geo_filtered if geo_filtered else context_headlines

    sources = ["yfinance:market_news_scan"] if total_scanned else []
    if not geo_filtered and context_headlines:
        warnings.append("No geo keyword matches — showing general market headlines for context")
    if not display_headlines:
        warnings.append("No geopolitical headlines matched in yfinance scan window")

    return GeopoliticsSnapshot(
        as_of_date=as_of_date,
        headlines=display_headlines[:10],
        total_scanned=total_scanned,
        data_sources=sources,
        warnings=warnings,
    )


def _default_settings() -> GeopoliticsSettings:
    return GeopoliticsSettings(api_key="unused")


def _normalize_news_item(item: dict) -> Tuple[str, date | None, str, str]:
    content = item.get("content") if isinstance(item.get("content"), dict) else item
    title = str((content or {}).get("title") or item.get("title") or "")
    pub = _parse_pub_date((content or {}).get("pubDate") or item.get("providerPublishTime"))
    provider = (content or {}).get("provider") or {}
    source = str(provider.get("displayName") or provider.get("sourceId") or item.get("publisher") or "yfinance")
    url = str(
        (content or {}).get("canonicalUrl")
        or (content or {}).get("clickThroughUrl")
        or item.get("link")
        or item.get("url")
        or ""
    )
    return title, pub, source, url


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


def _match_keywords(text: str, keywords: Iterable[str]) -> List[str]:
    lower = text.lower()
    return [kw for kw in keywords if kw in lower]
