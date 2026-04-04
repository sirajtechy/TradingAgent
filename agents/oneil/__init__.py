"""
oneil_agent — William O'Neil CAN SLIM Technical Analysis Agent.

Primary timeframe : Weekly  (pattern formation, stage analysis)
Secondary timeframe: Daily  (entry precision, 200-day EMA)

Public API
----------
    from oneil_agent import analyze_ticker

    signal = analyze_ticker("AAPL")
    print(signal.to_dict())
"""

from .service import analyze_ticker
from .models import ONeilSignal, ONeilRequest

__all__ = ["analyze_ticker", "ONeilSignal", "ONeilRequest"]
