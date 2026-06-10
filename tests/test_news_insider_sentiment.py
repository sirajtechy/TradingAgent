from __future__ import annotations

from datetime import date

from agents.news.fmp_client import _parse_datetime_to_date
from agents.news.models import AnalystGrade, Headline, NewsSnapshot, PriceTarget
from agents.news.rules import evaluate_news
from agents.news.config import NewsSettings

from agents.insider.fmp_client import _parse_date as insider_parse_date
from agents.insider.models import InsiderSnapshot, InsiderTrade
from agents.insider.rules import evaluate_insider

from agents.sentiment.models import SentimentSnapshot
from agents.sentiment.rules import evaluate_sentiment


# ── News rules tests ──────────────────────────────────────────────────────


def _make_news_settings() -> NewsSettings:
    return NewsSettings(api_key="test")


def test_news_evaluate_upgrades_bullish():
    grades = [
        AnalystGrade("Goldman Sachs", "Buy", "Hold", "upgrade", date(2026, 5, 20)),
        AnalystGrade("Morgan Stanley", "Overweight", "Equal-Weight", "upgrade", date(2026, 5, 22)),
    ]
    snapshot = NewsSnapshot(
        ticker="AAPL",
        as_of_date=date(2026, 6, 1),
        headlines=[Headline("Apple rallies", date(2026, 5, 25), "Reuters", "http://example.com")],
        grades=grades,
        data_sources=["fmp:/grades"],
    )
    result = evaluate_news(snapshot, _make_news_settings(), current_close=190.0)
    assert result["signal"] == "bullish"
    assert result["score"] >= 58
    assert len(result["priority_actions"]) == 2


def test_news_evaluate_no_data_abstains():
    snapshot = NewsSnapshot(
        ticker="XYZ",
        as_of_date=date(2026, 6, 1),
        headlines=[],
        grades=[],
        data_sources=[],
        warnings=["No FMP headlines for XYZ"],
    )
    result = evaluate_news(snapshot, _make_news_settings())
    assert result["abstain"] is True
    assert result["signal"] == "neutral"


def test_news_date_parsing():
    assert _parse_datetime_to_date("2026-05-30 14:30:00") == date(2026, 5, 30)
    assert _parse_datetime_to_date(None) is None
    assert _parse_datetime_to_date("") is None


# ── Insider rules tests ──────────────────────────────────────────────────


def test_insider_net_buys_bullish():
    trades = [
        InsiderTrade(date(2026, 5, 20), date(2026, 5, 19), "Jane CEO", "CEO", "purchase", 10000, 50.0, 500000),
        InsiderTrade(date(2026, 5, 22), date(2026, 5, 21), "Bob CFO", "CFO", "purchase", 5000, 50.0, 250000),
    ]
    snapshot = InsiderSnapshot(
        ticker="AAPL",
        as_of_date=date(2026, 6, 1),
        trades=trades,
        data_sources=["fmp:/insider-trading"],
    )
    result = evaluate_insider(snapshot)
    assert result["signal"] == "bullish"
    assert result["metrics"]["buy_count"] == 2
    assert result["metrics"]["sell_count"] == 0


def test_insider_net_sells_bearish():
    trades = [
        InsiderTrade(date(2026, 5, 20), date(2026, 5, 19), "Exec A", "Director", "sale", 20000, 100.0, 2000000),
        InsiderTrade(date(2026, 5, 22), date(2026, 5, 21), "Exec B", "VP", "sale", 15000, 100.0, 1500000),
    ]
    snapshot = InsiderSnapshot(
        ticker="AAPL",
        as_of_date=date(2026, 6, 1),
        trades=trades,
        data_sources=["fmp:/insider-trading"],
    )
    result = evaluate_insider(snapshot)
    assert result["signal"] == "bearish"
    assert result["metrics"]["net_value"] < 0


def test_insider_no_trades_abstains():
    snapshot = InsiderSnapshot(
        ticker="XYZ",
        as_of_date=date(2026, 6, 1),
        trades=[],
        warnings=["No FMP insider trades for XYZ in the last 90d"],
    )
    result = evaluate_insider(snapshot)
    assert result["abstain"] is True


def test_insider_date_parsing():
    assert insider_parse_date("2026-05-30") == date(2026, 5, 30)
    assert insider_parse_date(None) is None


# ── Sentiment rules tests ─────────────────────────────────────────────────


def test_sentiment_bullish_when_news_and_insider_bullish():
    snapshot = SentimentSnapshot(
        ticker="AAPL",
        as_of_date=date(2026, 6, 1),
        news_eval={"score": 72, "subscores": {"analyst_grades": 75}, "data_sources": ["fmp:/grades"]},
        insider_eval={"score": 68, "data_sources": ["fmp:/insider-trading"]},
        macro_eval={"score": 60, "data_sources": ["fred:DFF"]},
        data_sources=["news_agent", "insider_agent", "macro_agent"],
    )
    result = evaluate_sentiment(snapshot)
    assert result["signal"] == "bullish"
    assert result["score"] >= 58
    assert result["dimensions"]["news"] == "positive"
    assert result["dimensions"]["insider"] == "positive"


def test_sentiment_bearish_when_all_negative():
    snapshot = SentimentSnapshot(
        ticker="XYZ",
        as_of_date=date(2026, 6, 1),
        news_eval={"score": 30, "subscores": {"analyst_grades": 25}, "data_sources": []},
        insider_eval={"score": 28, "data_sources": []},
        macro_eval={"score": 35, "data_sources": []},
        data_sources=[],
    )
    result = evaluate_sentiment(snapshot)
    assert result["signal"] == "bearish"
    assert result["sentiment"] == "negative"


def test_sentiment_no_data_abstains():
    snapshot = SentimentSnapshot(
        ticker="ZZZ",
        as_of_date=date(2026, 6, 1),
        warnings=["All agents unavailable"],
    )
    result = evaluate_sentiment(snapshot)
    assert result["abstain"] is True
    assert result["score"] == 50.0
