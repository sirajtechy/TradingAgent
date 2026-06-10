from __future__ import annotations

from typing import Any, Dict


def build_text_report(evaluation: Dict[str, Any]) -> str:
    metrics = evaluation.get("metrics") or {}
    lines = [
        "Macroeconomics Agent — 1-month swing backdrop",
        f"As of: {metrics.get('as_of_date', 'n/a')}",
        f"Signal: {evaluation.get('signal')} | Score: {evaluation.get('score')} | Band: {evaluation.get('band')}",
        "",
    ]
    for bullet in evaluation.get("bullets") or []:
        lines.append(bullet)
    if evaluation.get("warnings"):
        lines.append("")
        lines.append("Warnings:")
        for w in evaluation["warnings"]:
            lines.append(f"  - {w}")
    return "\n".join(lines)
