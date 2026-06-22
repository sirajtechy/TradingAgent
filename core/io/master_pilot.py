"""
Master pilot merge helpers — shared by unified/sector pilots (logic unchanged).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def slug_sector(sector: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", sector.strip()).strip("-").lower()
    return s or "unknown"


def confusion_from_master_tickers(tickers: Dict[str, Any]) -> Dict[str, Any]:
    """Directional confusion vs target-hit labels (multi-agent when fields present)."""
    from core.evaluation.confusion import build_confusion_payload

    rows: List[Dict[str, Any]] = []
    for sym, row in tickers.items():
        if not isinstance(row, dict):
            continue
        px_sym = row.get("phoenix_signal")
        if px_sym == "BUY":
            px_dir = "bullish"
        elif px_sym == "AVOID":
            px_dir = "bearish"
        else:
            px_dir = "neutral"
        rows.append(
            {
                "ticker": str(sym).upper(),
                "signal": row.get("fusion_final_signal"),
                "signal_correct": row.get("signal_correct"),
                "phoenix_signal": px_dir,
                "signal_correct_phoenix": row.get("signal_correct_phoenix"),
                "technical_signal": row.get("technical_signal"),
                "signal_correct_technical": row.get("signal_correct_technical"),
                "fund_signal": row.get("fund_signal_normalized"),
                "signal_correct_fundamental": row.get("signal_correct_fundamental"),
                "error": row.get("error"),
            }
        )

    payload = build_confusion_payload(
        rows,
        meta={"source": "master_pilot.tickers", "tickers": len(rows)},
    )
    return payload.get("cumulative", {}).get("overall") or {}
