"""
test_fusion.py — Unit tests for the CWAF fusion engine.

Tests cover:
  - agent_confidence helper
  - Signal extraction from both agents
  - All 9 matrix cases (agreement, single-agent, conflict)
  - Anti-bullish guardrails
  - Error-handling paths
"""

import pytest

from orchestrator_agent.config import OrchestratorSettings
from orchestrator_agent.fusion import (
    agent_confidence,
    fuse_signals,
    _extract_tech_output,
    _extract_fund_output,
)
from orchestrator_agent.models import BAND_TO_SIGNAL


# ---------------------------------------------------------------------------
# Fixtures — synthetic evaluation dicts
# ---------------------------------------------------------------------------

def _tech_eval(score=70.0, band="good", confidence="medium",
               subscores=None):
    """Build a minimal technical evaluation dict."""
    return {
        "experimental_score": {
            "available": True,
            "score": score,
            "band": band,
            "confidence": confidence,
            "subscores": subscores or {},
        },
        "frameworks": {},
        "key_indicators": {},
        "as_of_price": {"price": 100.0, "price_date": "2025-01-01"},
    }


def _fund_eval(score=75.0, band="good", confidence="medium",
               subscores=None,
               coverage_ratio=0.9):
    """Build a minimal fundamental evaluation dict."""
    return {
        "experimental_score": {
            "available": True,
            "score": score,
            "band": band,
            "confidence": confidence,
            "subscores": subscores or {},
        },
        "frameworks": {},
        "data_quality": {"coverage_ratio": coverage_ratio, "warnings_count": 0},
        "as_of_price": {"price": 100.0, "price_date": "2025-01-01"},
    }


# ---------------------------------------------------------------------------
# agent_confidence
# ---------------------------------------------------------------------------

class TestAgentConfidence:
    """Tests for the boundary-distance confidence function."""

    def test_at_boundary_returns_zero(self):
        thresholds = [35.0, 50.0, 60.0, 75.0]
        assert agent_confidence(50.0, thresholds) == 0.0

    def test_far_from_boundary(self):
        thresholds = [35.0, 50.0, 60.0, 75.0]
        # score=55, nearest boundary=50, distance=5, 5/25=0.2
        assert agent_confidence(55.0, thresholds) == pytest.approx(0.2)

    def test_at_extreme_high(self):
        thresholds = [35.0, 50.0, 60.0, 75.0]
        # score=100, nearest boundary=75, distance=25, 25/25=1.0
        assert agent_confidence(100.0, thresholds) == pytest.approx(1.0)

    def test_capped_at_one(self):
        thresholds = [35.0, 50.0, 60.0, 75.0]
        # score=110, nearest=75, distance=35, 35/25=1.4 → capped at 1.0
        assert agent_confidence(110.0, thresholds) == 1.0

    def test_fund_thresholds(self):
        thresholds = [40.0, 62.0, 70.0, 85.0]
        # score=51, nearest=40, distance=11, 11/25=0.44
        assert agent_confidence(51.0, thresholds) == pytest.approx(0.44)

    def test_zero_score(self):
        thresholds = [35.0, 50.0, 60.0, 75.0]
        # distance=35, 35/25=1.4 → capped at 1.0
        assert agent_confidence(0.0, thresholds) == 1.0


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

class TestExtractTechOutput:

    def test_normal_extraction(self):
        ev = _tech_eval(72.0, "good", "high")
        cfg = OrchestratorSettings()
        out = _extract_tech_output(ev, cfg.tech_thresholds)
        assert out.signal == "bullish"
        assert out.score == 72.0
        assert out.band == "good"

    def test_unavailable_score(self):
        ev = {"experimental_score": {"available": False}}
        cfg = OrchestratorSettings()
        out = _extract_tech_output(ev, cfg.tech_thresholds)
        assert out.signal == "neutral"
        assert out.score == 50.0

    def test_missing_score_key(self):
        ev = {}
        cfg = OrchestratorSettings()
        out = _extract_tech_output(ev, cfg.tech_thresholds)
        assert out.signal == "neutral"


class TestExtractFundOutput:

    def test_normal_extraction(self):
        ev = _fund_eval(75.0, "good", "high")
        cfg = OrchestratorSettings()
        out = _extract_fund_output(ev, cfg.fund_thresholds)
        assert out.signal == "bullish"
        assert out.score == 75.0
        assert out.data_quality == "good"

    def test_poor_data_quality(self):
        ev = _fund_eval(75.0, "good", coverage_ratio=0.3)
        cfg = OrchestratorSettings()
        out = _extract_fund_output(ev, cfg.fund_thresholds)
        assert out.data_quality == "poor"

    def test_fair_data_quality(self):
        ev = _fund_eval(75.0, "good", coverage_ratio=0.6)
        cfg = OrchestratorSettings()
        out = _extract_fund_output(ev, cfg.fund_thresholds)
        assert out.data_quality == "fair"


# ---------------------------------------------------------------------------
# Error handling (Layer 0)
# ---------------------------------------------------------------------------

class TestErrorHandling:

    def test_both_errors(self):
        r = fuse_signals(
            tech_error="Network error",
            fund_error="API timeout",
        )
        assert r.final_signal == "neutral"
        assert r.final_confidence == 0.0
        assert r.note == "Both agents failed"

    def test_tech_error_only(self):
        r = fuse_signals(
            tech_error="boom",
            fund_result=_fund_eval(75.0, "good", "high"),
        )
        assert r.final_signal == "bullish"
        assert r.tech_error == "boom"
        assert r.weights_applied == {"tech": 0.0, "fund": 1.0}

    def test_fund_error_only(self):
        r = fuse_signals(
            tech_result=_tech_eval(72.0, "good"),
            fund_error="timeout",
        )
        assert r.final_signal == "bullish"
        assert r.fund_error == "timeout"
        assert r.weights_applied == {"tech": 1.0, "fund": 0.0}


# ---------------------------------------------------------------------------
# Agreement cases (Layer 1)
# ---------------------------------------------------------------------------

class TestAgreement:

    def test_agreement_bullish(self):
        r = fuse_signals(
            tech_result=_tech_eval(70.0, "good"),
            fund_result=_fund_eval(75.0, "good"),
        )
        assert r.final_signal == "bullish"
        assert r.conflict_detected is False
        assert r.weights_applied == {"tech": 0.45, "fund": 0.55}
        expected_score = 0.45 * 70.0 + 0.55 * 75.0
        assert r.orchestrator_score == pytest.approx(expected_score, abs=0.1)

    def test_agreement_bearish(self):
        r = fuse_signals(
            tech_result=_tech_eval(25.0, "weak"),
            fund_result=_fund_eval(30.0, "weak"),
        )
        assert r.final_signal == "bearish"
        assert r.conflict_detected is False
        expected_score = 0.45 * 25.0 + 0.55 * 30.0
        assert r.orchestrator_score == pytest.approx(expected_score, abs=0.1)

    def test_agreement_bearish_bonus_higher_than_bullish(self):
        """Bearish agreement bonus (1.20) > bullish agreement bonus (1.15)."""
        cfg = OrchestratorSettings()
        assert cfg.bearish_agreement_bonus > cfg.bullish_agreement_bonus

    def test_agreement_neutral(self):
        r = fuse_signals(
            tech_result=_tech_eval(45.0, "mixed"),
            fund_result=_fund_eval(50.0, "mixed"),
        )
        assert r.final_signal == "neutral"
        assert r.final_confidence == 0.70
        assert r.weights_applied == {"tech": 0.50, "fund": 0.50}


# ---------------------------------------------------------------------------
# Single-agent directional (Layer 2)
# ---------------------------------------------------------------------------

class TestSingleAgent:

    def test_tech_only_bullish(self):
        """Tech=bullish, Fund=neutral → orchestrator follows tech."""
        r = fuse_signals(
            tech_result=_tech_eval(70.0, "good"),
            fund_result=_fund_eval(50.0, "mixed"),
        )
        assert r.final_signal == "bullish"
        assert r.weights_applied == {"tech": 0.85, "fund": 0.15}
        expected_score = 0.85 * 70.0 + 0.15 * 50.0
        assert r.orchestrator_score == pytest.approx(expected_score, abs=0.1)

    def test_tech_only_bearish(self):
        """Tech=bearish, Fund=neutral → orchestrator follows tech."""
        r = fuse_signals(
            tech_result=_tech_eval(25.0, "weak"),
            fund_result=_fund_eval(50.0, "mixed"),
        )
        assert r.final_signal == "bearish"
        assert r.weights_applied == {"tech": 0.85, "fund": 0.15}

    def test_fund_only_bullish(self):
        """Tech=neutral, Fund=bullish → orchestrator follows fund."""
        r = fuse_signals(
            tech_result=_tech_eval(45.0, "mixed"),
            fund_result=_fund_eval(75.0, "good"),
        )
        assert r.final_signal == "bullish"
        assert r.weights_applied == {"tech": 0.15, "fund": 0.85}

    def test_fund_only_bearish(self):
        """Tech=neutral, Fund=bearish → orchestrator follows fund."""
        r = fuse_signals(
            tech_result=_tech_eval(45.0, "mixed"),
            fund_result=_fund_eval(30.0, "weak"),
        )
        assert r.final_signal == "bearish"
        assert r.weights_applied == {"tech": 0.15, "fund": 0.85}

    def test_tech_only_bullish_poor_data_quality_discount(self):
        """Poor fund data quality adds extra discount to tech-only confidence."""
        r_good = fuse_signals(
            tech_result=_tech_eval(70.0, "good"),
            fund_result=_fund_eval(50.0, "mixed", coverage_ratio=0.9),
        )
        r_poor = fuse_signals(
            tech_result=_tech_eval(70.0, "good"),
            fund_result=_fund_eval(50.0, "mixed", coverage_ratio=0.3),
        )
        assert r_poor.final_confidence < r_good.final_confidence


# ---------------------------------------------------------------------------
# Band-to-signal mapping
# ---------------------------------------------------------------------------

class TestBandToSignal:

    @pytest.mark.parametrize("band,expected", [
        ("strong", "bullish"),
        ("good", "bullish"),
        ("mixed_positive", "bullish"),
        ("mixed", "neutral"),
        ("weak", "bearish"),
    ])
    def test_mapping(self, band, expected):
        assert BAND_TO_SIGNAL[band] == expected


# ---------------------------------------------------------------------------
# Anti-bullish guardrails
# ---------------------------------------------------------------------------

class TestGuardrails:

    def test_bullish_threshold_guardrail(self):
        """Even if both agents are bullish, a combined score < 62 → neutral."""
        # Use scores that when combined produce < 62
        r = fuse_signals(
            tech_result=_tech_eval(53.0, "mixed_positive"),
            fund_result=_fund_eval(63.0, "mixed_positive"),
        )
        # 0.45*53 + 0.55*63 = 23.85 + 34.65 = 58.5 → < 62 → neutral
        assert r.orchestrator_score == pytest.approx(58.5, abs=0.1)
        assert r.final_signal == "neutral"

    def test_bearish_threshold_guardrail(self):
        """Both agents bearish, combined score < 38 → confirmed bearish."""
        r = fuse_signals(
            tech_result=_tech_eval(20.0, "weak"),
            fund_result=_fund_eval(25.0, "weak"),
        )
        # 0.45*20 + 0.55*25 = 9 + 13.75 = 22.75 → < 38 → bearish
        assert r.orchestrator_score == pytest.approx(22.75, abs=0.1)
        assert r.final_signal == "bearish"

    def test_bullish_confirmation_mixed_positive_vs_bearish(self):
        """Tech=mixed_positive (weak bullish) + Fund=bearish → conflict → may neutralise."""
        r = fuse_signals(
            tech_result=_tech_eval(55.0, "mixed_positive"),
            fund_result=_fund_eval(30.0, "weak"),  # bearish
        )
        # This is a CONFLICT case (Tech=B, Fund=R).
        # The bullish confirmation guardrail should block mixed_positive bullish
        # when fund is bearish.
        assert r.conflict_detected is True
        # The guardrail will kick in if the fusion tries to output bullish
        # with tech.band == "mixed_positive" and fund.signal == "bearish"
        # Since it's a conflict, if tech wins it'd propose bullish but guardrail blocks it
        # Either way, the result should NOT be bullish
        assert r.final_signal != "bullish" or r.final_signal == "neutral"
