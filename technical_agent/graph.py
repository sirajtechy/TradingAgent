"""
graph.py — LangGraph pipeline for the technical analysis agent.

Implements a 5-node StateGraph with **parallel fan-out** for Nodes 2 & 3:

    START
      │
      ▼
    fetch_data              ← Node 1: download OHLCV bars
      │
      ├──► compute_indicators   ← Node 2: pure-math indicator computation
      │                          (runs in parallel with Node 3)
      └──► detect_patterns      ← Node 3: chart pattern scanning
                │          │
                └────┬─────┘
                     ▼
                  evaluate             ← Node 4: 7 frameworks + composite score
                     │
                     ▼
                   render              ← Node 5: text report generation
                     │
                     ▼
                    END

Nodes 2 and 3 share no data dependency — they both read only from
``snapshot`` (written by Node 1).  LangGraph will execute them
concurrently and trigger Node 4 only after both have written their
results to state.
"""

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .data_client import YFinanceTechnicalClient
from .indicators import compute_all_indicators
from .low_volume_validator import validate_stock_reliability, apply_reliability_adjustments
from .models import PatternSignal, RawTechnicalSnapshot, TechnicalRequest
from .patterns import detect_all_patterns
from .reporting import build_text_report
from .rules import evaluate_snapshot


# ----------------------------------------------------------------------- #
# State schema                                                              #
# ----------------------------------------------------------------------- #

class TechnicalState(TypedDict, total=False):
    """
    Typed state flowing through the graph.

    Keys are added progressively by each node:
        request     → set by caller
        snapshot    → set by fetch_data
        indicators  → set by compute_indicators
        patterns    → set by detect_patterns
        evaluation  → set by evaluate, enriched by render
    """
    request: TechnicalRequest
    snapshot: RawTechnicalSnapshot
    indicators: Dict[str, Any]
    patterns: List[Dict[str, Any]]
    pattern_warnings: List[str]
    evaluation: Dict[str, Any]


# ----------------------------------------------------------------------- #
# Graph builder                                                             #
# ----------------------------------------------------------------------- #

def build_graph(client: YFinanceTechnicalClient):
    """
    Construct and compile the LangGraph StateGraph.

    Args:
        client: A ``YFinanceTechnicalClient`` instance used by Node 1.

    Returns:
        A compiled LangGraph runnable that accepts
        ``{"request": TechnicalRequest}`` and produces
        ``{"evaluation": {...}}``.
    """
    graph = StateGraph(TechnicalState)

    # ── Node 1: fetch_data ─────────────────────────────────────────── #
    def fetch_data_node(state: TechnicalState) -> Dict[str, Any]:
        """Download OHLCV bars from yfinance and build the snapshot."""
        request = state["request"]
        snapshot = client.build_snapshot(request)
        return {"snapshot": snapshot}

    # ── Node 2: compute_indicators (parallel with Node 3) ─────────── #
    def compute_indicators_node(state: TechnicalState) -> Dict[str, Any]:
        """Compute all technical indicator arrays from raw bars."""
        snapshot: RawTechnicalSnapshot = state["snapshot"]
        bars = snapshot.bars

        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        volumes = [b.volume for b in bars]

        indicators = compute_all_indicators(closes, highs, lows, volumes)
        return {"indicators": indicators}

    # ── Node 3: detect_patterns (parallel with Node 2) ─────────────── #
    def detect_patterns_node(state: TechnicalState) -> Dict[str, Any]:
        """Scan bars for chart breakout / breakdown patterns."""
        snapshot: RawTechnicalSnapshot = state["snapshot"]
        pattern_signals, warnings = detect_all_patterns(snapshot.bars)

        # Convert PatternSignal objects to dicts for state serialisation,
        # but keep the originals available via a helper when evaluate needs them.
        pattern_dicts = [
            {
                "pattern_name": p.pattern_name,
                "direction": p.direction,
                "confidence": p.confidence,
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat(),
                "breakout_confirmed": p.breakout_confirmed,
                "volume_confirmation": p.volume_confirmation,
                "description": p.description,
                # Keep the frozen dataclass around for the rules engine
                "_signal_obj": p,
            }
            for p in pattern_signals
        ]

        return {"patterns": pattern_dicts, "pattern_warnings": warnings}

    # ── Node 4: evaluate ───────────────────────────────────────────── #
    def evaluate_node(state: TechnicalState) -> Dict[str, Any]:
        """Run all 9 scoring frameworks, composite score, and reliability check."""
        snapshot: RawTechnicalSnapshot = state["snapshot"]
        indicators = state["indicators"]
        pattern_dicts = state.get("patterns", [])

        # Recover PatternSignal objects for the rules engine
        pattern_signals: List[PatternSignal] = []
        for pd in pattern_dicts:
            obj = pd.get("_signal_obj")
            if isinstance(obj, PatternSignal):
                pattern_signals.append(obj)

        evaluation = evaluate_snapshot(snapshot, indicators, pattern_signals)

        # Low-volume / small-cap reliability check (Task 4)
        closes = [b.close for b in snapshot.bars]
        volumes = [b.volume for b in snapshot.bars]
        reliability = validate_stock_reliability(
            closes, volumes, snapshot.request.ticker,
        )
        evaluation = apply_reliability_adjustments(evaluation, reliability)

        # Append any pattern-detection warnings
        pw = state.get("pattern_warnings", [])
        if pw:
            evaluation["warnings"] = evaluation.get("warnings", []) + pw

        return {"evaluation": evaluation}

    # ── Node 5: render ─────────────────────────────────────────────── #
    def render_node(state: TechnicalState) -> Dict[str, Any]:
        """Generate the human-readable text report."""
        evaluation = dict(state["evaluation"])
        evaluation["report"] = build_text_report(evaluation)
        return {"evaluation": evaluation}

    # ── Wire the graph ─────────────────────────────────────────────── #
    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("compute_indicators", compute_indicators_node)
    graph.add_node("detect_patterns", detect_patterns_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("render", render_node)

    # Fan-out from fetch_data to both compute_indicators and detect_patterns
    graph.add_edge(START, "fetch_data")
    graph.add_edge("fetch_data", "compute_indicators")
    graph.add_edge("fetch_data", "detect_patterns")

    # Fan-in: evaluate waits for both
    graph.add_edge("compute_indicators", "evaluate")
    graph.add_edge("detect_patterns", "evaluate")

    graph.add_edge("evaluate", "render")
    graph.add_edge("render", END)

    return graph.compile()
