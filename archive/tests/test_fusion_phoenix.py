"""Phoenix + FA fusion uses phoenix_fund_weights (default 90/10)."""

from __future__ import annotations

import pytest

from agents.orchestrator.fusion_phoenix import fuse_signals_phoenix


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


def test_phoenix_fund_agreement_bullish_weights_and_score():
    phoenix_result = {
        "signal": "BUY",
        "score": 80.0,
        "hard_filter_passed": True,
        "score_breakdown": {},
        "pattern": {},
        "stage": {},
        "warnings": [],
    }
    r = fuse_signals_phoenix(
        phoenix_result=phoenix_result,
        phoenix_error=None,
        fund_result=_fund_eval(score=75.0, band="good"),
        fund_error=None,
    )
    assert r.weights_applied == {"tech": 0.90, "fund": 0.10}
    assert r.final_signal == "bullish"
    expected = 0.90 * 80.0 + 0.10 * 75.0
    assert r.orchestrator_score == pytest.approx(expected, abs=0.05)


def test_phoenix_fund_single_agent_weights():
    px = {"signal": "BUY", "score": 70.0, "hard_filter_passed": True}
    r_fa_fail = fuse_signals_phoenix(
        phoenix_result=px,
        phoenix_error=None,
        fund_result=None,
        fund_error="no data",
    )
    assert r_fa_fail.weights_applied == {"tech": 1.0, "fund": 0.0}

    r_px_fail = fuse_signals_phoenix(
        phoenix_result=None,
        phoenix_error="down",
        fund_result=_fund_eval(),
        fund_error=None,
    )
    assert r_px_fail.weights_applied == {"tech": 0.0, "fund": 1.0}
