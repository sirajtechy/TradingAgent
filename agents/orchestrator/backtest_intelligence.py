"""Intelligence agent evaluation for labeled backtests (PIT-gated)."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, Optional, Tuple

from core.evaluation.pit_policy import agent_pit_status

from .config import OrchestratorSettings
from .fusion_full import fuse_signals_full

logger = logging.getLogger(__name__)

_SESSION_AGENTS = ("macro", "market_summary", "geopolitics")
_TICKER_AGENTS = ("news", "insider", "sentiment")
_SESSION_CACHE: Dict[str, Dict[str, Any]] = {}


def _safe_envelope(agent_id: str, *, ticker: str, as_of_date: str, **kwargs: Any) -> Tuple[Optional[Dict], Optional[Dict], Optional[str]]:
    pit = agent_pit_status(agent_id, as_of_date)
    if not pit.get("allowed"):
        return None, None, pit.get("reason")
    try:
        from agents._registry import analyze_and_envelope

        native, envelope = analyze_and_envelope(
            agent_id,
            ticker=ticker,
            as_of_date=as_of_date,
            **kwargs,
        )
        return native, envelope, None
    except Exception as exc:
        logger.warning("Intelligence agent %s failed for %s: %s", agent_id, ticker, exc)
        return None, None, str(exc)


def load_session_agents(as_of_date: str) -> Dict[str, Dict[str, Any]]:
    if as_of_date in _SESSION_CACHE:
        return _SESSION_CACHE[as_of_date]
    agents: Dict[str, Dict[str, Any]] = {}
    for aid in _SESSION_AGENTS:
        native, envelope, err = _safe_envelope(aid, ticker="", as_of_date=as_of_date)
        agents[aid] = {"native": native, "envelope": envelope, "error": err, "pit": agent_pit_status(aid, as_of_date)}
    _SESSION_CACHE[as_of_date] = agents
    return agents


def evaluate_intelligence_layer(
    *,
    ticker: str,
    signal_date: date,
    phoenix_result: Optional[Dict[str, Any]],
    fund_result: Optional[Dict[str, Any]],
    technical_result: Optional[Dict[str, Any]],
    settings: Optional[OrchestratorSettings] = None,
) -> Dict[str, Any]:
    """
    Run PIT-gated intelligence agents and fusion_full for one backtest period.

    Returns signal fields + pit_manifest fragment for the period row.
    """
    cfg = settings or OrchestratorSettings()
    as_of = signal_date.isoformat()
    session = load_session_agents(as_of)

    agents: Dict[str, Any] = {
        "technical": {"native": technical_result, "envelope": None},
        "phoenix": {"native": phoenix_result, "envelope": None},
        "fundamental": {"native": fund_result, "envelope": None},
    }
    agents.update(session)

    for aid in _TICKER_AGENTS:
        native, envelope, err = _safe_envelope(aid, ticker=ticker, as_of_date=as_of)
        agents[aid] = {"native": native, "envelope": envelope, "error": err, "pit": agent_pit_status(aid, as_of)}

    agent_envelopes: Dict[str, Dict[str, Any]] = {}
    for aid, bundle in agents.items():
        env = (bundle or {}).get("envelope")
        if env:
            agent_envelopes[aid] = env

    ms_native = (agents.get("market_summary") or {}).get("native")

    fusion = fuse_signals_full(
        phoenix_result=phoenix_result or {},
        fund_result=fund_result or {},
        agent_envelopes=agent_envelopes,
        market_summary_native=ms_native,
        settings=cfg,
    )

    out: Dict[str, Any] = {
        "fusion_full_signal": fusion.final_signal,
        "fusion_full_score": fusion.orchestrator_score,
        "intelligence_pit": {
            aid: (agents.get(aid) or {}).get("pit") or agent_pit_status(aid, as_of)
            for aid in (*_SESSION_AGENTS, *_TICKER_AGENTS, "fusion_full")
        },
    }

    for aid in ("macro", "news", "insider", "sentiment", "geopolitics"):
        env = agent_envelopes.get(aid)
        out[f"{aid}_signal"] = (env or {}).get("signal") or "neutral"

    return out


def apply_intelligence_correctness(period: Dict[str, Any], target_eval: Dict[str, Any]) -> None:
    """Add signal_correct_* for intelligence agents to period dict in place."""
    from agents.orchestrator.backtest_phoenix import _correctness_for_signal

    mapping = {
        "signal_correct_fusion_full": "fusion_full_signal",
        "signal_correct_macro": "macro_signal",
        "signal_correct_news": "news_signal",
        "signal_correct_insider": "insider_signal",
        "signal_correct_sentiment": "sentiment_signal",
        "signal_correct_geopolitics": "geopolitics_signal",
    }
    for corr_key, sig_key in mapping.items():
        period[corr_key] = _correctness_for_signal(period.get(sig_key), target_eval)
