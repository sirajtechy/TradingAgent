"""Unit tests for full-context orchestrator fusion."""

from __future__ import annotations

from agents.orchestrator.config import OrchestratorSettings
from agents.orchestrator.envelope_adapter import envelope_to_agent_output
from agents.orchestrator.agent_breakdown import build_agent_breakdown
from agents.orchestrator.fusion_full import fuse_signals_full
from agents.orchestrator.operator_verdict import map_operator_verdict
from agents.orchestrator.models import FusionResult


def _env(agent_id: str, signal: str, score: float, abstain: bool = False) -> dict:
    return {
        "agent_id": agent_id,
        "signal": signal,
        "score": score,
        "confidence": "medium",
        "band": "good",
        "abstain": abstain,
        "data_quality": "good",
        "warnings": [],
        "extras": {},
    }


def test_should_run_ticker_agents_buy_and_watch():
    """Legacy helper — full pipeline now always runs all agents."""
    from agents.orchestrator.pipeline_full import TICKER_AGENT_IDS

    assert len(TICKER_AGENT_IDS) == 3


def test_envelope_to_agent_output_bullish():
    ao = envelope_to_agent_output(_env("news", "bullish", 72.0))
    assert ao.signal == "bullish"
    assert ao.score == 72.0


def test_fusion_full_weighted_blend_bullish():
    phoenix = {"signal": "BUY", "score": 75.0}
    fund = {
        "experimental_score": {
            "available": True,
            "score": 68.0,
            "band": "good",
            "confidence": "medium",
            "subscores": {},
        },
        "data_quality": {"coverage_ratio": 0.9},
    }
    envelopes = {
        "phoenix": _env("phoenix", "bullish", 75.0),
        "fundamental": _env("fundamental", "bullish", 68.0),
        "macro": _env("macro", "bullish", 60.0),
        "news": _env("news", "bullish", 65.0),
        "insider": _env("insider", "bullish", 70.0),
        "geopolitics": _env("geopolitics", "neutral", 55.0),
    }
    result = fuse_signals_full(
        phoenix_result=phoenix,
        fund_result=fund,
        agent_envelopes=envelopes,
        settings=OrchestratorSettings(),
    )
    assert result.orchestrator_score >= 60.0
    assert result.final_signal == "bullish"
    assert result.operator_verdict == "STRONG BUY"
    assert "phoenix" in result.weights_applied or "tech" in result.weights_applied


def test_fusion_full_abstain_renormalizes():
    phoenix = {"signal": "BUY", "score": 70.0}
    fund = {
        "experimental_score": {
            "available": True,
            "score": 65.0,
            "band": "good",
            "confidence": "medium",
            "subscores": {},
        },
        "data_quality": {"coverage_ratio": 0.9},
    }
    envelopes = {
        "phoenix": _env("phoenix", "bullish", 70.0),
        "fundamental": _env("fundamental", "bullish", 65.0),
        "macro": _env("macro", "bullish", 60.0, abstain=True),
    }
    result = fuse_signals_full(
        phoenix_result=phoenix,
        fund_result=fund,
        agent_envelopes=envelopes,
    )
    assert "macro" not in result.weights_applied
    assert result.orchestrator_score > 0


def test_agent_breakdown_includes_all_agents():
    agents = {
        "phoenix": {"native": {"signal": "AVOID", "score": 0}, "envelope": {"signal": "bearish", "score": 0}, "error": None},
        "fundamental": {"native": None, "envelope": None, "error": "failed"},
    }
    bd = build_agent_breakdown(agents, ticker="NVDA", as_of_date="2026-06-06")
    assert bd["decision_by"] == "human"
    assert "phoenix" in bd["agents"]
    assert "sentiment" in bd["agents"]
    assert bd["agents"]["phoenix"]["phoenix_signal"] == "AVOID"


def test_operator_verdict_sell_on_avoid():
    fusion = FusionResult(
        final_signal="bearish",
        final_confidence=0.5,
        orchestrator_score=30.0,
        conflict_detected=False,
        conflict_resolution=None,
        weights_applied={},
    )
    verdict, reasons = map_operator_verdict(
        phoenix_native={"signal": "AVOID", "score": 25},
        fusion=fusion,
    )
    assert verdict == "SELL"
    assert reasons


def test_operator_verdict_hold_on_watch():
    fusion = FusionResult(
        final_signal="neutral",
        final_confidence=0.5,
        orchestrator_score=55.0,
        conflict_detected=False,
        conflict_resolution=None,
        weights_applied={},
    )
    verdict, _ = map_operator_verdict(
        phoenix_native={"signal": "WATCH", "score": 58},
        fusion=fusion,
    )
    assert verdict == "HOLD"


def test_regime_overlay_caps_bullish_on_risk_off():
    phoenix = {"signal": "BUY", "score": 80.0}
    fund = {
        "experimental_score": {
            "available": True,
            "score": 70.0,
            "band": "good",
            "confidence": "medium",
            "subscores": {},
        },
        "data_quality": {"coverage_ratio": 0.9},
    }
    envelopes = {
        "phoenix": _env("phoenix", "bullish", 80.0),
        "fundamental": _env("fundamental", "bullish", 70.0),
        "macro": _env("macro", "bullish", 65.0),
        "news": _env("news", "bullish", 70.0),
        "insider": _env("insider", "bullish", 68.0),
        "geopolitics": _env("geopolitics", "neutral", 55.0),
    }
    market_summary = {"market_wide_signal": "risk_off", "vix_regime": "extreme"}
    result = fuse_signals_full(
        phoenix_result=phoenix,
        fund_result=fund,
        agent_envelopes=envelopes,
        market_summary_native=market_summary,
        settings=OrchestratorSettings(regime_vix_cap_score=62.0),
    )
    assert result.orchestrator_score <= 62.0
    assert result.market_regime is not None
