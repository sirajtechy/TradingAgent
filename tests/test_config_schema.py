"""Tests for core.config_schema — FEAT-001."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config_schema import (
    KNOWN_ENV_KEYS,
    parse_env_file,
    validate_config,
    validate_env_file,
)


def test_valid_data_source_values():
    env = {
        "MACRO_DATA_SOURCE": "auto",
        "NEWS_DATA_SOURCE": "yfinance",
        "INSIDER_DATA_SOURCE": "fmp",
        "GEOPOLITICS_DATA_SOURCE": "auto",
        "MARKET_DATA_SOURCE": "polygon",
        "LLM_PROVIDER": "deterministic",
    }
    report = validate_config(env)
    assert report.ok is True
    assert not report.errors
    assert report.normalized["MACRO_DATA_SOURCE"] == "auto"
    assert report.normalized["NEWS_DATA_SOURCE"] == "yfinance"


def test_invalid_macro_data_source():
    report = validate_config({"MACRO_DATA_SOURCE": "polygon"})
    assert report.ok is False
    assert any("MACRO_DATA_SOURCE" in e for e in report.errors)
    assert "auto" in report.errors[0]


def test_invalid_news_data_source():
    report = validate_config({"NEWS_DATA_SOURCE": "fred"})
    assert report.ok is False


def test_unknown_key_error():
    report = validate_config({"TOTALLY_UNKNOWN_FLAG": "1"})
    assert report.ok is False
    assert any("Unknown env key" in e for e in report.errors)


def test_known_api_keys_no_error():
    report = validate_config({
        "POLYGON_API_KEY": "pk-test",
        "FMP_API_KEY": "abc",
        "FRED_API_KEY": "xyz",
    })
    assert report.ok is True


def test_llm_provider_invalid():
    report = validate_config({"LLM_PROVIDER": "anthropic"})
    assert report.ok is False


def test_llm_provider_valid():
    report = validate_config({"LLM_PROVIDER": "openai"})
    assert report.ok is True


def test_parse_env_file(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# comment\nMACRO_DATA_SOURCE=auto\nUNKNOWN_BAD=1\nPOLYGON_API_KEY=secret\n",
        encoding="utf-8",
    )
    parsed = parse_env_file(env_path)
    assert parsed["MACRO_DATA_SOURCE"] == "auto"
    assert parsed["POLYGON_API_KEY"] == "secret"
    assert "UNKNOWN_BAD" in parsed

    report = validate_env_file(env_path)
    assert report.ok is False
    assert any("UNKNOWN_BAD" in e for e in report.errors)


def test_env_example_keys_are_known():
    example = Path(__file__).resolve().parent.parent / ".env.example"
    if not example.is_file():
        pytest.skip(".env.example missing")
    parsed = parse_env_file(example)
    for key in parsed:
        assert key in KNOWN_ENV_KEYS, f".env.example key {key} not in KNOWN_ENV_KEYS"


def test_placeholder_api_key_warning():
    report = validate_config({"POLYGON_API_KEY": "your_polygon_api_key_here"})
    assert report.ok is True
    assert any("POLYGON_API_KEY" in w for w in report.warnings)
