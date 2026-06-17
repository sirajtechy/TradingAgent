from __future__ import annotations

from typing import Any, Dict


def build_text_report(evaluation: Dict[str, Any]) -> str:
    metrics = evaluation.get("metrics") or {}
    lines = [
        "Insider Trades Agent — Form 4 common-stock sales (code S)",
        f"Signal: {evaluation.get('signal')} | Score: {evaluation.get('score')} | Band: {evaluation.get('band')}",
        f"Trades: {metrics.get('total_trades', 0)} total (buy={metrics.get('buy_count', 0)}, sell={metrics.get('sell_count', 0)})",
        "",
    ]
    for bullet in evaluation.get("bullets") or []:
        lines.append(bullet)
    per_insider = evaluation.get("per_insider_sales") or []
    if per_insider:
        lines.extend(["", "Per-insider sales:"])
        for row in per_insider:
            title = f" ({row['title']})" if row.get("title") else ""
            period = row.get("sale_period") or row.get("last_sale_date") or ""
            period_txt = f" · {period}" if period else ""
            lines.append(
                f"  • {row.get('owner')}{title}: "
                f"${row.get('dollars', 0):,.0f} · "
                f"{row.get('shares', 0):,.0f} sh @ ${row.get('avg_price', 0):,.2f} · "
                f"{row.get('sale_count', 0)} sale(s){period_txt}"
            )
    if evaluation.get("warnings"):
        lines.append("")
        for w in evaluation["warnings"]:
            lines.append(f"  Warning: {w}")
    return "\n".join(lines)
