from __future__ import annotations

from typing import Any, Dict


def build_text_report(evaluation: Dict[str, Any]) -> str:
    lines = [
        "News Analyst Agent — ticker headline + analyst activity",
        f"Signal: {evaluation.get('signal')} | Score: {evaluation.get('score')} | Band: {evaluation.get('band')}",
        "",
    ]
    for bullet in evaluation.get("bullets") or []:
        lines.append(bullet)
    pa = evaluation.get("priority_actions") or []
    if pa:
        lines.append("")
        lines.append("Priority analyst actions:")
        for a in pa:
            lines.append(f"  - {a['firm']}: {a['action']} → {a['grade']} ({a['date']})")
    if evaluation.get("warnings"):
        lines.append("")
        for w in evaluation["warnings"]:
            lines.append(f"  Warning: {w}")
    return "\n".join(lines)
