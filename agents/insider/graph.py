from __future__ import annotations

from typing import Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph

from typing import Protocol, runtime_checkable


@runtime_checkable
class InsiderDataClient(Protocol):
    def build_snapshot(self, ticker: str, as_of_date): ...
from .models import InsiderRequest, InsiderSnapshot
from .reporting import build_text_report
from .rules import evaluate_insider


class InsiderState(TypedDict, total=False):
    request: InsiderRequest
    snapshot: InsiderSnapshot
    evaluation: Dict[str, Any]


def build_graph(client: InsiderDataClient):
    graph = StateGraph(InsiderState)

    def fetch_node(state: InsiderState) -> Dict[str, Any]:
        request = state["request"]
        snapshot = client.build_snapshot(request.ticker, request.as_of_date)
        return {"snapshot": snapshot}

    def evaluate_node(state: InsiderState) -> Dict[str, Any]:
        evaluation = evaluate_insider(state["snapshot"])
        return {"evaluation": evaluation}

    def render_node(state: InsiderState) -> Dict[str, Any]:
        evaluation = dict(state["evaluation"])
        evaluation["report"] = build_text_report(evaluation)
        return {"evaluation": evaluation}

    graph.add_node("fetch_insider", fetch_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("render", render_node)
    graph.add_edge(START, "fetch_insider")
    graph.add_edge("fetch_insider", "evaluate")
    graph.add_edge("evaluate", "render")
    graph.add_edge("render", END)
    return graph.compile()
