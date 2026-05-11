"""
fusion_phoenix.py — CWAF fusion using Phoenix + Fundamental.

This is a variant of :mod:`agents.orchestrator.fusion` where the
"technical" input is replaced by the Phoenix agent output.

We intentionally keep the same FusionResult schema:
  - weights_applied uses keys {"tech", "fund"} where "tech" == Phoenix weight (from
    ``OrchestratorSettings.phoenix_fund_weights``, default **90% Phoenix / 10% FA**).
  - tech_output in FusionResult is a normalized Phoenix output
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import OrchestratorSettings
from .fusion import (
    _agreement_bear,
    _agreement_bull,
    _agreement_neutral,
    _apply_guardrails,
    _conflict,
    _fund_only_bear,
    _fund_only_bull,
    _score_to_signal,
    _tech_only_bear,
    _tech_only_bull,
    agent_confidence,
)
from .models import AgentOutput, FusionResult


def _phoenix_band(score: float, thresholds: List[float]) -> str:
    """
    Approximate Phoenix score into the standard 5 bands.

    thresholds are the same style as OrchestratorSettings.tech_thresholds:
        [bearish_cut, neutral_mid, bullish_weak, bullish_strong]
    """
    t0, t1, t2, t3 = sorted(thresholds)
    if score >= t3:
        return "strong"
    if score >= t2:
        return "good"
    if score >= t1:
        return "mixed_positive"
    if score >= t0:
        return "mixed"
    return "weak"


def _extract_phoenix_output(
    phoenix_eval: Dict[str, Any],
    thresholds: List[float],
) -> AgentOutput:
    """
    Normalise a Phoenix analysis dict into an AgentOutput.

    Phoenix provides:
      - signal: BUY / WATCH / AVOID
      - score:  0–100
    """
    sig = str(phoenix_eval.get("signal") or "WATCH").upper()
    score = float(phoenix_eval.get("score") or 0.0)

    if sig == "BUY":
        signal = "bullish"
    elif sig == "AVOID":
        signal = "bearish"
    else:
        signal = "neutral"

    band = _phoenix_band(score, thresholds)
    computed = agent_confidence(score, thresholds)

    # Phoenix doesn't expose an explicit confidence label comparable to TA/FA
    # so keep a placeholder label but rely on computed_confidence.
    conf_label = "medium"

    return AgentOutput(
        signal=signal,
        score=score,
        band=band,
        confidence=conf_label,
        computed_confidence=computed,
        subscores=phoenix_eval.get("score_breakdown") or {},
        adx_confidence=None,
    )


def fuse_signals_phoenix(
    phoenix_result: Optional[Dict[str, Any]] = None,
    phoenix_error: Optional[str] = None,
    fund_result: Optional[Dict[str, Any]] = None,
    fund_error: Optional[str] = None,
    settings: Optional[OrchestratorSettings] = None,
) -> FusionResult:
    """
    CWAF fusion — combine Phoenix and Fundamental signals.
    """
    cfg = settings or OrchestratorSettings()
    # Phoenix slot uses cfg.weights slot names {"tech","fund"} but numeric blend is Phoenix-dominant.
    w = cfg.phoenix_fund_weights

    # Layer 0: Error handling
    if phoenix_error and fund_error:
        return FusionResult(
            final_signal="neutral",
            final_confidence=0.0,
            orchestrator_score=50.0,
            conflict_detected=False,
            conflict_resolution=None,
            weights_applied={"tech": 0.0, "fund": 0.0},
            tech_error=phoenix_error,
            fund_error=fund_error,
            note="Both agents failed (Phoenix + FA)",
        )

    px_out: Optional[AgentOutput] = None
    fund_out: Optional[AgentOutput] = None

    if not phoenix_error and phoenix_result is not None:
        px_out = _extract_phoenix_output(phoenix_result, cfg.tech_thresholds)

    if not fund_error and fund_result is not None:
        # reuse the standard extractor by importing from fusion lazily
        from .fusion import _extract_fund_output  # local import avoids circular
        fund_out = _extract_fund_output(fund_result, cfg.fund_thresholds)

    # Single-agent fallbacks
    if phoenix_error:
        assert fund_out is not None
        return FusionResult(
            final_signal=fund_out.signal,
            final_confidence=fund_out.computed_confidence,
            orchestrator_score=fund_out.score,
            conflict_detected=False,
            conflict_resolution=None,
            weights_applied={"tech": 0.0, "fund": 1.0},
            fund_output=fund_out,
            tech_error=phoenix_error,
            note="Phoenix failed; FA only",
        )

    if fund_error:
        assert px_out is not None
        return FusionResult(
            final_signal=px_out.signal,
            final_confidence=px_out.computed_confidence,
            orchestrator_score=px_out.score,
            conflict_detected=False,
            conflict_resolution=None,
            weights_applied={"tech": 1.0, "fund": 0.0},
            tech_output=px_out,
            fund_error=fund_error,
            note="Fund agent failed; Phoenix only",
        )

    assert px_out is not None and fund_out is not None
    ts, fs = px_out.signal, fund_out.signal

    # Agreement
    if ts == fs:
        if ts == "bullish":
            # guardrails still apply; uses band and fund signal.
            return _agreement_bull(px_out, fund_out, cfg, w)
        if ts == "bearish":
            return _agreement_bear(px_out, fund_out, cfg, w)
        return _agreement_neutral(px_out, fund_out, cfg, w)

    # Single-agent directional (other neutral)
    if fs == "neutral":
        if ts == "bullish":
            return _tech_only_bull(px_out, fund_out, cfg, w)
        return _tech_only_bear(px_out, fund_out, cfg, w)

    if ts == "neutral":
        if fs == "bullish":
            return _fund_only_bull(px_out, fund_out, cfg, w)
        return _fund_only_bear(px_out, fund_out, cfg, w)

    # Conflict
    return _conflict(px_out, fund_out, cfg, w)

