"""
test_orchestrator_graph.py — Integration tests for the orchestrator LangGraph pipeline.

Uses mocked sub-agents to test the full pipeline without network calls.
"""

import pytest
from unittest.mock import patch, MagicMock

from orchestrator_agent.config import OrchestratorSettings
from orchestrator_agent.graph import build_graph
from orchestrator_agent.models import OrchestratorState, FusionResult


# ---------------------------------------------------------------------------
# Mock evaluation dicts
# ---------------------------------------------------------------------------

def _mock_tech_eval(score=70.0, band="good", confidence="medium"):
    return {
        "experimental_score": {
            "available": True,
            "score": score,
            "band": band,
            "confidence": confidence,
            "subscores": {"ema_trend": 75, "macd": 65, "rsi": 70},
        },
        "frameworks": {
            "ema_trend": {"applicable": True, "score_pct": 75},
            "macd": {"applicable": True, "score_pct": 65},
        },
        "key_indicators": {"adx_value": 25, "adx_confidence": "medium"},
        "as_of_price": {"price": 150.0, "price_date": "2025-06-01"},
        "company": {"ticker": "AAPL", "company_name": "Apple Inc."},
        "warnings": [],
    }


def _mock_fund_eval(score=75.0, band="good", confidence="high"):
    return {
        "experimental_score": {
            "available": True,
            "score": score,
            "band": band,
            "confidence": confidence,
            "subscores": {
                "financial_health": 80,
                "valuation": 70,
                "quality": 75,
                "growth": 72,
            },
        },
        "frameworks": {
            "graham": {"applicable": True, "score_pct": 70},
            "piotroski": {"applicable": True, "score_pct": 80},
        },
        "data_quality": {"coverage_ratio": 0.95, "warnings_count": 0},
        "as_of_price": {"price": 150.0, "price_date": "2025-06-01"},
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Graph pipeline tests
# ---------------------------------------------------------------------------

class TestOrchestratorGraph:
    """Test the full 4-node LangGraph pipeline with mocked sub-agents."""

    @patch("orchestrator_agent.graph.run_fundamental")
    @patch("orchestrator_agent.graph.run_technical")
    def test_full_pipeline_agreement(self, mock_tech_node, mock_fund_node):
        """Both agents bullish → orchestrator bullish."""
        mock_tech_node.return_value = {
            "tech_result": _mock_tech_eval(70.0, "good"),
            "tech_error": None,
        }
        mock_fund_node.return_value = {
            "fund_result": _mock_fund_eval(75.0, "good"),
            "fund_error": None,
        }

        graph = build_graph()
        compiled = graph.compile()
        state = compiled.invoke({
            "ticker": "AAPL",
            "analysis_date": "2025-06-01",
        })

        assert state["ticker"] == "AAPL"
        fusion = state["fusion"]
        assert isinstance(fusion, FusionResult)
        assert fusion.final_signal == "bullish"
        assert fusion.conflict_detected is False
        assert state["text_report"] is not None
        assert "AAPL" in state["text_report"]

    @patch("orchestrator_agent.graph.run_fundamental")
    @patch("orchestrator_agent.graph.run_technical")
    def test_pipeline_tech_error(self, mock_tech_node, mock_fund_node):
        """Tech agent fails → falls back to fund only."""
        mock_tech_node.return_value = {
            "tech_result": None,
            "tech_error": "Network timeout",
        }
        mock_fund_node.return_value = {
            "fund_result": _mock_fund_eval(75.0, "good"),
            "fund_error": None,
        }

        graph = build_graph()
        compiled = graph.compile()
        state = compiled.invoke({
            "ticker": "MSFT",
            "analysis_date": "2025-06-01",
        })

        fusion = state["fusion"]
        assert fusion.final_signal == "bullish"
        assert fusion.tech_error == "Network timeout"
        assert fusion.weights_applied == {"tech": 0.0, "fund": 1.0}

    @patch("orchestrator_agent.graph.run_fundamental")
    @patch("orchestrator_agent.graph.run_technical")
    def test_pipeline_both_neutral(self, mock_tech_node, mock_fund_node):
        """Both agents neutral → orchestrator neutral with high confidence."""
        mock_tech_node.return_value = {
            "tech_result": _mock_tech_eval(45.0, "mixed"),
            "tech_error": None,
        }
        mock_fund_node.return_value = {
            "fund_result": _mock_fund_eval(48.0, "mixed"),
            "fund_error": None,
        }

        graph = build_graph()
        compiled = graph.compile()
        state = compiled.invoke({
            "ticker": "GOOG",
            "analysis_date": "2025-06-01",
        })

        fusion = state["fusion"]
        assert fusion.final_signal == "neutral"
        assert fusion.final_confidence == 0.70

    @patch("orchestrator_agent.graph.run_fundamental")
    @patch("orchestrator_agent.graph.run_technical")
    def test_pipeline_conflict(self, mock_tech_node, mock_fund_node):
        """Tech bullish vs Fund bearish → conflict detected."""
        mock_tech_node.return_value = {
            "tech_result": _mock_tech_eval(70.0, "good"),
            "tech_error": None,
        }
        mock_fund_node.return_value = {
            "fund_result": _mock_fund_eval(25.0, "weak"),
            "fund_error": None,
        }

        graph = build_graph()
        compiled = graph.compile()
        state = compiled.invoke({
            "ticker": "TSLA",
            "analysis_date": "2025-06-01",
        })

        fusion = state["fusion"]
        assert fusion.conflict_detected is True
        assert fusion.conflict_resolution is not None

    @patch("orchestrator_agent.graph.run_fundamental")
    @patch("orchestrator_agent.graph.run_technical")
    def test_report_contains_sections(self, mock_tech_node, mock_fund_node):
        """Report includes all expected sections."""
        mock_tech_node.return_value = {
            "tech_result": _mock_tech_eval(70.0, "good"),
            "tech_error": None,
        }
        mock_fund_node.return_value = {
            "fund_result": _mock_fund_eval(75.0, "good"),
            "fund_error": None,
        }

        graph = build_graph()
        compiled = graph.compile()
        state = compiled.invoke({
            "ticker": "AAPL",
            "analysis_date": "2025-06-01",
        })

        report = state["text_report"]
        assert "ORCHESTRATOR REPORT" in report
        assert "TECHNICAL AGENT" in report
        assert "FUNDAMENTAL AGENT" in report
        assert "SIGNAL" in report
        assert "SCORE" in report

    @patch("orchestrator_agent.graph.run_fundamental")
    @patch("orchestrator_agent.graph.run_technical")
    def test_pipeline_both_errors(self, mock_tech_node, mock_fund_node):
        """Both agents fail → neutral with zero confidence."""
        mock_tech_node.return_value = {
            "tech_result": None,
            "tech_error": "Tech crash",
        }
        mock_fund_node.return_value = {
            "fund_result": None,
            "fund_error": "Fund crash",
        }

        graph = build_graph()
        compiled = graph.compile()
        state = compiled.invoke({
            "ticker": "BAD",
            "analysis_date": "2025-06-01",
        })

        fusion = state["fusion"]
        assert fusion.final_signal == "neutral"
        assert fusion.final_confidence == 0.0
        assert fusion.tech_error == "Tech crash"
        assert fusion.fund_error == "Fund crash"


class TestRouteRequest:
    """Test the route_request node normalisation."""

    @patch("orchestrator_agent.graph.run_fundamental")
    @patch("orchestrator_agent.graph.run_technical")
    def test_ticker_uppercased(self, mock_tech_node, mock_fund_node):
        mock_tech_node.return_value = {
            "tech_result": _mock_tech_eval(),
            "tech_error": None,
        }
        mock_fund_node.return_value = {
            "fund_result": _mock_fund_eval(),
            "fund_error": None,
        }

        graph = build_graph()
        compiled = graph.compile()
        state = compiled.invoke({
            "ticker": "aapl",
            "analysis_date": "2025-06-01",
        })

        assert state["ticker"] == "AAPL"
