"""
common.py — Shared constants and confusion-matrix helpers for all backtest runners.

Centrally defines:
  MONTHS   : The canonical 12-month backtest window (Mar 2025 – Feb 2026)
  SECTORS  : 5-sector, 10-ticker universe (50 tickers total)
  Confusion matrix helpers identical to those used in the orchestrator backtest

Import this from any backtest runner to keep sector/period definitions in sync.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# 12-month window: March 2025 – February 2026
# ─────────────────────────────────────────────────────────────────────────────

MONTHS: List[Tuple[date, date]] = [
    (date(2025,  3,  1), date(2025,  3, 31)),
    (date(2025,  4,  1), date(2025,  4, 30)),
    (date(2025,  5,  1), date(2025,  5, 31)),
    (date(2025,  6,  1), date(2025,  6, 30)),
    (date(2025,  7,  1), date(2025,  7, 31)),
    (date(2025,  8,  1), date(2025,  8, 31)),
    (date(2025,  9,  1), date(2025,  9, 30)),
    (date(2025, 10,  1), date(2025, 10, 31)),
    (date(2025, 11,  1), date(2025, 11, 30)),
    (date(2025, 12,  1), date(2025, 12, 31)),
    (date(2026,  1,  1), date(2026,  1, 31)),
    (date(2026,  2,  1), date(2026,  2, 28)),
]

# ─────────────────────────────────────────────────────────────────────────────
# 5-sector, 10-ticker universe (50 tickers × 12 months = 600 data points)
# ─────────────────────────────────────────────────────────────────────────────

SECTORS: Dict[str, List[str]] = {
    "Technology": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "META",
        "AMZN", "TSLA", "ORCL", "ANET", "CRM",
    ],
    "Healthcare": [
        "JNJ", "UNH", "LLY", "ABBV", "MRK",
        "PFE", "BMY", "CVS", "CI", "ABT",
    ],
    "Financials": [
        "JPM", "BAC", "WFC", "GS", "MS",
        "V", "MA", "AXP", "BLK", "C",
    ],
    "Consumer_Staples": [
        "PEP", "KO", "PG", "WMT", "COST",
        "MCD", "PM", "MO", "GIS", "CL",
    ],
    "Energy": [
        "XOM", "CVX", "COP", "SLB", "OXY",
        "PSX", "VLO", "MPC", "EOG", "HAL",
    ],
}

# All tickers in a flat list (preserves sector order)
ALL_TICKERS: List[str] = [t for tickers in SECTORS.values() for t in tickers]


# ─────────────────────────────────────────────────────────────────────────────
# Confusion matrix helpers
# ─────────────────────────────────────────────────────────────────────────────

def empty_matrix() -> Dict[str, int]:
    return {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "neutral": 0, "errors": 0}


def update_matrix(matrix: Dict[str, int], period: Dict[str, Any]) -> None:
    """Classify a single backtest period into the confusion matrix."""
    signal  = period.get("signal", "neutral")
    correct = period.get("signal_correct")

    if "error" in period and period.get("signal") in (None, "unknown"):
        matrix["errors"] += 1
        return

    if correct is None:
        matrix["neutral"] += 1
        return

    if signal == "bullish":
        matrix["TP" if correct else "FP"] += 1
    elif signal == "bearish":
        matrix["TN" if correct else "FN"] += 1
    else:
        matrix["neutral"] += 1


def matrix_metrics(m: Dict[str, int]) -> Dict[str, Any]:
    """Compute accuracy / precision / recall / specificity / F1 from counts."""
    tp, fp, tn, fn = m["TP"], m["FP"], m["TN"], m["FN"]
    d    = tp + fp + tn + fn
    c    = tp + tn
    prec = tp / (tp + fp) if (tp + fp) else None
    rec  = tp / (tp + fn) if (tp + fn) else None
    spec = tn / (tn + fp) if (tn + fp) else None
    f1   = 2 * prec * rec / (prec + rec) if prec and rec else None
    acc  = c / d if d else None
    tot  = d + m["neutral"]
    abst = m["neutral"] / tot if tot else None

    pct  = lambda v: round(v * 100, 1) if v is not None else None
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "neutral_count":       m["neutral"],
        "error_count":         m["errors"],
        "directional_signals": d,
        "correct_signals":     c,
        "accuracy_pct":        pct(acc),
        "precision_pct":       pct(prec),
        "recall_pct":          pct(rec),
        "specificity_pct":     pct(spec),
        "f1_pct":              pct(f1),
        "abstention_rate_pct": pct(abst),
    }


def print_matrix(met: Dict[str, Any], label: str) -> None:
    """Print a formatted 2×2 confusion matrix table to stdout."""
    f = lambda v: f"{v:.1f}%" if v is not None else "N/A"
    print(f"\n{'─'*60}")
    print(f"  2×2 CONFUSION MATRIX — {label}")
    print(f"{'─'*60}")
    print(f"                    Actual UP    Actual DOWN")
    print(f"  Pred BULLISH  │  TP={met['TP']:>5}     FP={met['FP']:>5}")
    print(f"  Pred BEARISH  │  FN={met['FN']:>5}     TN={met['TN']:>5}")
    print(f"{'─'*60}")
    print(f"  Accuracy   : {f(met['accuracy_pct'])}")
    print(f"  Precision  : {f(met['precision_pct'])}")
    print(f"  Recall     : {f(met['recall_pct'])}")
    print(f"  Specificity: {f(met['specificity_pct'])}")
    print(f"  F1         : {f(met['f1_pct'])}")
    print(f"  Abstention : {f(met['abstention_rate_pct'])}  ({met['neutral_count']} neutral, {met['error_count']} errors)")
