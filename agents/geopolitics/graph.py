from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .config import GeopoliticsSettings
from typing import Protocol, runtime_checkable


@runtime_checkable
class GeopoliticsDataClient(Protocol):
    def build_snapshot(self, as_of_date): ...
from .models import GeopoliticsRequest, GeopoliticsSnapshot
from .reporting import build_text_report
from .rules import evaluate_geopolitics


class GeopoliticsState(TypedDict, total=False):
    request: GeopoliticsRequest
    snapshot: GeopoliticsSnapshot
    llm_result: Optional[Dict[str, Any]]
    evaluation: Dict[str, Any]


def build_graph(client: GeopoliticsDataClient, settings: GeopoliticsSettings):
    graph = StateGraph(GeopoliticsState)

    def fetch_node(state: GeopoliticsState) -> Dict[str, Any]:
        request = state["request"]
        snapshot = client.build_snapshot(request.as_of_date)
        return {"snapshot": snapshot}

    def classify_node(state: GeopoliticsState) -> Dict[str, Any]:
        """Run LLM classification on geo headlines (post-fetch, pre-score)."""
        snapshot: GeopoliticsSnapshot = state["snapshot"]
        llm_result = _run_llm_classification(snapshot)
        return {"llm_result": llm_result}

    def evaluate_node(state: GeopoliticsState) -> Dict[str, Any]:
        evaluation = evaluate_geopolitics(
            state["snapshot"],
            settings,
            llm_result=state.get("llm_result"),
        )
        return {"evaluation": evaluation}

    def render_node(state: GeopoliticsState) -> Dict[str, Any]:
        evaluation = dict(state["evaluation"])
        evaluation["report"] = build_text_report(evaluation)
        return {"evaluation": evaluation}

    graph.add_node("fetch_geo", fetch_node)
    graph.add_node("classify", classify_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("render", render_node)
    graph.add_edge(START, "fetch_geo")
    graph.add_edge("fetch_geo", "classify")
    graph.add_edge("classify", "evaluate")
    graph.add_edge("evaluate", "render")
    graph.add_edge("render", END)
    return graph.compile()


def _run_llm_classification(snapshot: GeopoliticsSnapshot) -> Optional[Dict[str, Any]]:
    """Call shared LLM helper if enabled and geo headlines exist."""
    if not snapshot.headlines:
        return None
    try:
        from agents._shared.llm_summary import generate_summary_safe

        headline_text = "\n".join(
            f"- [{h.published_date}] {h.title} (keywords: {', '.join(h.matched_keywords)})"
            for h in snapshot.headlines[:15]
        )
        return generate_summary_safe(
            agent_id="geopolitics",
            as_of_date=snapshot.as_of_date.isoformat(),
            context=headline_text,
            instruction=(
                "Classify the overall geopolitical risk sentiment for US equities "
                "based on these headlines. Focus on whether these events increase or "
                "decrease market risk for a 1-month swing trade horizon."
            ),
        )
    except Exception:
        return None
