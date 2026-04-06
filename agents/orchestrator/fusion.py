"""
fusion.py — Confidence-Weighted Asymmetric Fusion (CWAF) engine.

Implements the full decision tree from ORCHESTRATOR_DESIGN.md §4.2:
  1. Error handling (Layer 0)
  2. Agreement cases (Layer 1)
  3. Single-agent directional (Layer 2)
  4. Conflict cases (Layer 3)
  5. Anti-bullish guardrails (§4.4)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import OrchestratorSettings
from .models import AgentOutput, BAND_TO_SIGNAL, FusionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def agent_confidence(score: float, band_thresholds: List[float]) -> float:
    """Return 0.0–1.0 confidence based on distance from nearest band boundary.

    Scores deep inside a band → high confidence.
    Scores near a boundary → low confidence.
    """
    boundaries = sorted(band_thresholds)
    min_distance = min(abs(score - b) for b in boundaries)
    max_possible = 25.0  # half of the widest band
    return min(min_distance / max_possible, 1.0)


def _extract_tech_output(
    eval_dict: Dict[str, Any],
    thresholds: List[float],
) -> AgentOutput:
    """Normalise a technical agent evaluation dict into an AgentOutput.

    Note: Technical agent stores its composite score under the key
    ``experimental_score`` (same key name as fundamental agent).
    """
    cs = eval_dict.get("experimental_score", {})
    if not cs or not cs.get("available"):
        return AgentOutput(
            signal="neutral",
            score=50.0,
            band="mixed",
            confidence="low",
            computed_confidence=0.0,
        )

    score = float(cs["score"])
    band = cs["band"]
    conf_label = cs.get("confidence", "medium")
    signal = BAND_TO_SIGNAL.get(band, "neutral")
    computed = agent_confidence(score, thresholds)

    # Extract ADX confidence from the score dict or key_indicators
    adx_conf = cs.get("adx_confidence") or eval_dict.get(
        "key_indicators", {}
    ).get("adx_confidence")

    return AgentOutput(
        signal=signal,
        score=score,
        band=band,
        confidence=conf_label,
        computed_confidence=computed,
        subscores=cs.get("subscores", {}),
        adx_confidence=adx_conf,
    )


def _extract_fund_output(
    eval_dict: Dict[str, Any],
    thresholds: List[float],
) -> AgentOutput:
    """Normalise a fundamental agent evaluation dict into an AgentOutput."""
    es = eval_dict.get("experimental_score", {})
    if not es or not es.get("available"):
        return AgentOutput(
            signal="neutral",
            score=50.0,
            band="mixed",
            confidence="low",
            computed_confidence=0.0,
        )

    score = float(es["score"])
    band = es["band"]
    conf_label = es.get("confidence", "medium")
    signal = BAND_TO_SIGNAL.get(band, "neutral")
    computed = agent_confidence(score, thresholds)

    # Derive data quality from coverage
    dq = eval_dict.get("data_quality", {})
    coverage = dq.get("coverage_ratio", 1.0) if dq else 1.0
    if coverage >= 0.8:
        quality = "good"
    elif coverage >= 0.5:
        quality = "fair"
    else:
        quality = "poor"

    return AgentOutput(
        signal=signal,
        score=score,
        band=band,
        confidence=conf_label,
        computed_confidence=computed,
        subscores=es.get("subscores", {}),
        data_quality=quality,
    )


# ---------------------------------------------------------------------------
# Main fusion function
# ---------------------------------------------------------------------------

def fuse_signals(
    tech_result: Optional[Dict[str, Any]] = None,
    tech_error: Optional[str] = None,
    fund_result: Optional[Dict[str, Any]] = None,
    fund_error: Optional[str] = None,
    settings: Optional[OrchestratorSettings] = None,
) -> FusionResult:
    """
    CWAF fusion — combine technical and fundamental signals.

    Implements the complete decision tree from ORCHESTRATOR_DESIGN.md §4.2
    plus anti-bullish guardrails from §4.4.
    """
    cfg = settings or OrchestratorSettings()
    w = cfg.weights

    # ── LAYER 0: Error handling ──────────────────────────────────────────
    if tech_error and fund_error:
        return FusionResult(
            final_signal="neutral",
            final_confidence=0.0,
            orchestrator_score=50.0,
            conflict_detected=False,
            conflict_resolution=None,
            weights_applied={"tech": 0.0, "fund": 0.0},
            tech_error=tech_error,
            fund_error=fund_error,
            note="Both agents failed",
        )

    # Extract normalised outputs where available
    tech_out: Optional[AgentOutput] = None
    fund_out: Optional[AgentOutput] = None

    if not tech_error and tech_result is not None:
        tech_out = _extract_tech_output(tech_result, cfg.tech_thresholds)

    if not fund_error and fund_result is not None:
        fund_out = _extract_fund_output(fund_result, cfg.fund_thresholds)

    # Single-agent fallbacks when one errored
    if tech_error:
        assert fund_out is not None
        return FusionResult(
            final_signal=fund_out.signal,
            final_confidence=fund_out.computed_confidence,
            orchestrator_score=fund_out.score,
            conflict_detected=False,
            conflict_resolution=None,
            weights_applied={"tech": 0.0, "fund": 1.0},
            fund_output=fund_out,
            tech_error=tech_error,
            note="Tech agent failed; FA only",
        )

    if fund_error:
        assert tech_out is not None
        return FusionResult(
            final_signal=tech_out.signal,
            final_confidence=tech_out.computed_confidence,
            orchestrator_score=tech_out.score,
            conflict_detected=False,
            conflict_resolution=None,
            weights_applied={"tech": 1.0, "fund": 0.0},
            tech_output=tech_out,
            fund_error=fund_error,
            note="Fund agent failed; TA only",
        )

    # Both agents produced results
    assert tech_out is not None and fund_out is not None
    ts, fs = tech_out.signal, fund_out.signal

    # ── LAYER 1: Agreement cases ─────────────────────────────────────────
    if ts == fs:
        if ts == "bullish":
            return _agreement_bull(tech_out, fund_out, cfg, w)
        elif ts == "bearish":
            return _agreement_bear(tech_out, fund_out, cfg, w)
        else:
            return _agreement_neutral(tech_out, fund_out, cfg, w)

    # ── LAYER 2: Single-agent directional (other is neutral) ─────────────
    if fs == "neutral":
        if ts == "bullish":
            return _tech_only_bull(tech_out, fund_out, cfg, w)
        else:
            return _tech_only_bear(tech_out, fund_out, cfg, w)

    if ts == "neutral":
        if fs == "bullish":
            return _fund_only_bull(tech_out, fund_out, cfg, w)
        else:
            return _fund_only_bear(tech_out, fund_out, cfg, w)

    # ── LAYER 3: Conflict (both directional, opposite directions) ────────
    return _conflict(tech_out, fund_out, cfg, w)


# ---------------------------------------------------------------------------
# Layer 1 — Agreement
# ---------------------------------------------------------------------------

def _agreement_bull(
    tech: AgentOutput, fund: AgentOutput,
    cfg: OrchestratorSettings, w: Any,
) -> FusionResult:
    wt, wf = w.agreement
    score = wt * tech.score + wf * fund.score
    conf = max(tech.computed_confidence, fund.computed_confidence)
    conf = min(conf * cfg.bullish_agreement_bonus, 1.0)
    signal, score = _apply_guardrails(
        "bullish", score, tech, fund, cfg,
    )
    return FusionResult(
        final_signal=signal,
        final_confidence=conf,
        orchestrator_score=round(score, 2),
        conflict_detected=False,
        conflict_resolution=None,
        weights_applied={"tech": wt, "fund": wf},
        tech_output=tech,
        fund_output=fund,
    )


def _agreement_bear(
    tech: AgentOutput, fund: AgentOutput,
    cfg: OrchestratorSettings, w: Any,
) -> FusionResult:
    wt, wf = w.agreement
    score = wt * tech.score + wf * fund.score
    conf = max(tech.computed_confidence, fund.computed_confidence)
    conf = min(conf * cfg.bearish_agreement_bonus, 1.0)
    signal = _score_to_signal(score, cfg)
    return FusionResult(
        final_signal=signal,
        final_confidence=conf,
        orchestrator_score=round(score, 2),
        conflict_detected=False,
        conflict_resolution=None,
        weights_applied={"tech": wt, "fund": wf},
        tech_output=tech,
        fund_output=fund,
    )


def _agreement_neutral(
    tech: AgentOutput, fund: AgentOutput,
    cfg: OrchestratorSettings, w: Any,
) -> FusionResult:
    wt, wf = w.agreement_neutral
    score = wt * tech.score + wf * fund.score
    return FusionResult(
        final_signal="neutral",
        final_confidence=cfg.agreement_neutral_confidence,
        orchestrator_score=round(score, 2),
        conflict_detected=False,
        conflict_resolution=None,
        weights_applied={"tech": wt, "fund": wf},
        tech_output=tech,
        fund_output=fund,
    )


# ---------------------------------------------------------------------------
# Layer 2 — Single-agent directional
# ---------------------------------------------------------------------------

def _tech_only_bull(
    tech: AgentOutput, fund: AgentOutput,
    cfg: OrchestratorSettings, w: Any,
) -> FusionResult:
    wt, wf = w.tech_only
    score = wt * tech.score + wf * fund.score
    conf = tech.computed_confidence * cfg.tech_only_discount
    if fund.data_quality == "poor":
        conf *= cfg.poor_data_quality_discount
    signal, score = _apply_guardrails("bullish", score, tech, fund, cfg)
    return FusionResult(
        final_signal=signal,
        final_confidence=round(conf, 4),
        orchestrator_score=round(score, 2),
        conflict_detected=False,
        conflict_resolution=None,
        weights_applied={"tech": wt, "fund": wf},
        tech_output=tech,
        fund_output=fund,
    )


def _tech_only_bear(
    tech: AgentOutput, fund: AgentOutput,
    cfg: OrchestratorSettings, w: Any,
) -> FusionResult:
    wt, wf = w.tech_only
    score = wt * tech.score + wf * fund.score
    conf = tech.computed_confidence * cfg.tech_only_discount
    signal = _score_to_signal(score, cfg)
    return FusionResult(
        final_signal=signal,
        final_confidence=round(conf, 4),
        orchestrator_score=round(score, 2),
        conflict_detected=False,
        conflict_resolution=None,
        weights_applied={"tech": wt, "fund": wf},
        tech_output=tech,
        fund_output=fund,
    )


def _fund_only_bull(
    tech: AgentOutput, fund: AgentOutput,
    cfg: OrchestratorSettings, w: Any,
) -> FusionResult:
    wt, wf = w.fund_only
    score = wt * tech.score + wf * fund.score
    conf = fund.computed_confidence * cfg.fund_only_discount
    signal, score = _apply_guardrails("bullish", score, tech, fund, cfg)
    return FusionResult(
        final_signal=signal,
        final_confidence=round(conf, 4),
        orchestrator_score=round(score, 2),
        conflict_detected=False,
        conflict_resolution=None,
        weights_applied={"tech": wt, "fund": wf},
        tech_output=tech,
        fund_output=fund,
    )


def _fund_only_bear(
    tech: AgentOutput, fund: AgentOutput,
    cfg: OrchestratorSettings, w: Any,
) -> FusionResult:
    wt, wf = w.fund_only
    score = wt * tech.score + wf * fund.score
    conf = fund.computed_confidence * cfg.fund_only_discount
    signal = _score_to_signal(score, cfg)
    return FusionResult(
        final_signal=signal,
        final_confidence=round(conf, 4),
        orchestrator_score=round(score, 2),
        conflict_detected=False,
        conflict_resolution=None,
        weights_applied={"tech": wt, "fund": wf},
        tech_output=tech,
        fund_output=fund,
    )


# ---------------------------------------------------------------------------
# Layer 3 — Conflict
# ---------------------------------------------------------------------------

def _conflict(
    tech: AgentOutput, fund: AgentOutput,
    cfg: OrchestratorSettings, w: Any,
) -> FusionResult:
    """Resolve Tech=B/Fund=R or Tech=R/Fund=B conflicts."""
    gap = cfg.conflict_confidence_gap
    tc = tech.computed_confidence
    fc = fund.computed_confidence

    # v4: Always use fixed tech-dominant weights for score blending.
    # The confidence winner still determines the signal direction,
    # but the orchestrator score is always 90% tech / 10% fund.
    wt, wf = 0.90, 0.10

    if fc > tc + gap:
        # Fund has higher confidence — adopt fund's signal direction
        score = wt * tech.score + wf * fund.score
        conf = fc * cfg.conflict_winner_discount_fa
        signal = fund.signal
        note = (
            f"Conflict: FA {fund.signal} (conf={fc:.2f}) overrides "
            f"TA {tech.signal} (conf={tc:.2f})"
        )
    elif tc > fc + gap:
        # Tech has higher confidence — adopt tech's signal direction
        score = wt * tech.score + wf * fund.score
        conf = tc * cfg.conflict_winner_discount_ta
        signal = tech.signal
        note = (
            f"Conflict: TA {tech.signal} (conf={tc:.2f}) overrides "
            f"FA {fund.signal} (conf={fc:.2f})"
        )
    else:
        # Near-equal → abstain
        score = wt * tech.score + wf * fund.score
        conf = cfg.conflict_abstain_confidence
        signal = "neutral"
        note = (
            f"Conflict: TA {tech.signal} vs FA {fund.signal} "
            f"with similar confidence → abstain"
        )

    # Apply guardrails to final signal
    signal_after, score = _apply_guardrails(signal, score, tech, fund, cfg)

    return FusionResult(
        final_signal=signal_after,
        final_confidence=round(conf, 4),
        orchestrator_score=round(score, 2),
        conflict_detected=True,
        conflict_resolution=note,
        weights_applied={"tech": wt, "fund": wf},
        tech_output=tech,
        fund_output=fund,
        note=note,
    )


# ---------------------------------------------------------------------------
# Guardrails & helpers
# ---------------------------------------------------------------------------

def _score_to_signal(score: float, cfg: OrchestratorSettings) -> str:
    """Map orchestrator score to final signal using tighter thresholds."""
    if score >= cfg.bullish_threshold:
        return "bullish"
    elif score < cfg.bearish_threshold:
        return "bearish"
    return "neutral"


def _apply_guardrails(
    proposed_signal: str,
    score: float,
    tech: AgentOutput,
    fund: AgentOutput,
    cfg: OrchestratorSettings,
) -> tuple:
    """
    Anti-bullish guardrails from §4.4:
    1. Score-based override (tighter orchestrator thresholds)
    2. Bullish Confirmation Requirement — weak-bullish tech + bearish fund → neutral
    """
    # Guardrail 2: Bullish Confirmation Requirement
    if (
        cfg.require_bullish_confirmation
        and proposed_signal == "bullish"
        and tech.band == "mixed_positive"
        and fund.signal == "bearish"
    ):
        return "neutral", score

    # Guardrail 1: Score-based final signal (overrides proposed if score disagrees)
    final_signal = _score_to_signal(score, cfg)

    # If the proposed signal was bearish but score says neutral or bullish,
    # trust the score — it aggregated both agents' scores.
    # If proposed was bullish and score < bullish_threshold → downgrade.
    return final_signal, score
