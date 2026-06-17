"""Market-wide regime features (Moglen / McIntosh context)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.phoenix.models import PhoenixSnapshot

from .features import ema_at, ema_trend_grid, slope_rising, snapshot_bars


def evaluate_market_regime(
    index_snapshot: Optional[PhoenixSnapshot],
    *,
    index_symbol: str = "SPY",
) -> Dict[str, Any]:
    """
    Regime-first guard: constructive when index is above rising 21 EMA.

    Returns regime_ok, aggression_score (0–100), and EMA grid metadata.
    """
    bars = snapshot_bars(index_snapshot)
    if len(bars) < 25:
        return {
            "index_symbol": index_symbol,
            "regime_ok": False,
            "aggression_score": 0.0,
            "data_quality": "unavailable",
            "warnings": ["Insufficient index bar history for regime check."],
            "grid": {},
        }

    price = bars[-1].close
    ema21 = ema_at(bars, 21)
    ema21_prior = ema_at(bars, 21, offset=5)
    above_21 = ema21 is not None and price > ema21
    rising_21 = slope_rising(ema21, ema21_prior)
    up, total, grid = ema_trend_grid(bars)

    regime_ok = bool(above_21 and rising_21)
    aggression = 0.0
    if regime_ok:
        aggression = 55.0
        if up >= 3:
            aggression += 15.0
        if up == total and total >= 3:
            aggression += 15.0
        if rising_21:
            aggression += 10.0
    else:
        aggression = max(10.0, up / max(total, 1) * 40.0)

    warnings = []
    if not above_21:
        warnings.append(f"{index_symbol} below 21 EMA — reduce new long aggression.")
    if not rising_21:
        warnings.append(f"{index_symbol} 21 EMA not rising — chop/correction risk.")

    return {
        "index_symbol": index_symbol,
        "regime_ok": regime_ok,
        "aggression_score": round(min(aggression, 100.0), 1),
        "price": round(price, 2),
        "ema21": round(ema21, 2) if ema21 else None,
        "above_21ema": above_21,
        "ema21_rising": rising_21,
        "trend_grid_up": up,
        "trend_grid_total": total,
        "grid": grid,
        "data_quality": "good",
        "warnings": warnings,
    }
