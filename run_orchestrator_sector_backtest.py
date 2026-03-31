#!/usr/bin/env python3
"""
Full 5-sector orchestrator backtest — 12 months, 50 tickers, parallel.

Sectors: Technology, Healthcare, Financials, Consumer Staples, Energy
10 stocks each = 50 tickers × 12 months = 600 data points.
Parallel via ProcessPoolExecutor (6 workers).
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

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


def _run_one_ticker(ticker: str) -> Tuple[str, Any]:
    """Run orchestrator backtest for a single ticker (in worker process)."""
    from orchestrator_agent.backtest import run_monthly_backtest
    try:
        result = run_monthly_backtest(ticker=ticker, months=MONTHS)
        s = result["summary"]
        acc = f"{s['accuracy_pct']}%" if s["accuracy_pct"] is not None else "N/A"
        print(f"  ✓ {ticker:<6} dir={s['directional_signals']:>2}/{s['total_periods']}  acc={acc}", flush=True)
        return (ticker, result)
    except Exception as exc:
        print(f"  ✗ {ticker:<6} ERROR: {exc}", flush=True)
        return (ticker, None)


def _empty_matrix() -> Dict[str, int]:
    return {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "neutral": 0, "errors": 0}


def _update_matrix(m: Dict[str, int], period: Dict[str, Any]) -> None:
    signal = period.get("signal", "neutral")
    correct = period.get("signal_correct")
    if "error" in period and "start_price" not in period:
        m["errors"] += 1
        return
    if correct is None:
        m["neutral"] += 1
        return
    if signal == "bullish":
        m["TP" if correct else "FP"] += 1
    elif signal == "bearish":
        m["TN" if correct else "FN"] += 1


def _metrics(m: Dict[str, int]) -> Dict[str, Any]:
    tp, fp, tn, fn = m["TP"], m["FP"], m["TN"], m["FN"]
    d = tp + fp + tn + fn
    c = tp + tn
    prec = tp / (tp + fp) if (tp + fp) else None
    rec  = tp / (tp + fn) if (tp + fn) else None
    spec = tn / (tn + fp) if (tn + fp) else None
    f1   = 2 * prec * rec / (prec + rec) if prec and rec else None
    acc  = c / d if d else None
    tot  = d + m["neutral"]
    abst = m["neutral"] / tot if tot else None
    fmt  = lambda v: round(v * 100, 1) if v is not None else None
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "neutral": m["neutral"], "errors": m["errors"],
        "directional": d, "correct": c,
        "accuracy_pct": fmt(acc), "precision_pct": fmt(prec),
        "recall_pct": fmt(rec), "specificity_pct": fmt(spec),
        "f1_pct": fmt(f1), "abstention_pct": fmt(abst),
    }


def _print_matrix(met: Dict[str, Any], label: str) -> None:
    f = lambda v: f"{v:.1f}%" if v is not None else "N/A"
    print(f"\n{'─'*60}")
    print(f"  2×2 CONFUSION MATRIX — {label}")
    print(f"{'─'*60}")
    print(f"                  Actual UP   Actual DOWN")
    print(f"  Pred BULLISH  │  TP={met['TP']:>5}   FP={met['FP']:>5}")
    print(f"  Pred BEARISH  │  FN={met['FN']:>5}   TN={met['TN']:>5}")
    print(f"\n  Directional signals : {met['directional']}")
    print(f"  Neutral abstentions : {met['neutral']}  ({f(met['abstention_pct'])})")
    print(f"  Accuracy            : {f(met['accuracy_pct'])}")
    print(f"  Precision (TP/(TP+FP)): {f(met['precision_pct'])}")
    print(f"  Recall    (TP/(TP+FN)): {f(met['recall_pct'])}")
    print(f"  Specificity(TN/(TN+FP)): {f(met['specificity_pct'])}")
    print(f"  F1 Score            : {f(met['f1_pct'])}")


def main() -> None:
    output_dir = Path("orchestrator_sector_results")
    output_dir.mkdir(exist_ok=True)

    all_tickers = []
    ticker_to_sector = {}
    for sector, tickers in SECTORS.items():
        for t in tickers:
            all_tickers.append(t)
            ticker_to_sector[t] = sector

    total = len(all_tickers)
    workers = 6

    print(f"\n{'='*64}")
    print(f"  ORCHESTRATOR SECTOR BACKTEST — 12 months (Mar 2025 – Feb 2026)")
    print(f"  Sectors: {len(SECTORS)}   Tickers: {total}   Months: 12")
    print(f"  Total data points: {total * 12}")
    print(f"  Workers: {workers} parallel processes")
    print(f"{'='*64}\n")

    t0 = time.time()
    results: Dict[str, Any] = {}

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_one_ticker, t): t for t in all_tickers}
        for future in as_completed(futures):
            ticker, result = future.result()
            results[ticker] = result
            if result is not None:
                out = output_dir / f"{ticker}_orchestrator_backtest.json"
                with open(out, "w") as fh:
                    json.dump(result, fh, indent=2)

    elapsed = time.time() - t0
    print(f"\n⏱  Completed {total} tickers in {elapsed:.1f}s")

    # Per-sector tables + matrices
    overall = _empty_matrix()
    sector_metrics = {}

    for sector, tickers in SECTORS.items():
        sm = _empty_matrix()
        print(f"\n►  {sector.upper()}")
        print(f"  {'TICKER':<8} {'SIGNALS':>7} {'CORRECT':>7} {'HIT%':>7} {'AVG_SCORE':>9} {'CONFLICTS':>9}")
        print(f"  {'─'*55}")
        for t in tickers:
            r = results.get(t)
            if r is None:
                print(f"  {t:<8} {'ERROR':>7}")
                sm["errors"] += 1
                overall["errors"] += 1
                continue
            s = r["summary"]
            acc_s = f"{s['accuracy_pct']}%" if s["accuracy_pct"] is not None else "N/A"
            scores = [p["orchestrator_score"] for p in r["periods"]
                      if p.get("orchestrator_score") is not None]
            avg = f"{sum(scores)/len(scores):.1f}" if scores else "N/A"
            conflicts = sum(1 for p in r["periods"] if p.get("conflict_detected"))
            print(f"  {t:<8} {s['directional_signals']:>7} {s['correct_signals']:>7} {acc_s:>7} {avg:>9} {conflicts:>9}")
            for p in r["periods"]:
                _update_matrix(sm, p)
                _update_matrix(overall, p)

        met = _metrics(sm)
        sector_metrics[sector] = met
        _print_matrix(met, sector.upper())

    omet = _metrics(overall)
    _print_matrix(omet, "OVERALL (ALL 5 SECTORS)")

    # Summary comparison table
    print(f"\n\n{'='*80}")
    print(f"  SECTOR COMPARISON")
    print(f"{'='*80}")
    f = lambda v: f"{v:.1f}%" if v is not None else "N/A"
    print(f"  {'Sector':<18} {'Dir':>5} {'Acc':>7} {'Prec':>7} {'Spec':>7} {'F1':>7} {'Abst':>7}")
    print(f"  {'─'*65}")
    for sector in SECTORS:
        m = sector_metrics[sector]
        print(f"  {sector:<18} {m['directional']:>5} {f(m['accuracy_pct']):>7} "
              f"{f(m['precision_pct']):>7} {f(m['specificity_pct']):>7} "
              f"{f(m['f1_pct']):>7} {f(m['abstention_pct']):>7}")
    print(f"  {'─'*65}")
    print(f"  {'OVERALL':<18} {omet['directional']:>5} {f(omet['accuracy_pct']):>7} "
          f"{f(omet['precision_pct']):>7} {f(omet['specificity_pct']):>7} "
          f"{f(omet['f1_pct']):>7} {f(omet['abstention_pct']):>7}")
    print(f"{'='*80}")

    # Save JSON
    consolidated = {
        "meta": {
            "window": "Mar 2025 – Feb 2026",
            "months": 12,
            "sectors": len(SECTORS),
            "tickers": total,
            "data_points": total * 12,
            "elapsed_sec": round(elapsed, 1),
        },
        "overall": omet,
        "by_sector": sector_metrics,
    }
    with open("orchestrator_sector_backtest.json", "w") as fh:
        json.dump(consolidated, fh, indent=2, default=str)
    print(f"\n✓  Consolidated JSON → orchestrator_sector_backtest.json")
    print(f"✓  Per-ticker JSON   → {output_dir}/")


if __name__ == "__main__":
    main()
