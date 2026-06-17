from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .config import NewsSettings
from .fmp_client import FMPNewsClient
from .models import NewsRequest, NewsSnapshot
from .reporting import build_text_report
from .rules import evaluate_news


class NewsState(TypedDict, total=False):
    request: NewsRequest
    snapshot: NewsSnapshot
    current_close: Optional[float]
    evaluation: Dict[str, Any]


def build_graph(client: FMPNewsClient, settings: NewsSettings):
    graph = StateGraph(NewsState)

    def fetch_node(state: NewsState) -> Dict[str, Any]:
        request = state["request"]
        snapshot = client.build_snapshot(request.ticker, request.as_of_date)
        close = _fetch_close(request.ticker, request.as_of_date)
        return {"snapshot": snapshot, "current_close": close}

    def evaluate_node(state: NewsState) -> Dict[str, Any]:
        evaluation = evaluate_news(
            state["snapshot"],
            settings,
            current_close=state.get("current_close"),
        )
        return {"evaluation": evaluation}

    def enrich_llm_node(state: NewsState) -> Dict[str, Any]:
        """Post-score LLM enrichment — adds sentiment + bullets without changing scores."""
        evaluation = dict(state["evaluation"])
        llm = _run_news_llm(state["snapshot"], state["request"])
        if llm:
            evaluation["llm_sentiment"] = llm.get("sentiment")
            if llm.get("bullets"):
                evaluation["bullets"] = list(llm["bullets"])[:3]
        return {"evaluation": evaluation}

    def render_node(state: NewsState) -> Dict[str, Any]:
        evaluation = dict(state["evaluation"])
        snapshot = state["snapshot"]
        evaluation["report"] = build_text_report(evaluation)
        evaluation["headlines"] = [
            {
                "title": h.title,
                "source": h.source,
                "date": h.published_date.isoformat(),
                "url": h.url,
            }
            for h in snapshot.headlines[:10]
        ]
        return {"evaluation": evaluation}

    graph.add_node("fetch_news", fetch_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("enrich_llm", enrich_llm_node)
    graph.add_node("render", render_node)
    graph.add_edge(START, "fetch_news")
    graph.add_edge("fetch_news", "evaluate")
    graph.add_edge("evaluate", "enrich_llm")
    graph.add_edge("enrich_llm", "render")
    graph.add_edge("render", END)
    return graph.compile()


def _run_news_llm(snapshot: Any, request: Any) -> Optional[Dict[str, Any]]:
    """Call shared LLM helper if enabled and headlines exist."""
    if not snapshot.headlines:
        return None
    try:
        from agents._shared.llm_summary import generate_summary_safe

        headline_text = "\n".join(
            f"- [{h.published_date}] {h.title} ({h.source})"
            for h in snapshot.headlines[:10]
        )
        return generate_summary_safe(
            agent_id="news",
            as_of_date=request.as_of_date.isoformat(),
            context=f"Ticker: {request.ticker}\n\nRecent headlines:\n{headline_text}",
            instruction=(
                "Classify the news sentiment for this stock and produce "
                "2-3 bullet points summarizing the key takeaways."
            ),
        )
    except Exception:
        return None


def _fetch_close(ticker: str, as_of_date: Any) -> Optional[float]:
    try:
        from agents.polygon_data import PolygonClient

        client = PolygonClient()
        if not client.is_available():
            return None
        result = client.get_close_price(ticker, as_of_date)
        return result[0] if result else None
    except Exception:
        return None
