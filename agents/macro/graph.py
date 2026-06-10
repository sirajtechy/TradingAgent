from __future__ import annotations

from typing import Any, Dict, Protocol, TypedDict, runtime_checkable

from langgraph.graph import END, START, StateGraph

from .models import MacroRequest
from .reporting import build_text_report
from .rules import evaluate_metrics


class MacroState(TypedDict, total=False):
    request: MacroRequest
    metrics: Dict[str, Any]
    data_sources: list[str]
    warnings: list[str]
    evaluation: Dict[str, Any]


@runtime_checkable
class MacroDataClient(Protocol):
    def build_snapshot(self, as_of_date: Any) -> Any: ...


def build_graph(client: MacroDataClient):
    graph = StateGraph(MacroState)

    def fetch_node(state: MacroState) -> Dict[str, Any]:
        request = state["request"]
        metrics, sources, warnings = client.build_snapshot(request.as_of_date)
        return {"metrics": metrics, "data_sources": sources, "warnings": warnings}

    def evaluate_node(state: MacroState) -> Dict[str, Any]:
        evaluation = evaluate_metrics(
            state["metrics"],
            state.get("warnings") or [],
            state.get("data_sources") or [],
        )
        return {"evaluation": evaluation}

    def render_node(state: MacroState) -> Dict[str, Any]:
        evaluation = dict(state["evaluation"])
        evaluation["report"] = build_text_report(evaluation)
        return {"evaluation": evaluation}

    graph.add_node("fetch_macro", fetch_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("render", render_node)
    graph.add_edge(START, "fetch_macro")
    graph.add_edge("fetch_macro", "evaluate")
    graph.add_edge("evaluate", "render")
    graph.add_edge("render", END)
    return graph.compile()
