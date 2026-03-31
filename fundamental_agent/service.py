from datetime import date, datetime
from typing import Any, Dict, Optional

from .config import load_settings
from .fmp_client import FMPClient
from .graph import build_graph
from .models import AnalysisRequest
from .yf_client import YFinanceClient


def build_request(
    ticker: str,
    as_of_date: Optional[str] = None,
    shariah_standard: str = "aaoifi",
    include_experimental_score: bool = True,
) -> AnalysisRequest:
    resolved_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else date.today()
    return AnalysisRequest(
        ticker=ticker.upper(),
        as_of_date=resolved_date,
        shariah_standard=shariah_standard,
        include_experimental_score=include_experimental_score,
    )


def analyze_ticker(
    ticker: str,
    as_of_date: Optional[str] = None,
    shariah_standard: str = "aaoifi",
    include_experimental_score: bool = True,
    api_key: Optional[str] = None,
    data_source: str = "fmp",
) -> Dict[str, Any]:
    request = build_request(
        ticker=ticker,
        as_of_date=as_of_date,
        shariah_standard=shariah_standard,
        include_experimental_score=include_experimental_score,
    )
    if data_source == "yfinance":
        client = YFinanceClient()
    else:
        settings = load_settings(api_key=api_key)
        client = FMPClient(settings=settings)
    graph = build_graph(client)
    state = graph.invoke({"request": request})
    return state["evaluation"]
