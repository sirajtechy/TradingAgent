from __future__ import annotations

from typing import Any, Dict


def build_text_report(evaluation: Dict[str, Any]) -> str:
    lines = [
        "Geopolitics Agent — global risk scanner",
        f"Signal: {evaluation.get('signal')} | Score: {evaluation.get('score')} | Band: {evaluation.get('band')}",
        f"Headlines scanned: {evaluation.get('total_scanned', 0)} | Geo-relevant: {evaluation.get('geo_headline_count', 0)}",
        "",
    ]
    for bullet in evaluation.get("bullets") or []:
        lines.append(bullet)
    exposure = evaluation.get("sector_exposure") or {}
    if exposure:
        lines.append("")
        lines.append("Sector exposure:")
        for sector, count in sorted(exposure.items(), key=lambda x: -x[1]):
            lines.append(f"  - {sector}: {count} hit(s)")
    if evaluation.get("warnings"):
        lines.append("")
        for w in evaluation["warnings"]:
            lines.append(f"  Warning: {w}")
    return "\n".join(lines)
