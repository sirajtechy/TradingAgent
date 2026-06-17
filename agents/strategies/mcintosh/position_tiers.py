"""Steve McIntosh — position sizing tiers."""

from __future__ import annotations

from typing import Dict


def map_position_tiers(
    *,
    leader_rank_score: float,
    entry_trigger: bool,
    phoenix_signal: str,
    market_regime_ok: bool,
) -> Dict[str, object]:
    if phoenix_signal not in ("BUY", "WATCH") or not market_regime_ok:
        return {
            "starter_pct": 0.0,
            "pyramid_pct": 0.0,
            "max_pct": 0.0,
            "pyramid_permission": False,
            "position_tier": "none",
        }

    if leader_rank_score >= 80 and entry_trigger:
        starter, pyramid, max_pct = 5.0, 12.0, 15.0
        tier = "full"
    elif leader_rank_score >= 65:
        starter, pyramid, max_pct = 4.0, 10.0, 12.0
        tier = "starter"
    elif leader_rank_score >= 50:
        starter, pyramid, max_pct = 3.0, 8.0, 10.0
        tier = "starter"
    else:
        starter, pyramid, max_pct = 0.0, 0.0, 0.0
        tier = "none"

    return {
        "starter_pct": starter,
        "pyramid_pct": pyramid,
        "max_pct": max_pct,
        "pyramid_permission": leader_rank_score >= 65 and phoenix_signal == "BUY",
        "position_tier": tier,
        "risk_per_trade_pct": 0.15,
    }
