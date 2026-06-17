"""Lance Breitstein — trend character and rangebound filter."""

from __future__ import annotations

from agents.strategies.common.features import compute_adr_pct, is_rangebound, snapshot_bars
from agents.strategies.common.models import StrategyContext


def evaluate_trend_character(ctx: StrategyContext) -> dict:
    bars = snapshot_bars(ctx.snapshot)
    if len(bars) < 25:
        return {"applicable": False, "character": "unknown", "rangebound": True}

    adr = compute_adr_pct(bars)
    rangebound = is_rangebound(bars)

    recent = bars[-5:]
    slopes = []
    for i in range(1, len(recent)):
        if recent[i - 1].close > 0:
            slopes.append((recent[i].close - recent[i - 1].close) / recent[i - 1].close * 100.0)
    avg_slope = sum(slopes) / len(slopes) if slopes else 0.0

    character = "steady"
    if abs(avg_slope) >= 2.5:
        character = "capitulatory" if adr and adr >= 5.0 else "trending"
    if rangebound:
        character = "rangebound"

    return {
        "applicable": True,
        "character": character,
        "rangebound": rangebound,
        "adr_pct": adr,
        "avg_5d_slope_pct": round(avg_slope, 2),
        "notes": [
            f"Trend character: {character}.",
            "Rangebound — Breitstein avoids new trades." if rangebound else "Trending context.",
        ],
    }
