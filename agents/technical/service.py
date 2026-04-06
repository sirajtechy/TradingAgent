"""
service.py — Public entry-point for the technical analysis agent.

Callers use ``analyze_ticker()`` for a single-call interface that
constructs the request, wires the graph, and returns the evaluation dict.
``build_request()`` is also exported for callers who need to construct
the request separately (e.g. the backtest engine).
``predict_trade()`` routes through the orchestrator (CWAF fusion of
Technical + Fundamental agents) and returns a forward-looking trade
prediction.
"""

from datetime import date, datetime
from typing import Any, Dict, Optional

from .data_client import PolygonTechnicalClient
from .graph import build_graph
from .models import TechnicalRequest
from .predictor import build_trade_prediction


def build_request(
    ticker: str,
    as_of_date: Optional[str] = None,
) -> TechnicalRequest:
    """
    Construct a ``TechnicalRequest`` from raw string arguments.

    Args:
        ticker:      Stock ticker symbol (e.g. ``"AAPL"``).
        as_of_date:  ISO date string ``"YYYY-MM-DD"`` or ``None`` for today.

    Returns:
        Frozen ``TechnicalRequest`` dataclass.
    """
    resolved_date = (
        datetime.strptime(as_of_date, "%Y-%m-%d").date()
        if as_of_date
        else date.today()
    )
    return TechnicalRequest(
        ticker=ticker.upper(),
        as_of_date=resolved_date,
    )


def analyze_ticker(
    ticker: str,
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the full technical analysis pipeline on *ticker* as of *as_of_date*.

    This is the **single public function** that downstream code (CLI,
    backtest, web API) should call.

    Args:
        ticker:      Stock ticker symbol.
        as_of_date:  ISO date string or ``None`` for today.

    Returns:
        Evaluation dict containing frameworks, composite score, patterns,
        key indicators, and a text report.

    Raises:
        DataUnavailableError: if price data cannot be fetched.
        InsufficientDataError: if not enough bars for indicator computation.
    """
    request = build_request(ticker=ticker, as_of_date=as_of_date)
    client = PolygonTechnicalClient()
    graph = build_graph(client)
    state = graph.invoke({"request": request})
    return state["evaluation"]


def predict_trade(
    ticker: str,
    cutoff_date: Optional[str] = None,
    target_days: int = 10,
) -> Dict[str, Any]:
    """
    Run the full analysis through the **orchestrator** (which fuses Technical
    + Fundamental agents via CWAF) and produce a forward-looking LONG trade
    prediction.

    Args:
        ticker:       Stock ticker symbol (e.g. ``"AAPL"``).
        cutoff_date:  ISO date string ``"YYYY-MM-DD"`` or ``None`` for today.
                      All data used is **prior** to this date.
                      Entry = next trading day.
        target_days:  Maximum prediction window in trading days (3–30).

    Returns:
        Prediction dict with: trade_entry_date, trade_exit_date,
        confidence_score, sentiment, trade_entry_price, trade_exit_price,
        trade_profit_pct, patterns_formed, stop_loss_price,
        exhaustion_date, orchestrator context (tech/fund scores, fusion
        weights, conflict info).
    """
    # Resolve cutoff date — default to today
    if cutoff_date:
        resolved = datetime.strptime(cutoff_date, "%Y-%m-%d").date()
    else:
        resolved = date.today()
    cutoff_str = resolved.isoformat()

    # Step 1: Run ORCHESTRATOR — it internally runs both TA + FA, fuses via CWAF
    from agents.orchestrator.service import analyze_ticker as orchestrator_analyze
    orch_result = orchestrator_analyze(ticker=ticker, as_of_date=cutoff_str)

    # Step 2: Run the technical graph directly so we can extract BOTH the
    # full evaluation dict AND the raw bars (snapshot.bars) needed for
    # walk-forward exit simulation.  analyze_ticker() discards the snapshot.
    request = build_request(ticker=ticker, as_of_date=cutoff_str)
    client = PolygonTechnicalClient()
    graph = build_graph(client)
    state = graph.invoke({"request": request})
    tech_evaluation = state["evaluation"]
    bars = state["snapshot"].bars  # List[OHLCVBar], sorted oldest-first

    # Step 3: Build pattern-driven prediction with walk-forward exit simulation
    prediction = build_trade_prediction(
        orchestrator_result=orch_result,
        tech_evaluation=tech_evaluation,
        cutoff_date=resolved,
        target_days=target_days,
        bars=bars,
    )

    # Attach ticker
    prediction["ticker"] = ticker.upper()

    return prediction
