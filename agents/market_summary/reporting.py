from __future__ import annotations

from typing import Any, Dict


def build_text_report(evaluation: Dict[str, Any]) -> str:
    lines = [
        "Market Summary Agent — daily market-wide briefing",
        f"Market-wide signal: {evaluation.get('market_wide_signal')} | Score: {evaluation.get('score')}",
        f"VIX: {evaluation.get('vix')} ({evaluation.get('vix_regime')})",
        "",
    ]
    for bullet in evaluation.get("bullets") or []:
        lines.append(bullet)
    leaders = evaluation.get("sector_leaders") or []
    if leaders:
        lines.append("")
        lines.append("Sector leaders (20d vs SPY):")
        for row in leaders:
            lines.append(
                f"  - {row['label']} ({row['ticker']}): {row['vs_spy_20d_pct']:+.2f}%"
            )
    return "\n".join(lines)
