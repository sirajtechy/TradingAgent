"""
pipeline_full.py — Full-context orchestrator pipeline.

Runs ALL agents regardless of Phoenix BUY/WATCH/AVOID.
Human decision mode: complete per-agent breakdown; fusion is reference only.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.paths import ROOT

from .agent_breakdown import ALL_AGENT_IDS, build_agent_breakdown, build_deterministic_digest
from .config import OrchestratorSettings
from .fusion_full import fuse_signals_full

logger = logging.getLogger(__name__)

SESSION_AGENT_IDS = ("macro", "market_summary", "geopolitics")
TICKER_AGENT_IDS = ("news", "insider", "sentiment")

_CONTEXT_DIR = ROOT / "data" / "output" / "context"


def _safe_analyze(
    agent_id: str,
    *,
    ticker: str,
    as_of_date: str,
    **kwargs: Any,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
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
        logger.warning("Agent %s failed for %s: %s", agent_id, ticker or "session", exc)
        return None, None, str(exc)


def load_or_run_session_context(
    as_of_date: str,
    *,
    refresh: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Load session agents from cache or run inline."""
    _CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _CONTEXT_DIR / f"context_{as_of_date}.json"

    if cache_path.is_file() and not refresh:
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            agents = cached.get("agents") or {}
            if all(aid in agents for aid in SESSION_AGENT_IDS):
                stale = any(
                    (agents[aid].get("native") is None and agents[aid].get("error"))
                    for aid in SESSION_AGENT_IDS
                )
                if not stale:
                    return agents
        except (json.JSONDecodeError, OSError):
            pass

    agents: Dict[str, Dict[str, Any]] = {}
    for agent_id in SESSION_AGENT_IDS:
        native, envelope, err = _safe_analyze(agent_id, ticker="", as_of_date=as_of_date)
        agents[agent_id] = {
            "native": native,
            "envelope": envelope,
            "error": err,
        }

    payload = {"as_of_date": as_of_date, "agents": agents}
    try:
        cache_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write context cache: %s", exc)

    return agents


def run_full_analysis(
    *,
    ticker: str,
    as_of_date: str,
    fund_data_source: str = "yfinance",
    settings: Optional[OrchestratorSettings] = None,
    refresh_context: bool = False,
    include_llm_summary: bool = False,
    human_decision_mode: bool = True,
) -> Dict[str, Any]:
    """
    Full orchestrator analysis for one ticker.

    All agents run always. Output includes ``agent_breakdown`` for human review.
    ``fusion.advisory_verdict`` is reference only — not an auto trade decision.
    """
    cfg = settings or OrchestratorSettings(fund_data_source=fund_data_source)
    tk = ticker.strip().upper()

    px_native, px_env, px_err = _safe_analyze("phoenix", ticker=tk, as_of_date=as_of_date)
    fund_native, fund_env, fund_err = _safe_analyze(
        "fundamental",
        ticker=tk,
        as_of_date=as_of_date,
        data_source=cfg.fund_data_source,
    )

    if px_native is None and fund_native is None:
        return {
            "ok": False,
            "fusion_mode": "full",
            "ticker": tk,
            "as_of_date": as_of_date,
            "error": px_err or fund_err or "Phoenix and FA both failed",
        }

    session = load_or_run_session_context(as_of_date, refresh=refresh_context)

    agents: Dict[str, Any] = {
        "phoenix": {"native": px_native, "envelope": px_env, "error": px_err},
        "fundamental": {"native": fund_native, "envelope": fund_env, "error": fund_err},
    }

    for aid in SESSION_AGENT_IDS:
        bundle = session.get(aid) or {}
        agents[aid] = {
            "native": bundle.get("native"),
            "envelope": bundle.get("envelope"),
            "error": bundle.get("error"),
        }

    for aid in TICKER_AGENT_IDS:
        native, envelope, err = _safe_analyze(aid, ticker=tk, as_of_date=as_of_date)
        agents[aid] = {"native": native, "envelope": envelope, "error": err}

    agent_envelopes: Dict[str, Dict[str, Any]] = {}
    for aid, bundle in agents.items():
        env = (bundle or {}).get("envelope")
        if env:
            agent_envelopes[aid] = env

    ms_native = (agents.get("market_summary") or {}).get("native")

    fusion = fuse_signals_full(
        phoenix_result=px_native or {},
        fund_result=fund_native or {},
        agent_envelopes=agent_envelopes,
        market_summary_native=ms_native,
        phoenix_error=px_err,
        fund_error=fund_err,
        settings=cfg,
    )

    fusion_dict = dataclasses.asdict(fusion)
    advisory = fusion_dict.pop("operator_verdict", None)
    advisory_reasons = fusion_dict.pop("operator_reasons", ())
    fusion_dict["advisory_verdict"] = advisory
    fusion_dict["advisory_reasons"] = list(advisory_reasons)
    fusion_dict["decision_by"] = "human"
    fusion_dict["note"] = (
        "advisory_verdict is a reference blend only — your buy/hold/avoid decision "
        "should use agent_breakdown below."
    )

    breakdown = build_agent_breakdown(agents, ticker=tk, as_of_date=as_of_date)

    digest = build_deterministic_digest(
        ticker=tk,
        as_of_date=as_of_date,
        agents=agents,
        fusion=fusion_dict,
    )
    summary = digest["bullets"][0] if digest.get("bullets") else None

    if include_llm_summary:
        try:
            from agents._shared.llm_summary import generate_summary_safe

            llm = generate_summary_safe(
                agent_id="orchestrator_full",
                as_of_date=as_of_date,
                context=summary or "",
                instruction=(
                    f"Summarize all agent outputs for {tk} for a human trader. "
                    "Do not recommend a trade — present facts only."
                ),
            )
            if llm and llm.get("bullets"):
                summary = " ".join(str(b) for b in llm["bullets"][:3])
                digest = llm
        except Exception as exc:
            logger.warning("Optional LLM summary failed: %s", exc)

    fusion_dict["summary"] = summary

    return {
        "ok": True,
        "fusion_mode": "full",
        "human_decision_mode": human_decision_mode,
        "ticker": tk,
        "as_of_date": as_of_date,
        "phoenix": px_native,
        "fundamental": fund_native,
        "agents": agents,
        "agent_breakdown": breakdown,
        "research_digest": digest,
        "fusion": fusion_dict,
        "summary": summary,
        "all_agents_ran": True,
    }
