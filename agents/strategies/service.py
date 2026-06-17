"""Public API for trader strategy intelligence layer."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from agents.phoenix.data_client import PhoenixDataClient
from agents.phoenix.service import analyze_ticker as phoenix_analyze

from .common.models import StrategyContext
from .common.registry import run_strategies
from .fusion import build_meta_signals

logger = logging.getLogger(__name__)

_client: Optional[PhoenixDataClient] = None


def _get_client() -> PhoenixDataClient:
    global _client
    if _client is None:
        _client = PhoenixDataClient()
    return _client


def build_context(
    *,
    ticker: str,
    as_of_date: str,
    phoenix_result: Optional[Dict[str, Any]] = None,
    fund_result: Optional[Dict[str, Any]] = None,
    fetch_market_data: bool = True,
) -> StrategyContext:
    ticker = ticker.upper()
    warnings: list[str] = []
    snapshot = None
    spy_snapshot = None

    if fetch_market_data:
        client = _get_client()
        try:
            snapshot = client.build_snapshot(ticker, as_of_date)
        except Exception as exc:
            logger.warning("Strategy snapshot failed for %s: %s", ticker, exc)
            warnings.append(f"Ticker snapshot unavailable: {exc}")
        try:
            spy_snapshot = client.build_snapshot("SPY", as_of_date)
        except Exception as exc:
            logger.warning("SPY snapshot failed: %s", exc)
            warnings.append(f"SPY snapshot unavailable: {exc}")

    if phoenix_result is None and snapshot is not None:
        try:
            phoenix_result = phoenix_analyze(ticker=ticker, as_of_date=as_of_date)
        except Exception as exc:
            warnings.append(f"Phoenix analyze failed: {exc}")

    return StrategyContext(
        ticker=ticker,
        as_of_date=as_of_date,
        snapshot=snapshot,
        spy_snapshot=spy_snapshot,
        phoenix_result=phoenix_result,
        fund_result=fund_result,
        warnings=warnings,
    )


def analyze_strategies(
    *,
    ticker: str,
    as_of_date: str,
    profile: str = "blend",
    phoenix_result: Optional[Dict[str, Any]] = None,
    fund_result: Optional[Dict[str, Any]] = None,
    fetch_market_data: bool = True,
) -> Dict[str, Any]:
    """
    Run one or more trader strategy modules.

    profile: none | minervini | moglen | breitstein | mcintosh | blend | all
    """
    ctx = build_context(
        ticker=ticker,
        as_of_date=as_of_date,
        phoenix_result=phoenix_result,
        fund_result=fund_result,
        fetch_market_data=fetch_market_data,
    )
    layers = run_strategies(ctx, profile)
    meta = build_meta_signals(layers) if layers else {}
    return {
        "ok": True,
        "ticker": ctx.ticker,
        "as_of_date": as_of_date,
        "strategy_profile": profile,
        "layers": layers,
        "meta_signals": meta,
        "warnings": ctx.warnings,
    }
