#!/usr/bin/env python3
"""Rebuild sector_backtest_results.json from per-ticker cache files in sector_results/,
then apply v3 scoring via reevaluate_thresholds.py."""
import json
from pathlib import Path

SECTORS = {
    "Technology":       ["AAPL","MSFT","NVDA","GOOGL","META","AMZN","TSLA","ORCL","ANET","CRM","ADBE","INTC"],
    "Healthcare":       ["JNJ","UNH","PFE","MRK","ABBV","LLY","TMO","ABT","MDT","BMY","AMGN","GILD"],
    "Financials":       ["JPM","BAC","WFC","GS","MS","BLK","AXP","PNC","USB","SCHW","CME","MA"],
    "Consumer Staples": ["PG","KO","PEP","WMT","COST","MDLZ","CL","KHC","GIS","SJM","MO","PM"],
    "Energy":           ["XOM","CVX","COP","SLB","OXY","PSX","VLO","MPC","EOG","HAL","BKR","DVN"],
}

CACHE_DIR = Path("sector_results")


def load_ticker(ticker):
    path = CACHE_DIR / f"{ticker}_backtest_results.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def compute_cm(results):
    tp = fp = fn = tn = neutral = errors = 0
    for ticker, tdata in results.items():
        if tdata is None:
            errors += 1
            continue
        for p in tdata.get("periods", []):
            sig = (p.get("signal") or "").lower()
            act = (p.get("actual_direction") or "").lower()
            if "bullish" in sig and act == "up":
                tp += 1
            elif "bullish" in sig and act == "down":
                fp += 1
            elif "bearish" in sig and act == "up":
                fn += 1
            elif "bearish" in sig and act == "down":
                tn += 1
            else:
                neutral += 1
    total_dir = tp + fp + fn + tn
    correct = tp + tn
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "neutral_count": neutral, "error_count": errors,
        "directional_signals": total_dir,
        "correct_signals": correct,
        "accuracy_pct": round(correct / total_dir * 100, 1) if total_dir else None,
        "precision_pct": round(tp / (tp + fp) * 100, 1) if (tp + fp) else None,
        "recall_pct": round(tp / (tp + fn) * 100, 1) if (tp + fn) else None,
        "specificity_pct": round(tn / (tn + fp) * 100, 1) if (tn + fp) else None,
        "f1_pct": round(2 * tp / (2 * tp + fp + fn) * 100, 1) if (2 * tp + fp + fn) else None,
        "abstention_rate_pct": round(neutral / (total_dir + neutral) * 100, 1) if (total_dir + neutral) else None,
    }


# Rebuild
total_tickers = sum(len(v) for v in SECTORS.values())
consolidated = {
    "meta": {
        "window": "Mar 2025 – Feb 2026",
        "months": 12,
        "sectors": len(SECTORS),
        "tickers": total_tickers,
        "data_source": "yfinance",
    },
    "sectors": {},
}

for sector, tickers in SECTORS.items():
    results = {}
    for t in tickers:
        results[t] = load_ticker(t)
    consolidated["sectors"][sector] = {
        "tickers": results,
        "confusion_matrix": compute_cm(results),
    }

# Overall
all_results = {}
for sector_data in consolidated["sectors"].values():
    all_results.update(sector_data["tickers"])
consolidated["overall_confusion_matrix"] = compute_cm(all_results)

with open("sector_backtest_results.json", "w") as f:
    json.dump(consolidated, f, indent=2, default=str)

print(f"Rebuilt sector_backtest_results.json from {len(all_results)} ticker cache files")
print(f"v2 baseline: {consolidated['overall_confusion_matrix']}")
