from __future__ import annotations

from typing import Any, Dict


def build_text_report(evaluation: Dict[str, Any]) -> str:
    lines = [
        "Sentiment Agent — multi-dimension composite",
        f"Signal: {evaluation.get('signal')} | Score: {evaluation.get('score')} | Sentiment: {evaluation.get('sentiment')}",
        "",
    ]
    for bullet in evaluation.get("bullets") or []:
        lines.append(bullet)
    dims = evaluation.get("dimensions") or {}
    if dims:
        lines.append("")
        lines.append("Dimension map:")
        for k, v in dims.items():
            lines.append(f"  {k}: {v}")
    if evaluation.get("warnings"):
        lines.append("")
        for w in evaluation["warnings"]:
            lines.append(f"  Warning: {w}")
    return "\n".join(lines)
