"""Richard Moglen — setup pack classification."""

from __future__ import annotations

from typing import Any, Dict, List

from agents.strategies.common.features import gap_pct, snapshot_bars
from agents.strategies.common.models import StrategyContext


def classify_setup(ctx: StrategyContext) -> Dict[str, Any]:
    phoenix = ctx.phoenix_result or {}
    pattern = phoenix.get("pattern") or {}
    bars = snapshot_bars(ctx.snapshot)
    gap = gap_pct(bars) if bars else None
    name = pattern.get("pattern_name") or "None"

    setup_type = "none"
    notes: List[str] = []

    if gap is not None and gap >= 5.0:
        setup_type = "super_gap" if gap >= 10.0 else "earnings_gap_up"
        notes.append(f"Gap up {gap:+.1f}% on signal bar.")
    elif name == "VCP" and pattern.get("confirmed"):
        setup_type = "vcp_base_breakout"
        notes.append("VCP base breakout confirmed.")
    elif name == "Flat Base":
        setup_type = "range_breakout"
        notes.append("Flat base / range breakout structure.")
    elif name == "Tight Flag":
        setup_type = "range_breakout"
        notes.append("Tight flag continuation.")
    elif name in ("Shakeout", "Pullback"):
        setup_type = "reversal_mean_reversion"
        notes.append(f"{name} mean-reversion style setup.")
    elif len(bars) < 150 and name != "None":
        setup_type = "ipo_base"
        notes.append("Shorter history — IPO-style base candidate.")

    detected = setup_type != "none"
    return {
        "setup_detected": detected,
        "setup_type": setup_type,
        "gap_pct": gap,
        "pattern_name": name,
        "notes": notes,
    }
