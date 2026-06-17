"""Minervini chase / extension guard (wraps Phoenix extension when available)."""

from __future__ import annotations

from typing import Any, Dict, List


def evaluate_chase_guard(phoenix_result: dict) -> Dict[str, Any]:
    ext = phoenix_result.get("extension_guardrail")
    if ext:
        chase_risk = ext.get("chase_risk", "unknown")
        metrics = ext.get("metrics") or {}
        from_pivot = metrics.get("pct_from_pivot")
        invalid = from_pivot is not None and from_pivot > 5.0
        penalty = 0.0
        if chase_risk == "elevated":
            penalty = 35.0
        elif chase_risk == "moderate":
            penalty = 15.0
        return {
            "applicable": True,
            "chase_risk": chase_risk,
            "pct_from_pivot": from_pivot,
            "invalid_if_chasing": invalid,
            "penalty": penalty,
            "flags": list(ext.get("flags") or []),
            "summary": ext.get("summary"),
        }

    pattern = phoenix_result.get("pattern") or {}
    entry = phoenix_result.get("entry") or {}
    pivot = pattern.get("pivot_price")
    entry_price = entry.get("entry_price")
    if pivot and entry_price and pivot > 0:
        pct = (entry_price - pivot) / pivot * 100.0
        invalid = pct > 5.0
        return {
            "applicable": True,
            "chase_risk": "moderate" if invalid else "low",
            "pct_from_pivot": round(pct, 2),
            "invalid_if_chasing": invalid,
            "penalty": 20.0 if invalid else 0.0,
            "flags": ["extended_from_pivot"] if invalid else [],
            "summary": f"Pivot distance {pct:+.1f}%.",
        }

    return {
        "applicable": False,
        "chase_risk": "unknown",
        "invalid_if_chasing": False,
        "penalty": 0.0,
        "flags": [],
        "summary": "No pivot/extension data.",
    }
