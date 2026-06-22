"""Technical fusion — PASS rules, resilience score, signal derivation."""

from __future__ import annotations

from typing import Any, Dict, List

from agents.strategies.fusion import build_meta_signals

from .models import TechnicalFusion


def compute_resilience_score(
    phoenix: Dict[str, Any],
    layers: Dict[str, Dict[str, Any]],
) -> float:
    """Weighted 0–100 resilience score (no lookahead)."""
    phoenix_score = float(phoenix.get("score") or 0.0)
    pattern = phoenix.get("pattern") or {}
    pattern_bonus = 10.0 if pattern.get("confirmed") and pattern.get("pattern_name") == "VCP" else 0.0
    phoenix_part = min(100.0, phoenix_score + pattern_bonus) * 0.30

    minervini = layers.get("minervini") or {}
    sub = minervini.get("subscores") or {}
    template_pass = float(sub.get("trend_template_pass_count") or 0.0)
    minervini_part = (template_pass / 10.0 * 100.0) * 0.20

    moglen = layers.get("moglen") or {}
    msub = moglen.get("subscores") or {}
    rmv15 = msub.get("rmv15")
    regime_ok = bool(moglen.get("regime_ok"))
    rmv_tight = max(0.0, 100.0 - float(rmv15)) if rmv15 is not None else 50.0
    moglen_part = (rmv_tight * 0.7 + (100.0 if regime_ok else 0.0) * 0.3) * 0.15

    mcintosh = layers.get("mcintosh") or {}
    mci_sub = mcintosh.get("subscores") or {}
    leader = float(mci_sub.get("fastest_horse_rank") or mcintosh.get("score") or 0.0)
    mcintosh_part = leader * 0.20

    ext = phoenix.get("extension_guardrail") or {}
    chase = ext.get("chase_risk", "unknown")
    if chase == "elevated":
        ext_part = 0.0
    elif chase == "moderate":
        ext_part = 50.0 * 0.15
    else:
        ext_part = 100.0 * 0.15

    return round(phoenix_part + minervini_part + moglen_part + mcintosh_part + ext_part, 2)


def _pass_fail_reason(
    *,
    hard_passed: bool,
    phoenix_sig: str,
    blend_signal: str,
    consensus: int,
    minervini_trigger: bool,
    moglen_regime: bool,
) -> str:
    if not hard_passed:
        return "Phoenix hard filters failed."
    if phoenix_sig not in ("BUY", "WATCH"):
        return f"Phoenix signal {phoenix_sig} — not eligible for enrichment."
    if blend_signal == "bearish":
        return "Strategy blend bearish — enrichment blocked."
    if consensus >= 2:
        return f"Phoenix {phoenix_sig} + {consensus}/4 entry triggers + blend {blend_signal}"
    if minervini_trigger and moglen_regime:
        return f"Phoenix {phoenix_sig} + Minervini entry + Moglen regime OK"
    return "Insufficient strategy consensus for enrichment gate."


def build_technical_fusion(
    phoenix: Dict[str, Any],
    layers: Dict[str, Dict[str, Any]],
) -> TechnicalFusion:
    """Combine strategy meta-signals with enrichment PASS rules."""
    meta = build_meta_signals(layers)
    hard_passed = bool(phoenix.get("hard_filter_passed"))
    phoenix_sig = str(phoenix.get("signal") or "AVOID").upper()
    blend_signal = str(meta.get("blend_signal") or "bearish")
    consensus = int(meta.get("consensus_entry_triggers") or 0)

    minervini = layers.get("minervini") or {}
    moglen = layers.get("moglen") or {}
    minervini_trigger = bool(minervini.get("entry_trigger"))
    moglen_regime = bool(moglen.get("regime_ok"))
    alt_pass = minervini_trigger and moglen_regime
    consensus_pass = consensus >= 2

    pass_enrichment = (
        hard_passed
        and phoenix_sig in ("BUY", "WATCH")
        and (consensus_pass or alt_pass)
        and (blend_signal != "bearish" or alt_pass)
    )

    resilience = compute_resilience_score(phoenix, layers)
    pass_reason = (
        _pass_fail_reason(
            hard_passed=hard_passed,
            phoenix_sig=phoenix_sig,
            blend_signal=blend_signal,
            consensus=consensus,
            minervini_trigger=minervini_trigger,
            moglen_regime=moglen_regime,
        )
        if pass_enrichment
        else "Enrichment gate closed: "
        + (
            "hard filters failed."
            if not hard_passed
            else (
                f"Phoenix {phoenix_sig} not eligible."
                if phoenix_sig not in ("BUY", "WATCH")
                else (
                    "strategy blend bearish."
                    if blend_signal == "bearish"
                    else "insufficient strategy consensus (need ≥2 triggers or Minervini+Moglen)."
                )
            )
        )
    )

    return TechnicalFusion(
        blend_signal=blend_signal,
        blend_score=float(meta.get("blend_score") or 0.0),
        consensus_entry_triggers=consensus,
        consensus_total=int(meta.get("consensus_total") or len(layers)),
        high_conviction_swing=bool(meta.get("high_conviction_swing")),
        resilience_score=resilience,
        pass_enrichment=pass_enrichment,
        pass_reason=pass_reason,
        meta={k: v for k, v in meta.items() if k not in {
            "blend_signal", "blend_score", "consensus_entry_triggers",
            "consensus_total", "high_conviction_swing",
        }},
    )


def derive_technical_signal(phoenix: Dict[str, Any], fusion: TechnicalFusion) -> str:
    """Map Phoenix + fusion to envelope signal."""
    if not phoenix.get("hard_filter_passed"):
        return "bearish"
    phoenix_sig = str(phoenix.get("signal") or "AVOID").upper()
    if phoenix_sig == "AVOID":
        return "bearish"
    if fusion.pass_enrichment:
        return "bullish"
    if phoenix_sig == "WATCH" or fusion.blend_signal == "neutral":
        return "neutral"
    return "bearish"


def derive_confidence(fusion: TechnicalFusion, phoenix: Dict[str, Any]) -> str:
    phoenix_sig = str(phoenix.get("signal") or "").upper()
    if fusion.pass_enrichment and fusion.resilience_score >= 70:
        return "high"
    if fusion.pass_enrichment or phoenix_sig == "BUY":
        return "medium"
    return "low"


def collect_disqualifiers(phoenix: Dict[str, Any], layers: Dict[str, Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    if not phoenix.get("hard_filter_passed"):
        reason = phoenix.get("hard_filter_reason")
        if reason:
            out.append(reason)
    for sid, layer in layers.items():
        for d in layer.get("disqualifiers") or []:
            out.append(f"{sid}: {d}")
    return out


def derive_score(fusion: TechnicalFusion, phoenix: Dict[str, Any]) -> float:
    phoenix_score = float(phoenix.get("score") or 0.0)
    return round((phoenix_score * 0.4 + fusion.resilience_score * 0.6), 2)


def derive_data_quality(phoenix: Dict[str, Any], layers: Dict[str, Dict[str, Any]]) -> str:
    if not phoenix.get("hard_filter_passed"):
        return "poor"
    qualities = [phoenix.get("data_quality")] if phoenix.get("data_quality") else []
    qualities.extend(layer.get("data_quality") for layer in layers.values())
    labels = [q for q in qualities if q]
    if not labels:
        return "good"
    if any(q == "partial" for q in labels):
        return "fair"
    if all(q == "good" for q in labels):
        return "good"
    return "fair"
