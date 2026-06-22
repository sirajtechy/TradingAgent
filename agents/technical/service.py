"""Unified Technical Agent — Phoenix hard filters + 4 strategy modules + fusion."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from agents.phoenix.data_client import PhoenixDataClient
from agents.phoenix.service import analyze_ticker as phoenix_analyze
from agents.strategies.service import analyze_strategies

from .fusion import (
    build_technical_fusion,
    collect_disqualifiers,
    derive_confidence,
    derive_data_quality,
    derive_score,
    derive_technical_signal,
)
from .models import TechnicalResult
from .recovery_upgrade import maybe_upgrade_phoenix
from .trade_enrichment import enrich_phoenix_for_export

logger = logging.getLogger(__name__)

_client: Optional[PhoenixDataClient] = None


def _get_client() -> PhoenixDataClient:
    global _client
    if _client is None:
        _client = PhoenixDataClient()
    return _client


def analyze_technical(
    *,
    ticker: str,
    as_of_date: str,
    strategy_profile: str = "blend",
    fund_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run Phoenix once, then strategy layers reusing Phoenix output and cached bars.

    Does not invoke enrichment agents (FA, macro, news, etc.).
    """
    ticker = ticker.upper()
    warnings: list[str] = []

    try:
        phoenix_result = phoenix_analyze(ticker=ticker, as_of_date=as_of_date)
    except Exception as exc:
        logger.error("Technical agent: Phoenix failed for %s: %s", ticker, exc)
        return _error_result(ticker, as_of_date, str(exc))

    if phoenix_result.get("error") or phoenix_result.get("signal") is None:
        err = phoenix_result.get("error") or "Phoenix returned no signal"
        return _error_result(ticker, as_of_date, err, phoenix=phoenix_result)

    client = _get_client()
    snapshot = None
    spy_snapshot = None
    try:
        snapshot = client.build_snapshot(ticker, as_of_date)
    except Exception as exc:
        warnings.append(f"Ticker snapshot unavailable for strategies: {exc}")
    try:
        spy_snapshot = client.build_snapshot("SPY", as_of_date)
    except Exception as exc:
        warnings.append(f"SPY snapshot unavailable for strategies: {exc}")

    # Phase 2: post-correction recovery pathway. If Phoenix said AVOID purely
    # because the standard trend gates failed, but the broad tape is in a
    # confirmed recovery AND this ticker shows a credible reclaim, upgrade
    # AVOID → WATCH so downstream strategies have a real signal to work with.
    # Phoenix internals are unchanged; this runs as a post-processing adapter.
    phoenix_result = maybe_upgrade_phoenix(phoenix_result, snapshot, spy_snapshot)
    phoenix_result = enrich_phoenix_for_export(phoenix_result, snapshot)

    try:
        strategy_out = analyze_strategies(
            ticker=ticker,
            as_of_date=as_of_date,
            profile=strategy_profile,
            phoenix_result=phoenix_result,
            fund_result=fund_result,
            fetch_market_data=False,
            snapshot=snapshot,
            spy_snapshot=spy_snapshot,
        )
    except Exception as exc:
        logger.warning("Technical agent: strategies failed for %s: %s", ticker, exc)
        warnings.append(f"Strategy layer failed: {exc}")
        strategy_out = {"layers": {}, "warnings": [str(exc)]}

    layers = strategy_out.get("layers") or {}
    warnings.extend(strategy_out.get("warnings") or [])

    fusion = build_technical_fusion(phoenix_result, layers)
    signal = derive_technical_signal(phoenix_result, fusion)
    score = derive_score(fusion, phoenix_result)
    confidence = derive_confidence(fusion, phoenix_result)
    disqualifiers = collect_disqualifiers(phoenix_result, layers)
    data_quality = derive_data_quality(phoenix_result, layers)

    result = TechnicalResult(
        ok=True,
        ticker=ticker,
        as_of_date=as_of_date,
        signal=signal,
        score=score,
        confidence=confidence,
        hard_gates_passed=bool(phoenix_result.get("hard_filter_passed")),
        hard_gate_reason=phoenix_result.get("hard_filter_reason"),
        phoenix=phoenix_result,
        strategy_layers=layers,
        strategy_profile=strategy_profile,
        technical_fusion=fusion,
        disqualifiers=disqualifiers,
        warnings=warnings,
        data_quality=data_quality,
    )
    return result.to_dict()


def _error_result(
    ticker: str,
    as_of_date: str,
    error: str,
    *,
    phoenix: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from .models import TechnicalFusion

    empty_fusion = TechnicalFusion(
        blend_signal="bearish",
        blend_score=0.0,
        consensus_entry_triggers=0,
        consensus_total=0,
        high_conviction_swing=False,
        resilience_score=0.0,
        pass_enrichment=False,
        pass_reason=error,
    )
    return TechnicalResult(
        ok=False,
        ticker=ticker.upper(),
        as_of_date=as_of_date,
        signal="bearish",
        score=0.0,
        confidence="low",
        hard_gates_passed=False,
        hard_gate_reason=phoenix.get("hard_filter_reason") if phoenix else None,
        phoenix=phoenix or {},
        strategy_layers={},
        strategy_profile="blend",
        technical_fusion=empty_fusion,
        disqualifiers=[error],
        warnings=[],
        data_quality="poor",
        error=error,
    ).to_dict()
