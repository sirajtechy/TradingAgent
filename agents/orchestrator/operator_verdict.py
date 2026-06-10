"""Map fused orchestrator output to operator-facing STRONG BUY / HOLD / SELL."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import OrchestratorSettings
from .models import AgentOutput, FusionResult


def map_operator_verdict(
    *,
    phoenix_native: Dict[str, Any],
    fusion: FusionResult,
    context_outputs: Optional[Dict[str, AgentOutput]] = None,
    settings: Optional[OrchestratorSettings] = None,
) -> Tuple[str, List[str]]:
    """
    Deterministic operator label from Phoenix signal + fused score + context agents.

    Returns (verdict, reasons) where verdict is STRONG BUY | HOLD | SELL.
    """
    cfg = settings or OrchestratorSettings()
    ctx = context_outputs or fusion.context_outputs or {}

    px_sig = str(phoenix_native.get("signal") or "WATCH").upper()
    chase = (phoenix_native.get("extension_guardrail") or {}).get("chase_risk")
    reasons: List[str] = []

    macro = ctx.get("macro")
    geo = ctx.get("geopolitics")
    news = ctx.get("news")
    insider = ctx.get("insider")

    if px_sig == "AVOID" or fusion.final_signal == "bearish":
        reasons.append(f"Phoenix {px_sig}" if px_sig == "AVOID" else "Fusion bearish")
        if news and news.signal == "bearish":
            reasons.append("News bearish")
        if insider and insider.signal == "bearish":
            reasons.append("Insider bearish")
        return "SELL", reasons or ["Bearish overlay"]

    if fusion.conflict_detected:
        reasons.append("Fusion conflict detected")

    if chase == "high":
        reasons.append("High chase risk")

    if macro and macro.signal == "bearish":
        reasons.append("Macro bearish headwind")
    if geo and geo.signal == "bearish":
        reasons.append("Geopolitical risk elevated")

    strong_buy_ok = (
        px_sig == "BUY"
        and fusion.final_signal == "bullish"
        and fusion.orchestrator_score >= cfg.strong_buy_min_score
        and chase != "high"
        and not fusion.conflict_detected
        and (macro is None or macro.signal != "bearish")
        and (geo is None or geo.signal != "bearish")
        and (news is None or news.signal != "bearish")
        and (insider is None or insider.signal != "bearish")
    )

    if strong_buy_ok:
        reasons = [
            f"Phoenix BUY (score {phoenix_native.get('score')})",
            f"Fusion bullish ({fusion.orchestrator_score})",
        ]
        if news and news.signal == "bullish":
            reasons.append("News confirms")
        if insider and insider.signal == "bullish":
            reasons.append("Insider confirms")
        return "STRONG BUY", reasons

    if px_sig == "WATCH":
        reasons.insert(0, f"Phoenix WATCH (score {phoenix_native.get('score')})")
    elif px_sig == "BUY":
        reasons.insert(0, f"Phoenix BUY — mixed intelligence ({fusion.orchestrator_score})")
    else:
        reasons.insert(0, "Mixed signals")

    return "HOLD", reasons
