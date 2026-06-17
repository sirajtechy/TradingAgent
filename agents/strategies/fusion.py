"""Meta-signal fusion across trader strategy modules."""

from __future__ import annotations

from typing import Any, Dict, List


def build_meta_signals(strategies: Dict[str, dict]) -> Dict[str, Any]:
    """Derive composite meta-signals with attribution."""
    if not strategies:
        return {}

    minervini = strategies.get("minervini") or {}
    moglen = strategies.get("moglen") or {}
    breitstein = strategies.get("breitstein") or {}
    mcintosh = strategies.get("mcintosh") or {}

    meta: Dict[str, Any] = {}

    meta["high_conviction_swing"] = (
        minervini.get("entry_trigger")
        and moglen.get("regime_ok")
        and minervini.get("score", 0) >= 65
    )
    meta["gap_continuation"] = moglen.get("setup_type") in ("earnings_gap_up", "super_gap") and moglen.get(
        "setup_detected"
    )
    meta["late_stage_avoidance"] = (
        "Not Stage 2" in " ".join(minervini.get("disqualifiers") or [])
        or mcintosh.get("score", 100) < 45
    )
    meta["intraday_confirmation_needed"] = (
        minervini.get("signal") == "bullish"
        and not breitstein.get("entry_trigger")
        and breitstein.get("setup_type") == "timing_pending"
    )
    meta["concentration_candidate"] = mcintosh.get("entry_trigger") and moglen.get("regime_ok")

    attributions: List[str] = []
    for sid, sig in strategies.items():
        if sig.get("entry_trigger"):
            attributions.append(f"{sid}:{sig.get('setup_type')}")
    meta["active_attributions"] = attributions

    scores = [s.get("score", 0) for s in strategies.values() if s.get("score") is not None]
    meta["blend_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0

    triggers = sum(1 for s in strategies.values() if s.get("entry_trigger"))
    meta["consensus_entry_triggers"] = triggers
    meta["consensus_total"] = len(strategies)

    if triggers >= 3 and meta["high_conviction_swing"]:
        meta["blend_signal"] = "bullish"
    elif triggers >= 2:
        meta["blend_signal"] = "neutral"
    else:
        meta["blend_signal"] = "bearish"

    return meta
