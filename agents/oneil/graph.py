"""
graph.py — LangGraph pipeline for the O'Neil Technical Analysis Agent.

Pipeline (sequential 5-node graph):

  START
    │
    ▼
  fetch_data         Download weekly + daily OHLCV bars (ONeilDataClient)
    │
    ▼
  compute_indicators Compute all weekly indicators + daily EMA-200
    │
    ▼
  detect_patterns    Detect O'Neil base patterns on weekly bars
    │
    ▼
  stage_and_score    Weinstein stage classification + rules.evaluate()
    │
    ▼
  END

All state is carried forward in a typed ONeilState dict.  Each node is a
pure function (state → partial update dict) to keep side-effects isolated.

Error handling:
  Node failures surface as exceptions propagated to the caller (service.py).
  The graph does NOT swallow errors — it lets DataError / ValueError propagate
  so the service layer can decide whether to return a neutral signal or re-raise.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .data_client import ONeilDataClient
from .indicators import compute_daily_ema200, compute_weekly
from .models import BasePattern, DailyBar, ONeilRequest, ONeilSignal, StageResult, WeeklyBar
from .patterns import detect_all_patterns
from .rules import evaluate
from .stage_analysis import classify_stage


# ─────────────────────────────────────────────────────────────────────────────
# State definition
# ─────────────────────────────────────────────────────────────────────────────

class ONeilState(TypedDict, total=False):
    """Shared mutable state threaded through the pipeline nodes."""

    # Input
    request: ONeilRequest

    # Data layer
    weekly_bars:  List[WeeklyBar]
    daily_bars:   List[DailyBar]
    company_name: str

    # Computed indicators
    weekly_indicators: Dict[str, Optional[float]]
    daily_ema200:      Optional[float]

    # Pattern detection
    patterns: List[BasePattern]

    # Stage analysis
    stage: StageResult

    # Final output
    signal:   ONeilSignal
    warnings: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# Node implementations
# ─────────────────────────────────────────────────────────────────────────────

def _node_fetch_data(state: ONeilState) -> Dict[str, Any]:
    """Node 1 — Download weekly + daily OHLCV bars."""
    request: ONeilRequest = state["request"]
    client = ONeilDataClient()
    weekly_bars, daily_bars, company_name = client.fetch(request)
    return {
        "weekly_bars":  weekly_bars,
        "daily_bars":   daily_bars,
        "company_name": company_name,
        "warnings":     [],
    }


def _node_compute_indicators(state: ONeilState) -> Dict[str, Any]:
    """
    Node 2 — Compute indicators.

    For US tickers with a Polygon key, fetches pre-computed RSI/MACD/EMA values
    from Polygon.io in parallel (more accurate, warmed up on 10+ years of data).
    Falls back to locally-computed values from the raw bars in all other cases.
    Volume-ratio (10w) is always computed locally since Polygon has no endpoint for it.
    """
    request     = state["request"]
    weekly_bars = state["weekly_bars"]
    daily_bars  = state["daily_bars"]

    # Local computation (always available; used as base / fallback)
    local_inds   = compute_weekly(weekly_bars)
    daily_ema200 = compute_daily_ema200(daily_bars)

    # Try Polygon server-side indicators for US tickers
    if request.exchange.upper() == "US":
        try:
            from .polygon_client import PolygonONeilClient
            poly = PolygonONeilClient()
            if poly.is_available():
                _, _, polygon_inds, _ = poly.fetch_with_indicators(request)
                # Merge: Polygon values override local where non-None
                merged = {**local_inds}
                for k, v in polygon_inds.items():
                    if v is not None:
                        merged[k] = v
                # volume_ratio_10w is NOT available from Polygon — keep local value
                merged["volume_ratio_10w"] = local_inds.get("volume_ratio_10w")
                # EMA-200d: Polygon daily takes precedence
                if polygon_inds.get("ema_200d") is not None:
                    daily_ema200 = polygon_inds["ema_200d"]
                return {"weekly_indicators": merged, "daily_ema200": daily_ema200}
        except Exception:
            pass   # fall through to local indicators

    return {
        "weekly_indicators": local_inds,
        "daily_ema200":      daily_ema200,
    }


def _node_detect_patterns(state: ONeilState) -> Dict[str, Any]:
    """Node 3 — Detect O'Neil base patterns on the weekly bar series."""
    weekly_bars = state["weekly_bars"]
    patterns = detect_all_patterns(weekly_bars)
    return {"patterns": patterns}


def _node_stage_and_score(state: ONeilState) -> Dict[str, Any]:
    """
    Node 4 — Classify the market stage (Weinstein) and run rules.evaluate()
    to produce the final ONeilSignal.
    """
    request       = state["request"]
    weekly_bars   = state["weekly_bars"]
    weekly_inds   = state.get("weekly_indicators", {})
    daily_ema200  = state.get("daily_ema200")
    patterns      = state.get("patterns", [])
    warnings_list = state.get("warnings", [])

    stage = classify_stage(weekly_bars)

    # Last close
    last_close: float = weekly_bars[-1].close if weekly_bars else 0.0

    signal = evaluate(
        request=request,
        weekly_inds=weekly_inds,
        daily_ema200=daily_ema200,
        patterns=patterns,
        stage=stage,
        last_close=last_close,
        warnings=warnings_list,
    )

    return {
        "stage":   stage,
        "signal":  signal,
        "warnings": signal.warnings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────────────────────────────────────

def build_graph():
    """
    Compile and return the O'Neil analysis LangGraph.

    Returns a CompiledStateGraph that accepts an ``ONeilState`` dict with
    at least the ``request`` key populated.  Invoke with::

        graph = build_graph()
        final_state = graph.invoke({"request": request})
        signal: ONeilSignal = final_state["signal"]
    """
    g = StateGraph(ONeilState)

    g.add_node("fetch_data",          _node_fetch_data)
    g.add_node("compute_indicators",  _node_compute_indicators)
    g.add_node("detect_patterns",     _node_detect_patterns)
    g.add_node("stage_and_score",     _node_stage_and_score)

    g.add_edge(START,                "fetch_data")
    g.add_edge("fetch_data",         "compute_indicators")
    g.add_edge("compute_indicators", "detect_patterns")
    g.add_edge("detect_patterns",    "stage_and_score")
    g.add_edge("stage_and_score",    END)

    return g.compile()
