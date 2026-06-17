"""Richard Moglen — market regime guard."""

from __future__ import annotations

from agents.strategies.common.market_regime import evaluate_market_regime
from agents.strategies.common.models import StrategyContext


def evaluate_regime(ctx: StrategyContext) -> dict:
    snap = ctx.spy_snapshot
    symbol = "SPY"
    if snap is None:
        return evaluate_market_regime(None, index_symbol=symbol)
    return evaluate_market_regime(snap, index_symbol=symbol)
