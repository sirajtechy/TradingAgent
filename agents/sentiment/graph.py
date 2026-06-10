from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .config import SentimentSettings
from .models import SentimentRequest, SentimentSnapshot
from .reporting import build_text_report
from .rules import evaluate_sentiment


class SentimentState(TypedDict, total=False):
    request: SentimentRequest
    snapshot: SentimentSnapshot
    evaluation: Dict[str, Any]


def build_graph(settings: Optional[SentimentSettings] = None):
    cfg = settings or SentimentSettings()
    graph = StateGraph(SentimentState)

    def fetch_node(state: SentimentState) -> Dict[str, Any]:
        request = state["request"]
        snapshot = _build_snapshot(request.ticker, request.as_of_date)
        return {"snapshot": snapshot}

    def evaluate_node(state: SentimentState) -> Dict[str, Any]:
        evaluation = evaluate_sentiment(state["snapshot"], cfg)
        return {"evaluation": evaluation}

    def render_node(state: SentimentState) -> Dict[str, Any]:
        evaluation = dict(state["evaluation"])
        evaluation["report"] = build_text_report(evaluation)
        return {"evaluation": evaluation}

    graph.add_node("fetch_dimensions", fetch_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("render", render_node)
    graph.add_edge(START, "fetch_dimensions")
    graph.add_edge("fetch_dimensions", "evaluate")
    graph.add_edge("evaluate", "render")
    graph.add_edge("render", END)
    return graph.compile()


def _build_snapshot(ticker: str, as_of_date: Any) -> SentimentSnapshot:
    """
    Collect sub-agent outputs for all available dimensions.

    Each sub-agent call is wrapped in try/except to degrade gracefully.
    """
    from datetime import date as _date

    sources: list = []
    warnings: list = []
    news_eval: Optional[Dict[str, Any]] = None
    insider_eval: Optional[Dict[str, Any]] = None
    macro_eval: Optional[Dict[str, Any]] = None
    ohlcv_ctx: Optional[Dict[str, Any]] = None

    as_of_str = as_of_date.isoformat() if isinstance(as_of_date, _date) else str(as_of_date)

    try:
        from agents.news.service import analyze_ticker as news_analyze
        news_eval = news_analyze(ticker=ticker, as_of_date=as_of_str)
        sources.append("news_agent")
    except Exception as exc:
        warnings.append(f"News agent unavailable: {exc}")

    try:
        from agents.insider.service import analyze_ticker as insider_analyze
        insider_eval = insider_analyze(ticker=ticker, as_of_date=as_of_str)
        sources.append("insider_agent")
    except Exception as exc:
        warnings.append(f"Insider agent unavailable: {exc}")

    try:
        from agents.macro.service import analyze_market as macro_analyze
        macro_eval = macro_analyze(as_of_date=as_of_str)
        sources.append("macro_agent")
    except Exception as exc:
        warnings.append(f"Macro agent unavailable: {exc}")

    geo_eval: Optional[Dict[str, Any]] = None
    try:
        from agents.geopolitics.service import analyze_market as geo_analyze
        geo_eval = geo_analyze(as_of_date=as_of_str)
        sources.append("geopolitics_agent")
    except Exception as exc:
        warnings.append(f"Geopolitics agent unavailable: {exc}")

    try:
        from agents.polygon_data import PolygonClient
        pc = PolygonClient()
        if pc.is_available():
            result = pc.get_close_price(ticker, as_of_date if isinstance(as_of_date, _date) else _date.fromisoformat(as_of_str))
            if result:
                close_price, bar_date = result
                df = pc.fetch_daily_bars(ticker, as_of_date if isinstance(as_of_date, _date) else _date.fromisoformat(as_of_str), lookback_days=10)
                change_5d = None
                if df is not None and len(df) > 5:
                    prior = float(df["Close"].iloc[-6])
                    if prior > 0:
                        change_5d = round(((close_price - prior) / prior) * 100.0, 2)
                ohlcv_ctx = {"close": round(close_price, 2), "change_5d_pct": change_5d}
                sources.append("polygon:ohlcv")
    except Exception as exc:
        warnings.append(f"OHLCV context unavailable: {exc}")

    return SentimentSnapshot(
        ticker=ticker,
        as_of_date=as_of_date if isinstance(as_of_date, _date) else _date.fromisoformat(as_of_str),
        news_eval=news_eval,
        insider_eval=insider_eval,
        macro_eval=macro_eval,
        geopolitics_eval=geo_eval,
        ohlcv_context=ohlcv_ctx,
        data_sources=sources,
        warnings=warnings,
    )
