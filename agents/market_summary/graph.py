from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .data_client import MarketSummaryDataClient
from .models import MarketSummaryRequest
from .reporting import build_text_report
from .rules import evaluate_market_summary


class MarketSummaryState(TypedDict, total=False):
    request: MarketSummaryRequest
    macro_eval: Dict[str, Any]
    market_snapshot: Any
    evaluation: Dict[str, Any]


def build_graph(data_client: MarketSummaryDataClient):
    graph = StateGraph(MarketSummaryState)

    def fetch_macro_node(state: MarketSummaryState) -> Dict[str, Any]:
        from agents.macro.service import analyze_market

        as_of = state["request"].as_of_date.isoformat()
        return {"macro_eval": analyze_market(as_of_date=as_of)}

    def fetch_market_node(state: MarketSummaryState) -> Dict[str, Any]:
        request = state["request"]
        snapshot = data_client.build_snapshot(request.as_of_date)
        return {"market_snapshot": snapshot}

    def evaluate_node(state: MarketSummaryState) -> Dict[str, Any]:
        evaluation = evaluate_market_summary(
            market_snapshot=state["market_snapshot"],
            macro_eval=state["macro_eval"],
        )
        return {"evaluation": evaluation}

    def enrich_llm_node(state: MarketSummaryState) -> Dict[str, Any]:
        """Post-score LLM briefing bullets — never changes scores."""
        evaluation = dict(state["evaluation"])
        llm = _run_market_summary_llm(evaluation)
        if llm and llm.get("bullets"):
            evaluation["bullets"] = list(llm["bullets"])[:3]
        return {"evaluation": evaluation}

    def render_node(state: MarketSummaryState) -> Dict[str, Any]:
        evaluation = dict(state["evaluation"])
        evaluation["report"] = build_text_report(evaluation)
        return {"evaluation": evaluation}

    graph.add_node("fetch_macro", fetch_macro_node)
    graph.add_node("fetch_market", fetch_market_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("enrich_llm", enrich_llm_node)
    graph.add_node("render", render_node)
    graph.add_edge(START, "fetch_macro")
    graph.add_edge(START, "fetch_market")
    graph.add_edge("fetch_macro", "evaluate")
    graph.add_edge("fetch_market", "evaluate")
    graph.add_edge("evaluate", "enrich_llm")
    graph.add_edge("enrich_llm", "render")
    graph.add_edge("render", END)
    return graph.compile()


def _run_market_summary_llm(evaluation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call shared LLM helper if enabled."""
    try:
        from agents._shared.llm_summary import generate_summary_safe

        context_parts = [
            f"VIX: {evaluation.get('vix')} ({evaluation.get('vix_regime')})",
            f"SPY 20d: {evaluation.get('spy_change_20d_pct')}%",
            f"Market-wide signal: {evaluation.get('market_wide_signal')}",
        ]
        macro = evaluation.get("macro") or {}
        metrics = macro.get("metrics") or {}
        if metrics.get("cpi_yoy_pct") is not None:
            context_parts.append(f"CPI YoY: {metrics['cpi_yoy_pct']}%")
        if metrics.get("fed_funds") is not None:
            context_parts.append(f"Fed funds: {metrics['fed_funds']}%")

        leaders = evaluation.get("sector_leaders") or []
        if leaders:
            context_parts.append(f"Sector leaders: {', '.join(l['label'] for l in leaders[:3])}")

        return generate_summary_safe(
            agent_id="market_summary",
            as_of_date=evaluation.get("as_of_date", ""),
            context="\n".join(context_parts),
            instruction=(
                "Produce a concise daily market briefing for a swing trader. "
                "Focus on whether the overall market environment is favorable for new long positions."
            ),
        )
    except Exception:
        return None
