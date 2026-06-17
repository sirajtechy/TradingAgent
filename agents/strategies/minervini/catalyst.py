"""Minervini catalyst score from fundamental growth data."""

from __future__ import annotations

from typing import Any, Dict, List


def evaluate_catalyst(fund_result: dict | None) -> Dict[str, Any]:
    if not fund_result:
        return {"applicable": False, "score": 0.0, "notes": ["No fundamental data for catalyst check."]}

    growth = (fund_result.get("frameworks") or {}).get("growth_profile") or {}
    exp = fund_result.get("experimental_score") or {}
    notes: List[str] = []
    score = 40.0

    rev = growth.get("revenue_yoy_growth_pct")
    eps_q = growth.get("eps_qoq_growth_pct")
    eps_y = growth.get("eps_yoy_growth_pct")

    if rev is not None and rev >= 20:
        score += 20.0
        notes.append(f"Revenue YoY growth {rev:.1f}%.")
    elif rev is not None and rev > 0:
        score += 10.0
        notes.append(f"Revenue YoY growth {rev:.1f}% (moderate).")

    if eps_q is not None and eps_q > 0:
        score += 15.0
        notes.append("Recent quarter EPS growth positive.")
    if eps_y is not None and eps_y > 0:
        score += 15.0
        notes.append("Annual EPS growth positive.")

    if exp.get("band") in ("good", "excellent", "mixed_positive"):
        score += 10.0
        notes.append(f"FA band: {exp.get('band')}.")

    return {
        "applicable": True,
        "score": round(min(score, 100.0), 1),
        "notes": notes or ["Limited growth catalyst data."],
    }
