"""Minervini VCP quality scoring from Phoenix pattern output."""

from __future__ import annotations

from typing import Any, Dict


def evaluate_vcp_quality(phoenix_result: dict) -> Dict[str, Any]:
    pattern = phoenix_result.get("pattern") or {}
    name = pattern.get("pattern_name") or "None"
    if name == "None":
        return {
            "applicable": False,
            "score": 0.0,
            "setup_detected": False,
            "notes": ["No qualifying Phoenix pattern."],
        }

    contractions = int(pattern.get("vcp_contractions") or 0)
    confidence = float(pattern.get("confidence") or 0.0)
    confirmed = bool(pattern.get("confirmed"))
    vol_ok = bool(pattern.get("volume_confirmed"))

    score = confidence * 60.0
    if name == "VCP":
        score += min(contractions, 3) * 10.0
    elif name in ("Flat Base", "Tight Flag"):
        score += 15.0
    if confirmed:
        score += 10.0
    if vol_ok:
        score += 10.0
    score = min(score, 100.0)

    return {
        "applicable": True,
        "score": round(score, 1),
        "setup_detected": True,
        "pattern_name": name,
        "confirmed": confirmed,
        "volume_confirmed": vol_ok,
        "vcp_contractions": contractions,
        "pivot_price": pattern.get("pivot_price"),
        "notes": [pattern.get("description") or f"{name} pattern detected."],
    }
