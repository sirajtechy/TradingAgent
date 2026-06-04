"""
Master pilot merge helpers — shared by unified/sector pilots (logic unchanged).
"""

from __future__ import annotations

import re
from typing import Any, Dict


def slug_sector(sector: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", sector.strip()).strip("-").lower()
    return s or "unknown"


def confusion_from_master_tickers(tickers: Dict[str, Any]) -> Dict[str, Any]:
    """Directional confusion vs target-hit labels (same as parallel pilot)."""
    tp = fp = tn = fn = neutral = errors = 0
    for row in tickers.values():
        if not isinstance(row, dict):
            continue
        if row.get("error"):
            errors += 1
            continue
        sig = row.get("fusion_final_signal")
        corr = row.get("signal_correct")
        if corr is None:
            neutral += 1
            continue
        if sig is None:
            neutral += 1
            continue
        sig = str(sig).lower()
        corr = bool(corr)
        if sig not in ("bullish", "bearish"):
            neutral += 1
            continue
        if sig == "bullish" and corr is True:
            tp += 1
        elif sig == "bullish" and corr is False:
            fp += 1
        elif sig == "bearish" and corr is True:
            tn += 1
        elif sig == "bearish" and corr is False:
            fn += 1
        else:
            errors += 1

    directional = tp + fp + tn + fn
    correct = tp + tn

    def pct(v: float | None) -> float | None:
        return round(v * 100, 1) if v is not None else None

    acc = correct / directional if directional else None
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    spec = tn / (tn + fp) if (tn + fp) else None
    f1 = (
        (2 * prec * rec / (prec + rec))
        if (prec is not None and rec is not None and (prec + rec) > 0)
        else None
    )
    abst = neutral / (neutral + directional) if (neutral + directional) else None

    return {
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "directional": directional,
        "correct": correct,
        "neutral": neutral,
        "errors": errors,
        "accuracy_pct": pct(acc),
        "precision_pct": pct(prec),
        "recall_pct": pct(rec),
        "specificity_pct": pct(spec),
        "f1_pct": pct(f1),
        "abstention_pct": pct(abst),
    }
