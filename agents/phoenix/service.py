"""
service.py — Public API for the Phoenix Agent.

This is the single entry point for any caller (scripts, orchestrator,
backtest engine, tests) that wants a Phoenix analysis for one ticker.

Usage::
    from agents.phoenix.service import analyze_ticker

    result = analyze_ticker("CRWD", "2026-04-30")
    print(result["signal"])     # "BUY" / "WATCH" / "AVOID"
    print(result["score"])      # 0–100
    print(result["report"])     # human-readable text
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, Optional

from .config import PhoenixSettings
from .data_client import PhoenixDataClient
from .graph import build_graph
from .models import PhoenixRequest, PhoenixSignal

logger = logging.getLogger(__name__)

# Module-level shared client (avoids re-creating HTTP session per call)
_shared_client: Optional[PhoenixDataClient] = None


def _get_client() -> PhoenixDataClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = PhoenixDataClient()
    return _shared_client


def analyze_ticker(
    ticker: str,
    as_of_date: Optional[str] = None,
    settings: Optional[PhoenixSettings] = None,
    account_size: float = 100_000,
) -> Dict[str, Any]:
    """
    Full Phoenix Trader analysis for a single ticker at a cutoff date.

    Parameters
    ----------
    ticker:       Stock symbol (case-insensitive).
    as_of_date:   ISO date string (YYYY-MM-DD).  Defaults to today if None.
    settings:     PhoenixSettings; uses defaults (2× vol, strict Stage 2) if None.
    account_size: Account value in dollars used for position sizing.

    Returns
    -------
    Dict with keys:
        ticker, as_of_date, signal, score, score_breakdown,
        stage, pattern, entry, risk,
        hard_filter_passed, hard_filter_reason,
        report, warnings
    """
    ticker = ticker.upper()
    cfg    = settings or PhoenixSettings()

    # Resolve date
    if as_of_date is None:
        as_of = date.today()
    else:
        as_of = date.fromisoformat(as_of_date) if isinstance(as_of_date, str) else as_of_date

    request = PhoenixRequest(ticker=ticker, as_of_date=as_of)

    # Build and run the LangGraph pipeline
    compiled = build_graph(client=_get_client(), settings=cfg)
    try:
        state = compiled.invoke({
            "request":      request,
            "settings":     cfg,
            "account_size": account_size,
            "warnings":     [],
        })
    except Exception as exc:
        logger.error("Phoenix pipeline failed for %s: %s", ticker, exc, exc_info=True)
        return _error_result(ticker, as_of, str(exc))

    sig: PhoenixSignal = state.get("phoenix_signal")
    if sig is None:
        return _error_result(ticker, as_of, "Pipeline produced no output.")

    return _signal_to_dict(sig)


def _signal_to_dict(sig: PhoenixSignal) -> Dict[str, Any]:
    """Serialise a PhoenixSignal to a plain dict (JSON-safe)."""
    stage_dict = {
        "stage":        sig.stage.stage,
        "label":        sig.stage.label,
        "action":       sig.stage.action,
        "ma_alignment": sig.stage.ma_alignment,
        "ma_slopes":    sig.stage.ma_slopes,
        "notes":        sig.stage.notes,
    } if sig.stage else {}

    pattern_dict: Optional[Dict] = None
    if sig.pattern and sig.pattern.pattern_name != "None":
        pattern_dict = {
            "pattern_name":    sig.pattern.pattern_name,
            "confirmed":       sig.pattern.confirmed,
            "volume_confirmed":sig.pattern.volume_confirmed,
            "pivot_price":     sig.pattern.pivot_price,
            "confidence":      sig.pattern.confidence,
            "vcp_contractions":sig.pattern.vcp_contractions,
            "base_depth_pct":  sig.pattern.base_depth_pct,
            "description":     sig.pattern.description,
        }

    entry_dict: Optional[Dict] = None
    if sig.entry and sig.entry.entry_type != "none":
        entry_dict = {
            "entry_type":          sig.entry.entry_type,
            "entry_price":         sig.entry.entry_price,
            "trigger_description": sig.entry.trigger_description,
        }

    risk_dict: Optional[Dict] = None
    if sig.risk:
        risk_dict = {
            "stop_price":           sig.risk.stop_price,
            "stop_pct":             sig.risk.stop_pct,
            "target_1":             sig.risk.target_1,
            "target_2":             sig.risk.target_2,
            "reward_risk":          sig.risk.reward_risk,
            "position_size_shares": sig.risk.position_size_shares,
            "trail_stop_ma":        sig.risk.trail_stop_ma,
        }

    # Stable, UI-friendly snapshot (entry / targets / pattern). exit_price is unknown until a position closes.
    pat_name = (
        sig.pattern.pattern_name
        if sig.pattern
        else "None"
    )
    trade_levels = {
        "entry_price":    entry_dict.get("entry_price") if entry_dict else None,
        "target_1":       risk_dict.get("target_1") if risk_dict else None,
        "target_2":       risk_dict.get("target_2") if risk_dict else None,
        "stop_price":     risk_dict.get("stop_price") if risk_dict else None,
        "exit_price":     None,
        "pattern_name":   pat_name,
        "pattern_breakout": bool(sig.pattern.confirmed) if sig.pattern else False,
        "notes": (
            "exit_price is null for screening runs; populate after backtest or execution merge."
        ),
    }

    ext = sig.extension_guardrail

    return {
        "ticker":              sig.ticker,
        "as_of_date":          sig.as_of_date.isoformat(),
        "signal":              sig.signal,
        "score":               sig.score,
        "score_breakdown":     sig.score_breakdown,
        "stage":               stage_dict,
        "pattern":             pattern_dict,
        "entry":               entry_dict,
        "risk":                risk_dict,
        "trade_levels":        trade_levels,
        "extension_guardrail": ext,
        "hard_filter_passed":  sig.hard_filter_passed,
        "hard_filter_reason":  sig.hard_filter_reason,
        "report":              sig.report,
        "warnings":            sig.warnings,
    }


def _error_result(ticker: str, as_of: date, error_msg: str) -> Dict[str, Any]:
    return {
        "ticker":             ticker,
        "as_of_date":         as_of.isoformat(),
        "signal":             "AVOID",
        "score":              0.0,
        "score_breakdown":    {},
        "stage":              None,
        "pattern":            None,
        "entry":              None,
        "risk":               None,
        "trade_levels":       {
            "entry_price": None,
            "target_1": None,
            "target_2": None,
            "stop_price": None,
            "exit_price": None,
            "pattern_name": "None",
            "pattern_breakout": False,
            "notes": error_msg,
        },
        "extension_guardrail": None,
        "hard_filter_passed": False,
        "hard_filter_reason": error_msg,
        "report":             f"Phoenix Agent error for {ticker}: {error_msg}",
        "warnings":           [error_msg],
    }
