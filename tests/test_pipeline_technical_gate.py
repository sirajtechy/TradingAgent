"""Pipeline full analysis — technical enrichment gate."""

from __future__ import annotations

from unittest.mock import patch

from agents.orchestrator.pipeline_full import run_full_analysis


def _tech_fail():
    return {
        "ok": True,
        "agent_id": "technical",
        "signal": "bearish",
        "technical_fusion": {"pass_enrichment": False, "pass_reason": "hard filters failed"},
        "phoenix": {"signal": "AVOID", "hard_filter_passed": False},
    }


def _tech_pass():
    return {
        "ok": True,
        "agent_id": "technical",
        "signal": "bullish",
        "technical_fusion": {"pass_enrichment": True, "pass_reason": "Phoenix BUY + 3/4 triggers"},
        "phoenix": {"signal": "BUY", "score": 80, "hard_filter_passed": True},
        "strategy_layers": {},
    }


@patch("agents.orchestrator.pipeline_full.fuse_signals_full")
@patch("agents.orchestrator.pipeline_full.load_or_run_session_context")
@patch("agents.orchestrator.pipeline_full._safe_analyze")
def test_full_analysis_gated_when_technical_fails(mock_safe, mock_session, mock_fuse):
    mock_session.return_value = {}

    def side_effect(agent_id, **kwargs):
        if agent_id == "technical":
            return _tech_fail(), {"signal": "bearish"}, None
        return None, None, "skipped"

    mock_safe.side_effect = side_effect

    out = run_full_analysis(
        ticker="TEST",
        as_of_date="2025-09-01",
        technical_pass_only=True,
    )
    assert out.get("gated") is True
    assert out.get("pass_enrichment") is False
    assert out.get("all_agents_ran") is False
    mock_fuse.assert_not_called()


@patch("agents.orchestrator.pipeline_full.build_agent_breakdown")
@patch("agents.orchestrator.pipeline_full.build_deterministic_digest")
@patch("agents.orchestrator.pipeline_full.fuse_signals_full")
@patch("agents.orchestrator.pipeline_full.load_or_run_session_context")
@patch("agents.orchestrator.pipeline_full._safe_analyze")
def test_full_analysis_runs_enrichment_when_technical_passes(
    mock_safe, mock_session, mock_fuse, mock_digest, mock_breakdown
):
    mock_session.return_value = {}
    mock_digest.return_value = {"bullets": ["ok"]}
    mock_breakdown.return_value = {"agents": []}

    from agents.orchestrator.models import FusionResult

    mock_fuse.return_value = FusionResult(
        final_signal="bullish",
        final_confidence=0.7,
        orchestrator_score=70.0,
        conflict_detected=False,
        conflict_resolution=None,
        weights_applied={"tech": 0.9, "fund": 0.1},
        operator_verdict="buy",
    )

    calls = []

    def side_effect(agent_id, **kwargs):
        calls.append(agent_id)
        if agent_id == "technical":
            return _tech_pass(), {"signal": "bullish"}, None
        if agent_id == "fundamental":
            return {"experimental_score": {"available": True, "score": 60}}, {"signal": "neutral"}, None
        if agent_id in ("news", "insider", "sentiment"):
            return {"signal": "neutral", "score": 50}, {"signal": "neutral"}, None
        return {"signal": "neutral"}, {"signal": "neutral"}, None

    mock_safe.side_effect = side_effect

    out = run_full_analysis(
        ticker="TEST",
        as_of_date="2025-09-01",
        technical_pass_only=True,
    )
    assert out.get("gated") is False
    assert out.get("all_agents_ran") is True
    assert "fundamental" in calls
    mock_fuse.assert_called_once()
