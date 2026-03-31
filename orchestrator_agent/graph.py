"""
graph.py — LangGraph pipeline for the orchestrator agent.

4-node pipeline:
  route_request → [run_technical ‖ run_fundamental] → fuse → render
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, StateGraph

from .config import OrchestratorSettings
from .fusion import fuse_signals
from .models import OrchestratorState
from .reporting import build_text_report


_DEFAULT_SETTINGS = OrchestratorSettings()


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def route_request(state: OrchestratorState) -> Dict[str, Any]:
    """Validate inputs and normalise the ticker."""
    return {"ticker": state["ticker"].upper()}


def run_technical(state: OrchestratorState) -> Dict[str, Any]:
    """Invoke the technical analysis agent."""
    from technical_agent.service import analyze_ticker as tech_analyze

    try:
        result = tech_analyze(
            ticker=state["ticker"],
            as_of_date=state.get("analysis_date"),
        )
        return {"tech_result": result, "tech_error": None}
    except Exception as exc:
        return {"tech_result": None, "tech_error": str(exc)}


def run_fundamental(state: OrchestratorState) -> Dict[str, Any]:
    """Invoke the fundamental analysis agent."""
    from fundamental_agent.service import analyze_ticker as fund_analyze

    try:
        result = fund_analyze(
            ticker=state["ticker"],
            as_of_date=state.get("analysis_date"),
            data_source=_DEFAULT_SETTINGS.fund_data_source,
        )
        return {"fund_result": result, "fund_error": None}
    except Exception as exc:
        return {"fund_result": None, "fund_error": str(exc)}


def fuse(state: OrchestratorState) -> Dict[str, Any]:
    """Run the CWAF fusion engine over both agents' results."""
    fusion_result = fuse_signals(
        tech_result=state.get("tech_result"),
        tech_error=state.get("tech_error"),
        fund_result=state.get("fund_result"),
        fund_error=state.get("fund_error"),
        settings=_DEFAULT_SETTINGS,
    )
    return {"fusion": fusion_result}


def render(state: OrchestratorState) -> Dict[str, Any]:
    """Build the final text report."""
    report = build_text_report(
        ticker=state["ticker"],
        analysis_date=state.get("analysis_date", "latest"),
        fusion=state["fusion"],
        tech_result=state.get("tech_result"),
        fund_result=state.get("fund_result"),
    )
    return {"text_report": report}


# ---------------------------------------------------------------------------
# Graph wiring
# ---------------------------------------------------------------------------

def build_graph(settings: OrchestratorSettings | None = None) -> StateGraph:
    """
    Construct (but do not compile) the orchestrator LangGraph.

    The caller should do ``graph.compile()`` to get a runnable.
    """
    global _DEFAULT_SETTINGS
    if settings is not None:
        _DEFAULT_SETTINGS = settings

    graph = StateGraph(OrchestratorState)

    graph.add_node("route_request", route_request)
    graph.add_node("run_technical", run_technical)
    graph.add_node("run_fundamental", run_fundamental)
    graph.add_node("fuse", fuse)
    graph.add_node("render", render)

    graph.set_entry_point("route_request")

    # Fan-out: route_request → run_technical AND run_fundamental
    graph.add_edge("route_request", "run_technical")
    graph.add_edge("route_request", "run_fundamental")

    # Fan-in: both agents → fuse
    graph.add_edge("run_technical", "fuse")
    graph.add_edge("run_fundamental", "fuse")

    # fuse → render → END
    graph.add_edge("fuse", "render")
    graph.add_edge("render", END)

    return graph
