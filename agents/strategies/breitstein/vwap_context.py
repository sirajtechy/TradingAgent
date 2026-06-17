"""Lance Breitstein — daily VWAP context (intraday proxy)."""

from __future__ import annotations

from typing import List

from agents.strategies.common.features import daily_vwap_proxy, snapshot_bars
from agents.strategies.common.models import StrategyContext


def evaluate_vwap_context(ctx: StrategyContext) -> dict:
    bars = snapshot_bars(ctx.snapshot)
    if len(bars) < 20:
        return {
            "applicable": False,
            "above_vwap": None,
            "steadily_below": None,
            "notes": ["Insufficient bars for VWAP proxy."],
        }

    vwap = daily_vwap_proxy(bars, 20)
    price = bars[-1].close
    above = vwap is not None and price > vwap

    below_streak = 0
    for i in range(max(0, len(bars) - 5), len(bars)):
        v = daily_vwap_proxy(bars[: i + 1], 20)
        if v and bars[i].close < v:
            below_streak += 1
    steadily_below = below_streak >= 4

    return {
        "applicable": True,
        "vwap_proxy_20d": round(vwap, 2) if vwap else None,
        "price": round(price, 2),
        "above_vwap": above,
        "steadily_below_vwap": steadily_below,
        "notes": [
            "Daily VWAP proxy — upgrade with intraday bars for Breitstein-grade timing.",
            f"Price {'above' if above else 'below'} 20d VWAP proxy.",
        ],
    }
