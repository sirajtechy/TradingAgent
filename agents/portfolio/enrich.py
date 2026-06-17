"""Optional agent enrichment for top-ranked candidates (live / allocate / backtest)."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

INTELLIGENCE_AGENT_KEYS = ("macro", "news", "insider", "sentiment", "geopolitics")

_log_lock = threading.Lock()


def _intelligence_consensus(context_outputs: Dict[str, Any]) -> float:
    """Average score from intelligence agent slots (0–100)."""
    scores: List[float] = []
    for key in INTELLIGENCE_AGENT_KEYS:
        out = context_outputs.get(key)
        if out is None:
            continue
        sc = getattr(out, "score", None)
        if sc is None and isinstance(out, dict):
            sc = out.get("score")
        if sc is not None:
            scores.append(float(sc))
    if not scores:
        return 50.0
    return round(sum(scores) / len(scores), 2)


def _enrich_one_phoenix_fa(
    sym: str,
    as_of_date: str,
    *,
    strategy_profile: str,
) -> Optional[Dict[str, float]]:
    """Phoenix + FA + strategy layers only (faster)."""
    from agents.fundamental.service import analyze_ticker as fund_analyze
    from agents.orchestrator.fusion_phoenix import fuse_signals_phoenix
    from agents.phoenix.service import analyze_ticker as phoenix_analyze
    from agents.strategies.service import analyze_strategies

    phx = phoenix_analyze(ticker=sym, as_of_date=as_of_date)
    if (phx.get("signal") or "").upper() == "AVOID":
        return None
    fund = fund_analyze(ticker=sym, as_of_date=as_of_date)
    fused = fuse_signals_phoenix(phoenix_result=phx, fund_result=fund)
    strat = analyze_strategies(
        ticker=sym,
        as_of_date=as_of_date,
        profile=strategy_profile,
        phoenix_result=phx,
        fund_result=fund,
        fetch_market_data=False,
    )
    meta = (strat.get("meta") or {}) if isinstance(strat, dict) else {}
    return {
        "phoenix_fusion_score": float(fused.get("orchestrator_score") or 50.0),
        "strategy_blend_score": float(meta.get("blend_score") or 50.0),
        "intelligence_consensus": 50.0,
        "smoothness": 50.0,
        "phoenix_signal": str(phx.get("signal") or ""),
        "strategy_meta": meta,
    }


def _enrich_one_full(
    sym: str,
    as_of_date: str,
    *,
    strategy_profile: str,
) -> Optional[Dict[str, Any]]:
    """All agents: Phoenix, FA, macro, market_summary, news, insider, sentiment, geopolitics + strategies."""
    from agents.orchestrator.pipeline_full import run_full_analysis
    from agents.strategies.service import analyze_strategies

    doc = run_full_analysis(
        ticker=sym,
        as_of_date=as_of_date,
        include_llm_summary=False,
        human_decision_mode=True,
    )
    if not doc.get("ok"):
        return None

    phx = doc.get("phoenix") or {}
    if (phx.get("signal") or "").upper() == "AVOID":
        return None

    fusion = doc.get("fusion") or {}
    context = fusion.get("context_outputs") or {}

    strat = analyze_strategies(
        ticker=sym,
        as_of_date=as_of_date,
        profile=strategy_profile,
        phoenix_result=phx,
        fund_result=doc.get("fundamental"),
        fetch_market_data=False,
    )
    meta = (strat.get("meta") or {}) if isinstance(strat, dict) else {}

    intel = _intelligence_consensus(context)
    return {
        "phoenix_fusion_score": float(fusion.get("orchestrator_score") or 50.0),
        "strategy_blend_score": float(meta.get("blend_score") or 50.0),
        "intelligence_consensus": intel,
        "smoothness": 50.0,
        "phoenix_signal": str(phx.get("signal") or ""),
        "advisory_verdict": fusion.get("advisory_verdict"),
        "strategy_meta": meta,
        "agent_breakdown_keys": list((doc.get("agent_breakdown") or {}).keys()),
    }


def enrich_top_candidates(
    tickers: List[str],
    as_of_date: str,
    *,
    strategy_profile: str = "blend",
    max_tickers: int = 30,
    full_agents: bool = False,
    max_workers: int = 8,
) -> Dict[str, Dict[str, float]]:
    """
    Score top names with Phoenix + (optional) all intelligence agents + strategy layers.

    Session agents (macro, market_summary, geopolitics) are pre-warmed once per date
    before parallel ticker work. Returns ticker -> conviction subscores for portfolio rank blend.
    """
    subset = [sym for sym in tickers[:max_tickers] if sym]
    if not subset:
        return {}

    if full_agents:
        from agents.orchestrator.pipeline_full import load_or_run_session_context

        load_or_run_session_context(as_of_date)

    enrich_fn = _enrich_one_full if full_agents else _enrich_one_phoenix_fa
    workers = max(1, min(max_workers, len(subset)))
    out: Dict[str, Dict[str, float]] = {}

    def _run_one(sym: str) -> tuple[str, Optional[Dict[str, float]]]:
        row = enrich_fn(sym, as_of_date, strategy_profile=strategy_profile)
        return sym, row

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_one, sym): sym for sym in subset}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                _, row = fut.result()
                if row:
                    out[sym.upper()] = row
            except Exception as exc:
                with _log_lock:
                    logger.warning("enrich skip %s: %s", sym, exc)

    return out
