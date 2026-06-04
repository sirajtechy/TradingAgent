"""Orchestrator mode dispatch + multi-agent envelopes (no network)."""

from __future__ import annotations

from agents.orchestrator.agent_envelope import (
    envelope_from_fundamental,
    envelope_from_phoenix,
    envelope_from_technical,
)
from agents.orchestrator.models import FusionResult
from agents.orchestrator.modes import FusionMode, fuse_by_mode


def _tech_eval(score=72.0, band="good"):
    return {
        "experimental_score": {
            "available": True,
            "score": score,
            "band": band,
            "confidence": "medium",
            "subscores": {},
        },
        "frameworks": {},
        "key_indicators": {},
        "as_of_price": {"price": 100.0, "price_date": "2025-01-01"},
    }


def _fund_eval(score=75.0, band="good"):
    return {
        "experimental_score": {
            "available": True,
            "score": score,
            "band": band,
            "confidence": "high",
            "subscores": {},
        },
        "frameworks": {},
        "data_quality": {"coverage_ratio": 0.95},
        "as_of_price": {"price": 100.0, "price_date": "2025-01-01"},
        "warnings": [],
    }


def _px_eval(signal="BUY", score=80.0):
    return {
        "signal": signal,
        "score": score,
        "hard_filter_passed": True,
        "score_breakdown": {"volume": 10.0},
        "pattern": {},
        "stage": {},
        "warnings": [],
    }


def test_fuse_by_mode_tech_fund_matches_fuse_signals():
    r = fuse_by_mode(
        FusionMode.TECH_FUND,
        tech_result=_tech_eval(),
        tech_error=None,
        fund_result=_fund_eval(),
        fund_error=None,
    )
    assert isinstance(r, FusionResult)
    assert r.final_signal == "bullish"
    assert r.conflict_detected is False


def test_fuse_by_mode_phoenix_fund():
    r = fuse_by_mode(
        FusionMode.PHOENIX_FUND,
        phoenix_result=_px_eval(),
        phoenix_error=None,
        fund_result=_fund_eval(),
        fund_error=None,
    )
    assert isinstance(r, FusionResult)
    assert r.final_signal == "bullish"


def test_envelope_technical_keys():
    e = envelope_from_technical(_tech_eval(), as_of_date="2025-06-01")
    assert e["agent_id"] == "technical"
    assert e["as_of_date"] == "2025-06-01"
    assert e["signal"] == "bullish"
    assert "extras" in e


def test_envelope_fundamental_keys():
    e = envelope_from_fundamental(_fund_eval())
    assert e["agent_id"] == "fundamental"
    assert e["signal"] == "bullish"
    assert e["abstain"] is False


def test_envelope_phoenix_buy_and_watch():
    buy = envelope_from_phoenix(_px_eval(signal="BUY", score=80.0))
    assert buy["abstain"] is False

    watch = envelope_from_phoenix(_px_eval(signal="WATCH", score=55.0))
    assert watch["abstain"] is True
