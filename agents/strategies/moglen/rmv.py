"""Richard Moglen — RMV tightness wrapper."""

from __future__ import annotations

from agents.strategies.common.features import compute_rmv, snapshot_bars
from agents.strategies.common.models import StrategyContext


def evaluate_rmv(ctx: StrategyContext, *, period: int = 15) -> dict:
    bars = snapshot_bars(ctx.snapshot)
    rmv15 = compute_rmv(bars, period=15)
    rmv5 = compute_rmv(bars, period=5) if len(bars) >= 10 else None

    tight = rmv15 is not None and rmv15 <= 35.0
    return {
        "rmv15": rmv15,
        "rmv5": rmv5,
        "tight_right_side": tight,
        "period_default": period,
        "notes": [
            f"RMV15={rmv15} (0=tight, 100=expanded)." if rmv15 is not None else "RMV unavailable.",
        ],
    }
