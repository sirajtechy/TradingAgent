from __future__ import annotations

from typing import Any, Dict


def build_text_report(evaluation: Dict[str, Any]) -> str:
    metrics = evaluation.get("metrics") or {}
    lines = [
        "Insider Trades Agent — insider buy/sell activity",
        f"Signal: {evaluation.get('signal')} | Score: {evaluation.get('score')} | Band: {evaluation.get('band')}",
        f"Trades: {metrics.get('total_trades', 0)} total (buy={metrics.get('buy_count', 0)}, sell={metrics.get('sell_count', 0)})",
        "",
    ]
    for bullet in evaluation.get("bullets") or []:
        lines.append(bullet)
    if evaluation.get("warnings"):
        lines.append("")
        for w in evaluation["warnings"]:
            lines.append(f"  Warning: {w}")
    return "\n".join(lines)
