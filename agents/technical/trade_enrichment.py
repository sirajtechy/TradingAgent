"""
trade_enrichment.py — Fill Phoenix trade_levels + extension for backtest / Pilot export.

When Phoenix exits early (hard filter fail, recovery upgrade), risk and extension
nodes never run — so master_pilot rows lack stop, targets, 5d/4w extension.
Phoenix Pilot expects the full column set (entry, exit, stop, T1, T2, upside,
5d %, 4w %). This module back-fills those fields from snapshot bars only (no
lookahead).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from agents.phoenix.config import PhoenixSettings
from agents.phoenix.extension import compute_extension_guardrail
from agents.phoenix.models import PhoenixSnapshot

_RECOVERY_STOP_PCT = 7.5
_RECOVERY_T1_PCT = 15.0
_RECOVERY_T2_PCT = 25.0


def enrich_phoenix_for_export(
    phoenix_result: Dict[str, Any],
    snapshot: Optional[PhoenixSnapshot],
) -> Dict[str, Any]:
    """
    Ensure ``trade_levels`` and ``extension_guardrail`` are populated for
    dashboard / master_pilot export. Safe to call on every analyze_technical run.
    """
    if not isinstance(phoenix_result, dict):
        return phoenix_result

    result = deepcopy(phoenix_result)
    if snapshot is None:
        return result

    if not result.get("extension_guardrail"):
        result["extension_guardrail"] = compute_extension_guardrail(
            snapshot,
            None,
            PhoenixSettings(),
        )

    entry = float(snapshot.as_of_price or 0.0)
    if entry <= 0:
        return result

    tl: Dict[str, Any] = dict(result.get("trade_levels") or {})
    risk: Dict[str, Any] = dict(result.get("risk") or {})

    if tl.get("entry_price") is None:
        tl["entry_price"] = round(entry, 2)

    missing_stop = tl.get("stop_price") is None and risk.get("stop_price") is None
    missing_targets = tl.get("target_1") is None and tl.get("target_2") is None

    recovery = result.get("phoenix_entry_mode") == "recovery_upgrade"
    early_exit = not bool(result.get("hard_filter_passed"))
    needs_estimate = (recovery or early_exit) and (missing_stop or missing_targets)

    if needs_estimate:
        stop = round(entry * (1.0 - _RECOVERY_STOP_PCT / 100.0), 2)
        t1 = round(entry * (1.0 + _RECOVERY_T1_PCT / 100.0), 2)
        t2 = round(entry * (1.0 + _RECOVERY_T2_PCT / 100.0), 2)
        if missing_stop:
            tl["stop_price"] = stop
            risk.setdefault("stop_price", stop)
            risk.setdefault("stop_pct", _RECOVERY_STOP_PCT)
        if missing_targets:
            tl["target_1"] = t1
            tl["target_2"] = t2
            risk.setdefault("target_1", t1)
            risk.setdefault("target_2", t2)
        tl["notes"] = (
            "Estimated recovery-mode levels (7.5% stop, +15% / +25% targets) — "
            "Phoenix risk node did not run on hard-filter exit."
        )
        result["risk"] = risk
        result["trade_levels"] = tl
    elif tl:
        result["trade_levels"] = tl

    return result
