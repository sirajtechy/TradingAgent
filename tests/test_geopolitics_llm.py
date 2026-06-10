from __future__ import annotations

from datetime import date

from agents.geopolitics.fmp_client import _match_keywords
from agents.geopolitics.models import GeoHeadline, GeopoliticsSnapshot
from agents.geopolitics.rules import evaluate_geopolitics
from agents.geopolitics.config import GeopoliticsSettings

from agents._shared.llm_summary import _content_hash, _cache_key, is_llm_enabled


# ── Keyword matching ──────────────────────────────────────────────────────


def test_match_keywords_finds_sanctions():
    matches = _match_keywords("US expands sanctions on Russia oil exports", (
        "sanctions", "tariff", "oil", "chip ban",
    ))
    assert "sanctions" in matches
    assert "oil" in matches
    assert "tariff" not in matches


def test_match_keywords_empty_on_no_match():
    matches = _match_keywords("Apple reports strong earnings", (
        "sanctions", "tariff", "war",
    ))
    assert matches == []


# ── Geopolitics rules ─────────────────────────────────────────────────────


def _make_geo_settings() -> GeopoliticsSettings:
    return GeopoliticsSettings(api_key="test")


def test_geo_evaluate_risk_when_many_headlines():
    headlines = [
        GeoHeadline(
            f"Headline {i}", date(2026, 6, 1), "Reuters", "http://example.com",
            ["sanctions", "tariff"],
        )
        for i in range(6)
    ]
    snapshot = GeopoliticsSnapshot(
        as_of_date=date(2026, 6, 1),
        headlines=headlines,
        total_scanned=50,
        data_sources=["fmp:/news/general-latest"],
    )
    result = evaluate_geopolitics(snapshot, _make_geo_settings())
    assert result["score"] < 50
    assert result["signal"] in ("bearish", "neutral")
    assert result["geo_headline_count"] == 6


def test_geo_evaluate_calm_when_no_headlines():
    snapshot = GeopoliticsSnapshot(
        as_of_date=date(2026, 6, 1),
        headlines=[],
        total_scanned=40,
        data_sources=["fmp:/news/general-latest"],
    )
    result = evaluate_geopolitics(snapshot, _make_geo_settings())
    assert result["score"] >= 55
    assert result["signal"] in ("bullish", "neutral")


def test_geo_evaluate_with_llm_negative():
    headlines = [
        GeoHeadline("Trade war escalates", date(2026, 6, 1), "FT", "http://example.com", ["trade war"]),
    ]
    snapshot = GeopoliticsSnapshot(
        as_of_date=date(2026, 6, 1),
        headlines=headlines,
        total_scanned=30,
        data_sources=["fmp:/news/general-latest"],
    )
    llm_result = {"sentiment": "negative", "bullets": ["• Trade tensions rising"], "confidence": "medium"}
    result = evaluate_geopolitics(snapshot, _make_geo_settings(), llm_result=llm_result)
    assert result["llm_sentiment"] == "negative"
    assert result["confidence"] == "high"


def test_geo_sector_exposure():
    headlines = [
        GeoHeadline("Chip ban expands", date(2026, 6, 1), "BBC", "", ["chip ban"]),
        GeoHeadline("OPEC cuts output", date(2026, 6, 1), "CNBC", "", ["opec"]),
    ]
    snapshot = GeopoliticsSnapshot(
        as_of_date=date(2026, 6, 1),
        headlines=headlines,
        total_scanned=20,
        data_sources=["fmp:/news/general-latest"],
    )
    result = evaluate_geopolitics(snapshot, _make_geo_settings())
    exposure = result["sector_exposure"]
    assert "Information Technology" in exposure
    assert "Energy" in exposure


# ── LLM helper tests ──────────────────────────────────────────────────────


def test_content_hash_deterministic():
    assert _content_hash("hello") == _content_hash("hello")
    assert _content_hash("hello") != _content_hash("world")


def test_cache_key_format():
    key = _cache_key("news", "2026-06-01", "abc123")
    assert key == "news_2026-06-01_abc123"


def test_llm_enabled_default():
    import os
    old_enabled = os.environ.get("LLM_ENABLED")
    old_provider = os.environ.get("LLM_PROVIDER")
    try:
        os.environ.pop("LLM_ENABLED", None)
        os.environ.pop("LLM_PROVIDER", None)
        assert is_llm_enabled() is False
        os.environ["LLM_PROVIDER"] = "openai"
        os.environ["LLM_ENABLED"] = "true"
        assert is_llm_enabled() is True
        os.environ["LLM_ENABLED"] = "false"
        assert is_llm_enabled() is False
    finally:
        if old_enabled is not None:
            os.environ["LLM_ENABLED"] = old_enabled
        else:
            os.environ.pop("LLM_ENABLED", None)
        if old_provider is not None:
            os.environ["LLM_PROVIDER"] = old_provider
        else:
            os.environ.pop("LLM_PROVIDER", None)
