from typing import Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph

from .fmp_client import FMPClient
from .models import AnalysisRequest
from .reporting import build_text_report
from .rules import evaluate_snapshot


class AnalysisState(TypedDict, total=False):
    request: AnalysisRequest
    snapshot: Any
    evaluation: Dict[str, Any]


def build_graph(client: FMPClient):
    graph = StateGraph(AnalysisState)

    def fetch_snapshot_node(state: AnalysisState) -> Dict[str, Any]:
        request = state["request"]
        return {"snapshot": client.build_snapshot(request)}

    def evaluate_node(state: AnalysisState) -> Dict[str, Any]:
        request = state["request"]
        snapshot = state["snapshot"]
        return {
            "evaluation": evaluate_snapshot(
                snapshot=snapshot,
                include_experimental_score=request.include_experimental_score,
            )
        }

    def render_node(state: AnalysisState) -> Dict[str, Any]:
        evaluation = dict(state["evaluation"])
        evaluation["report"] = build_text_report(evaluation)
        return {"evaluation": evaluation}

    graph.add_node("fetch_snapshot", fetch_snapshot_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("render", render_node)
    graph.add_edge(START, "fetch_snapshot")
    graph.add_edge("fetch_snapshot", "evaluate")
    graph.add_edge("evaluate", "render")
    graph.add_edge("render", END)
    return graph.compile()
