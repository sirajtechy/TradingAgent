"""
service.py — Public entry-point for the O'Neil Technical Analysis Agent.

This is the only module callers need to import.  Everything else is an
implementation detail.

Quick-start::

    from oneil_agent import analyze_ticker

    signal = analyze_ticker("AAPL")
    print(signal.summary)

    # For orchestrator consumption:
    import json
    print(json.dumps(signal.to_dict(), indent=2))

    # NSE stocks (India):
    signal = analyze_ticker("RELIANCE", exchange="NSE")

Raises
------
DataError
    If market data cannot be fetched after retries (network / bad ticker).
ValueError
    If *ticker* is blank.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from .data_client import DataError  # re-export for callers
from .graph import build_graph
from .models import ONeilRequest, ONeilSignal


# Compile the graph once at module import time.
# LangGraph compilation is cheap but repeated compilation would waste cycles
# when analyze_ticker is called in a loop (e.g. batch screener).
_GRAPH = None


def _get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def analyze_ticker(
    ticker: str,
    as_of_date: Optional[date] = None,
    exchange: str = "US",
) -> ONeilSignal:
    """
    Run the full O'Neil CAN SLIM technical analysis pipeline for *ticker*.

    Parameters
    ----------
    ticker : str
        US or NSE ticker symbol (e.g. "AAPL", "NVDA", "RELIANCE").
    as_of_date : date, optional
        Analyse as if today were this date.  Defaults to today's date.
        Useful for backtesting or point-in-time analysis.
    exchange : str
        "US" (default) for NASDAQ/NYSE, "NSE" for Indian exchange stocks.

    Returns
    -------
    ONeilSignal
        Fully populated signal object.  Call ``.to_dict()`` for JSON output.

    Raises
    ------
    ValueError
        If *ticker* is blank.
    DataError
        If data cannot be fetched from Yahoo Finance.
    """
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("ticker must not be empty")

    as_of = as_of_date or date.today()
    request = ONeilRequest(ticker=ticker, as_of_date=as_of, exchange=exchange)

    graph = _get_graph()
    final_state = graph.invoke({"request": request})
    return final_state["signal"]


__all__ = ["analyze_ticker", "ONeilSignal", "ONeilRequest", "DataError"]
