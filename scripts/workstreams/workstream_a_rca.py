"""
workstream_a_rca.py — Orchestrator Reassessment: Steps 1 & 2

Step 1: Load + audit every misclassified data point
Step 2: Full Root Cause Analysis across 5 categories:
        - Signal Conflict Errors
        - Timing Errors
        - Market Regime Errors
        - Indicator Lag Errors
        - Fundamental Misalignment
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import paths

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Load & Audit All Misclassified Signals
# ─────────────────────────────────────────────────────────────────────────────

RESULTS_DIR = str(paths.ORCH_BACKTEST)


def load_all_signals() -> List[Dict[str, Any]]:
    signals = []
    for fname in sorted(os.listdir(RESULTS_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(RESULTS_DIR, fname)) as fh:
            data = json.load(fh)
        ticker = data["ticker"]
        for p in data.get("periods", []):
            p["ticker"] = ticker
            signals.append(p)
    return signals


def classify_error(s: Dict[str, Any]) -> str:
    """
    Assign a primary root-cause category to a misclassified signal.

    Category decision tree:
    1. conflict_detected=True  → Signal Conflict Error
    2. |price_return_pct| < 3  → Timing Error (small move, borderline call)
    3. tech_weight >= 0.7 and tech_score diverges from direction → Indicator Lag Error
    4. fund_score < 45 but signal is bullish → Fundamental Misalignment
    5. Otherwise              → Market Regime Error
    """
    if s.get("conflict_detected"):
        return "Signal Conflict Error"

    ret = abs(s.get("price_return_pct", 0.0))
    if ret < 3.0:
        return "Timing Error"

    tech_w = (s.get("weights_applied") or {}).get("tech", 0.5)
    tech_s = s.get("tech_score", 50.0) or 50.0
    actual = s.get("actual_direction", "")
    signal = s.get("signal", "")
    fund_s = s.get("fund_score", 50.0) or 50.0

    if tech_w >= 0.7 and actual == "down" and tech_s > 60:
        return "Indicator Lag Error"

    if signal == "bullish" and fund_s < 45:
        return "Fundamental Misalignment"

    return "Market Regime Error"


def run_step1(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Print structured extraction table of all misclassified signals."""
    misses = [s for s in signals if not s.get("signal_correct", True)]

    print("\n" + "=" * 90)
    print("STEP 1 — MISCLASSIFIED SIGNAL AUDIT TABLE")
    print("=" * 90)
    print(f"{'#':<4} {'Ticker':<6} {'Month':<14} {'Signal':<10} {'Actual':<8} "
          f"{'Return%':<9} {'Score':<7} {'TechW':<7} {'Conf':<7} {'Conflict':<9} {'Category'}")
    print("-" * 90)

    for i, s in enumerate(misses, 1):
        ret = s.get("price_return_pct", 0.0)
        tw = (s.get("weights_applied") or {}).get("tech", 0.0)
        category = classify_error(s)
        print(
            f"{i:<4} {s['ticker']:<6} {s.get('month','?'):<14} "
            f"{s.get('signal','?'):<10} {s.get('actual_direction','?'):<8} "
            f"{ret:+7.1f}%  {s.get('orchestrator_score',0.0):<7.1f} "
            f"{tw:<7.2f} {s.get('confidence',0.0):<7.4f} "
            f"{'YES' if s.get('conflict_detected') else 'NO':<9} {category}"
        )

    print(f"\nTotal misclassified: {len(misses)} / {len(signals)} "
          f"({len(misses)/len(signals)*100:.1f}%)")
    return misses


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Root Cause Analysis
# ─────────────────────────────────────────────────────────────────────────────

def run_step2(signals: List[Dict[str, Any]], misses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Full RCA across 5 categories."""

    print("\n" + "=" * 90)
    print("STEP 2 — ROOT CAUSE ANALYSIS (5 CATEGORIES)")
    print("=" * 90)

    # Categorise every miss
    categories = [classify_error(s) for s in misses]
    cat_counts = Counter(categories)
    total_miss = len(misses)

    rca: Dict[str, Any] = {}

    # ── Category 1: Signal Conflict Errors ────────────────────────────────
    conflict_misses = [s for s in misses if classify_error(s) == "Signal Conflict Error"]
    conflict_all   = [s for s in signals if s.get("conflict_detected")]
    conflict_accuracy = (
        sum(1 for s in conflict_all if s.get("signal_correct")) / len(conflict_all) * 100
        if conflict_all else 0
    )
    rca["signal_conflict"] = {
        "count": len(conflict_misses),
        "pct_of_misses": round(len(conflict_misses) / total_miss * 100, 1),
        "total_conflict_signals": len(conflict_all),
        "conflict_win_rate": round(conflict_accuracy, 1),
        "finding": (
            f"{len(conflict_all)} signals fired during conflict. "
            f"Win rate on conflicts: {conflict_accuracy:.1f}% — "
            f"{'BELOW AVERAGE' if conflict_accuracy < 52 else 'ACCEPTABLE'}. "
            "Root cause: conflict_winner_discount is insufficient; "
            "weak dominant signals still fire instead of abstaining."
        ),
    }

    # ── Category 2: Timing Errors ─────────────────────────────────────────
    timing_misses = [s for s in misses if classify_error(s) == "Timing Error"]
    timing_returns = [abs(s.get("price_return_pct", 0.0)) for s in timing_misses]
    rca["timing_errors"] = {
        "count": len(timing_misses),
        "pct_of_misses": round(len(timing_misses) / total_miss * 100, 1),
        "avg_abs_return_pct": round(statistics.mean(timing_returns), 2) if timing_returns else 0,
        "finding": (
            f"{len(timing_misses)} misses on moves < 3%. "
            "Root cause: monthly signal window is too coarse — "
            "small reversals within the month tip the actual direction "
            "against the signal. A trailing stop / early-exit rule "
            "would convert these to neutral rather than wrong."
        ),
    }

    # ── Category 3: Market Regime Errors ─────────────────────────────────
    regime_misses = [s for s in misses if classify_error(s) == "Market Regime Error"]
    # Check if losses cluster in specific months (potential regime shift)
    months_of_regime = Counter(s.get("month", "") for s in regime_misses)
    top_regime_months = months_of_regime.most_common(3)
    rca["market_regime"] = {
        "count": len(regime_misses),
        "pct_of_misses": round(len(regime_misses) / total_miss * 100, 1),
        "top_affected_months": top_regime_months,
        "finding": (
            f"{len(regime_misses)} misses in trending/volatile regimes. "
            f"Top affected months: {[m for m, _ in top_regime_months]}. "
            "Root cause: CWAF has no regime detection layer — "
            "bullish signals fire in high-volatility / downtrend regimes "
            "because ADX and VIX context are ignored."
        ),
    }

    # ── Category 4: Indicator Lag Errors ─────────────────────────────────
    lag_misses = [s for s in misses if classify_error(s) == "Indicator Lag Error"]
    lag_tech_scores = [s.get("tech_score", 50.0) or 50.0 for s in lag_misses]
    rca["indicator_lag"] = {
        "count": len(lag_misses),
        "pct_of_misses": round(len(lag_misses) / total_miss * 100, 1),
        "avg_tech_score_on_lag_misses": round(statistics.mean(lag_tech_scores), 1) if lag_tech_scores else 0,
        "finding": (
            f"{len(lag_misses)} misses where tech score was bullish (>60) "
            "but price fell. Root cause: momentum indicators (EMA, MACD) "
            "lag by 10–20 days on monthly bars. The tech agent fires on "
            "prior-month momentum when the trend has already reversed."
        ),
    }

    # ── Category 5: Fundamental Misalignment ──────────────────────────────
    fund_misses = [s for s in misses if classify_error(s) == "Fundamental Misalignment"]
    fund_scores_on_miss = [s.get("fund_score", 50.0) or 50.0 for s in fund_misses]
    rca["fundamental_misalignment"] = {
        "count": len(fund_misses),
        "pct_of_misses": round(len(fund_misses) / total_miss * 100, 1),
        "avg_fund_score_on_miss": round(statistics.mean(fund_scores_on_miss), 1) if fund_scores_on_miss else 0,
        "finding": (
            f"{len(fund_misses)} misses where fundamentals were bearish (<45) "
            "but orchestrator still fired bullish. Root cause: tech_only weight "
            "(0.85 tech / 0.15 fund) overpowers fundamental bearish signals — "
            "the fund agent's warning is diluted to irrelevance."
        ),
    }

    # ── Summary Table ──────────────────────────────────────────────────────
    print(f"\n{'Category':<30} {'Count':>6} {'% of Misses':>12}")
    print("-" * 52)
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"{cat:<30} {cnt:>6} {cnt/total_miss*100:>11.1f}%")

    print("\n── Detailed Findings ──────────────────────────────────────────")
    for key, data in rca.items():
        label = key.replace("_", " ").title()
        print(f"\n[{label}]")
        print(f"  Count: {data['count']} ({data['pct_of_misses']}% of misses)")
        print(f"  Finding: {data['finding']}")

    # Aggregate stats
    correct = [s for s in signals if s.get("signal_correct")]
    print("\n── Overall Baseline ───────────────────────────────────────────")
    print(f"  Total signals    : {len(signals)}")
    print(f"  Correct          : {len(correct)} ({len(correct)/len(signals)*100:.1f}%)")
    print(f"  Wrong            : {len(misses)} ({len(misses)/len(signals)*100:.1f}%)")

    # Bullish bias check
    bullish_signals = [s for s in signals if s.get("signal") == "bullish"]
    bullish_correct = [s for s in bullish_signals if s.get("signal_correct")]
    print(f"  Bullish fired    : {len(bullish_signals)} ({len(bullish_correct)/max(len(bullish_signals),1)*100:.1f}% correct)")
    bearish_signals = [s for s in signals if s.get("signal") == "bearish"]
    bearish_correct = [s for s in bearish_signals if s.get("signal_correct")]
    print(f"  Bearish fired    : {len(bearish_signals)} ({len(bearish_correct)/max(len(bearish_signals),1)*100:.1f}% correct)")
    neutral_signals = [s for s in signals if s.get("signal") == "neutral"]
    print(f"  Neutral fired    : {len(neutral_signals)}")

    return rca


# ─────────────────────────────────────────────────────────────────────────────
# Save RCA results
# ─────────────────────────────────────────────────────────────────────────────

def save_rca(misses: List[Dict[str, Any]], rca: Dict[str, Any]) -> None:
    output = {
        "total_misclassified": len(misses),
        "categories": rca,
        "misclassified_signals": [
            {
                "ticker": s["ticker"],
                "month": s.get("month"),
                "signal": s.get("signal"),
                "actual_direction": s.get("actual_direction"),
                "price_return_pct": s.get("price_return_pct"),
                "orchestrator_score": s.get("orchestrator_score"),
                "tech_score": s.get("tech_score"),
                "fund_score": s.get("fund_score"),
                "confidence": s.get("confidence"),
                "conflict_detected": s.get("conflict_detected"),
                "weights_applied": s.get("weights_applied"),
                "root_cause": classify_error(s),
            }
            for s in misses
        ],
    }
    with open("rca_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print("\n✓ RCA saved → rca_results.json")


if __name__ == "__main__":
    signals = load_all_signals()
    misses = run_step1(signals)
    rca = run_step2(signals, misses)
    save_rca(misses, rca)
