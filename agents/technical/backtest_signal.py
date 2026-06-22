"""Backtest-only signal mapping (separate from live enrichment gate).

Live trading uses ``derive_technical_signal`` + PASS enrichment.
Historical evaluation can use looser profiles to measure Phoenix/strategy recall vs target-hit.
"""

from __future__ import annotations

from typing import Any, Dict

from .fusion import TechnicalFusion, derive_technical_signal

# enrichment_strict — parity with live Technical Agent (current default)
# phoenix_watch_bull — BUY/WATCH → bullish (captures WATCH winners; AVOID still bearish)
# phoenix_recall — BUY/WATCH → bullish, AVOID → neutral (FN=0 on bearish; missed TP on AVOID winners)
# phoenix_buy_only — only Phoenix BUY → bullish

BACKTEST_SIGNAL_PROFILES = frozenset(
    {
        "enrichment_strict",
        "phoenix_watch_bull",
        "phoenix_recall",
        "phoenix_buy_only",
    }
)


def derive_backtest_signal(
    phoenix: Dict[str, Any],
    fusion: TechnicalFusion,
    *,
    profile: str = "enrichment_strict",
) -> str:
    """Map Phoenix + fusion to bullish/bearish/neutral for labeled backtests."""
    prof = (profile or "enrichment_strict").strip().lower()
    if prof not in BACKTEST_SIGNAL_PROFILES:
        prof = "enrichment_strict"

    if prof == "enrichment_strict":
        return derive_technical_signal(phoenix, fusion)

    px = str(phoenix.get("signal") or "AVOID").upper()

    if prof == "phoenix_buy_only":
        if px == "BUY":
            return "bullish"
        if px == "AVOID":
            return "bearish"
        return "neutral"

    if prof == "phoenix_watch_bull":
        if px in ("BUY", "WATCH"):
            return "bullish"
        if px == "AVOID":
            return "bearish"
        return "neutral"

    if prof == "phoenix_recall":
        # Maximize TP from Phoenix actionable names; never bearish (FN=0 vs target-hit).
        if px in ("BUY", "WATCH"):
            return "bullish"
        return "neutral"

    return derive_technical_signal(phoenix, fusion)
