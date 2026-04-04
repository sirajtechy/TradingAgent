"""
service.py — Public entry-point for the technical analysis agent.

Callers use ``analyze_ticker()`` for a single-call interface that
constructs the request, wires the graph, and returns the evaluation dict.
``build_request()`` is also exported for callers who need to construct
the request separately (e.g. the backtest engine).
"""

from datetime import date, datetime
from typing import Any, Dict, Optional

from .data_client import PolygonTechnicalClient
from .graph import build_graph
from .models import TechnicalRequest


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
