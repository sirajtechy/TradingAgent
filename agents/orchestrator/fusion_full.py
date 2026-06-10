"""
fusion_full.py — Multi-agent CWAF for full-context fusion mode.

Combines Phoenix, Fundamental, and intelligence agents via weighted score blend
with abstain renormalization and market_summary regime overlay.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import OrchestratorSettings
from .envelope_adapter import envelope_to_agent_output
from .fusion import _score_to_signal, agent_confidence
from .fusion_phoenix import _extract_phoenix_output
from .models import AgentOutput, FusionResult
from .operator_verdict import map_operator_verdict


def _apply_regime_overlay(
    score: float,
    signal: str,
    market_summary_native: Optional[Dict[str, Any]],
    cfg: OrchestratorSettings,
) -> Tuple[float, str, Optional[str]]:
    """Cap bullish scores when market regime is risk-off or VIX is extreme."""
    if not market_summary_native:
        return score, signal, None

    regime = str(market_summary_native.get("market_wide_signal") or "")
    vix_regime = str(market_summary_native.get("vix_regime") or "")
    note_parts = []

    if vix_regime in ("extreme", "elevated") or regime in ("risk_off", "caution"):
        note_parts.append(f"Regime {regime or vix_regime}")
        if signal == "bullish" and score > cfg.regime_vix_cap_score:
            score = cfg.regime_vix_cap_score
            signal = _score_to_signal(score, cfg)

    market_regime = regime or vix_regime or None
    note = "; ".join(note_parts) if note_parts else None
    return round(score, 2), signal, market_regime


def _detect_conflict(slots: Dict[str, AgentOutput]) -> Tuple[bool, Optional[str]]:
    """True when Phoenix bullish conflicts with bearish macro or geopolitics."""
    px = slots.get("phoenix")
    if not px or px.signal != "bullish":
        return False, None

    conflicts = []
    for key in ("macro", "geopolitics", "news", "insider"):
        out = slots.get(key)
        if out and out.signal == "bearish":
            conflicts.append(key)

    if not conflicts:
        return False, None
    return True, f"Phoenix bullish vs bearish: {', '.join(conflicts)}"


def fuse_signals_full(
    *,
    phoenix_result: Dict[str, Any],
    fund_result: Dict[str, Any],
    agent_envelopes: Dict[str, Dict[str, Any]],
    market_summary_native: Optional[Dict[str, Any]] = None,
    phoenix_error: Optional[str] = None,
    fund_error: Optional[str] = None,
    settings: Optional[OrchestratorSettings] = None,
) -> FusionResult:
    """
    Weighted multi-agent fusion. Envelopes must include at least phoenix + fundamental
    when available; optional keys: macro, news, insider, geopolitics.
    """
    cfg = settings or OrchestratorSettings()
    base_weights = dict(cfg.full_context_weights)

    if phoenix_error and fund_error:
        return FusionResult(
            final_signal="neutral",
            final_confidence=0.0,
            orchestrator_score=50.0,
            conflict_detected=False,
            conflict_resolution=None,
            weights_applied={},
            tech_error=phoenix_error,
            fund_error=fund_error,
            note="Both Phoenix and FA failed",
            agent_envelopes=agent_envelopes,
        )

    slots: Dict[str, AgentOutput] = {}
    abstain_keys: set = set()

    if not phoenix_error and phoenix_result is not None:
        slots["phoenix"] = _extract_phoenix_output(phoenix_result, cfg.tech_thresholds)
        env = agent_envelopes.get("phoenix") or {}
        if env.get("abstain"):
            abstain_keys.add("phoenix")
    elif phoenix_error:
        abstain_keys.add("phoenix")

    if not fund_error and fund_result is not None:
        from .fusion import _extract_fund_output

        slots["fundamental"] = _extract_fund_output(fund_result, cfg.fund_thresholds)
        env = agent_envelopes.get("fundamental") or {}
        if env.get("abstain"):
            abstain_keys.add("fundamental")
    elif fund_error:
        abstain_keys.add("fundamental")

    for key in ("macro", "news", "insider", "geopolitics"):
        env = agent_envelopes.get(key)
        if not env:
            abstain_keys.add(key)
            continue
        if env.get("abstain"):
            abstain_keys.add(key)
            continue
        slots[key] = envelope_to_agent_output(env, thresholds=cfg.tech_thresholds)

    active_weights: Dict[str, float] = {}
    for key, weight in base_weights.items():
        if key in abstain_keys or key not in slots:
            continue
        active_weights[key] = weight

    if not active_weights:
        return FusionResult(
            final_signal="neutral",
            final_confidence=0.0,
            orchestrator_score=50.0,
            conflict_detected=False,
            conflict_resolution=None,
            weights_applied={},
            note="No agent outputs available",
            agent_envelopes=agent_envelopes,
        )

    total_w = sum(active_weights.values())
    norm_weights = {k: v / total_w for k, v in active_weights.items()}

    score = sum(norm_weights[k] * slots[k].score for k in norm_weights)
    conf = sum(
        norm_weights[k] * slots[k].computed_confidence for k in norm_weights
    ) / max(len(norm_weights), 1)

    signal = _score_to_signal(score, cfg)
    conflict, conflict_note = _detect_conflict(slots)

    score, signal, market_regime = _apply_regime_overlay(
        score, signal, market_summary_native, cfg,
    )

    context_outputs = {
        k: v for k, v in slots.items() if k not in ("phoenix", "fundamental")
    }

    px_out = slots.get("phoenix")
    fund_out = slots.get("fundamental")

    weights_applied = dict(norm_weights)
    if px_out:
        weights_applied["tech"] = norm_weights.get("phoenix", 0.0)
    if fund_out:
        weights_applied["fund"] = norm_weights.get("fundamental", 0.0)

    fusion = FusionResult(
        final_signal=signal,
        final_confidence=round(min(conf, 1.0), 4),
        orchestrator_score=round(score, 2),
        conflict_detected=conflict,
        conflict_resolution=conflict_note,
        weights_applied=weights_applied,
        tech_output=px_out,
        fund_output=fund_out,
        tech_error=phoenix_error,
        fund_error=fund_error,
        note=conflict_note,
        context_outputs=context_outputs,
        agent_envelopes=agent_envelopes,
        market_regime=market_regime,
    )

    verdict, reasons = map_operator_verdict(
        phoenix_native=phoenix_result or {},
        fusion=fusion,
        context_outputs=context_outputs,
        settings=cfg,
    )

    return FusionResult(
        final_signal=fusion.final_signal,
        final_confidence=fusion.final_confidence,
        orchestrator_score=fusion.orchestrator_score,
        conflict_detected=fusion.conflict_detected,
        conflict_resolution=fusion.conflict_resolution,
        weights_applied=fusion.weights_applied,
        tech_output=fusion.tech_output,
        fund_output=fusion.fund_output,
        tech_error=fusion.tech_error,
        fund_error=fusion.fund_error,
        note=fusion.note,
        context_outputs=fusion.context_outputs,
        operator_verdict=verdict,
        operator_reasons=tuple(reasons),
        agent_envelopes=fusion.agent_envelopes,
        market_regime=fusion.market_regime,
        summary=fusion.summary,
    )
