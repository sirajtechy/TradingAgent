#!/usr/bin/env python3
"""
Parallel 2-sector technical backtest — Technology + Energy, 10 stocks each.
Uses ProcessPoolExecutor to run tickers concurrently.
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
    "Energy": [
        "XOM", "CVX", "COP", "SLB", "OXY",
        "PSX", "VLO", "MPC", "EOG", "HAL",
    ],
}


def _run_one_ticker(ticker: str) -> Tuple[str, Any]:
    """Run backtest for a single ticker (called in worker process)."""
    from technical_agent.backtest import run_monthly_backtest
    try:
        result = run_monthly_backtest(ticker=ticker, months=MONTHS)
        acc = result["summary"]["accuracy_pct"]
        sigs = result["summary"]["directional_signals"]
        hit = f"{acc}% ({result['summary']['correct_signals']}/{sigs})" if acc is not None else "N/A"
        print(f"  ✓ {ticker:<6} hit rate: {hit}", flush=True)
        return (ticker, result)
    except Exception as exc:
        print(f"  ✗ {ticker:<6} ERROR: {exc}", flush=True)
        return (ticker, None)


def _empty_matrix() -> Dict[str, int]:
    return {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "neutral": 0, "errors": 0}


def _update_matrix(m: Dict[str, int], period: Dict[str, Any]) -> None:
    signal = period.get("signal", "neutral")
    correct = period.get("signal_correct")
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
    print(f"  CONFUSION MATRIX — {label}")
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
    output_dir = Path("technical_sector_results")
    output_dir.mkdir(exist_ok=True)

    all_tickers = []
    ticker_to_sector = {}
    for sector, tickers in SECTORS.items():
        for t in tickers:
            all_tickers.append(t)
            ticker_to_sector[t] = sector

    total = len(all_tickers)
    workers = 4  # 4 parallel processes — good balance vs yfinance rate limits

    print(f"\n{'='*60}")
    print(f"  PARALLEL TECHNICAL BACKTEST — 12 months (Mar 2025 – Feb 2026)")
    print(f"  Sectors: 2 (Technology, Energy)   Tickers: {total}")
    print(f"  Workers: {workers} parallel processes")
    print(f"{'='*60}\n")

    t0 = time.time()
    results: Dict[str, Any] = {}

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_one_ticker, t): t for t in all_tickers}
        for future in as_completed(futures):
            ticker, result = future.result()
            results[ticker] = result
            if result is not None:
                out = output_dir / f"{ticker}_technical_backtest_results.json"
                with open(out, "w") as fh:
                    json.dump(result, fh, indent=2)

    elapsed = time.time() - t0
    print(f"\n  Completed in {elapsed:.1f}s")

    # Build per-sector and overall matrices
    overall = _empty_matrix()
    for sector, tickers in SECTORS.items():
        sm = _empty_matrix()
        print(f"\n►  {sector.upper()}")
        print(f"  {'TICKER':<8} {'SIGNALS':>7} {'CORRECT':>7} {'HIT%':>6} {'AVG SCORE':>9}")
        print(f"  {'─'*45}")
        for t in tickers:
            r = results.get(t)
            if r is None:
                print(f"  {t:<8} {'ERROR':>7}")
                sm["errors"] += 1
                overall["errors"] += 1
                continue
            s = r["summary"]
            acc = f"{s['accuracy_pct']}%" if s["accuracy_pct"] is not None else "N/A"
            scores = [p["experimental_score"] for p in r["periods"] if p.get("experimental_score") is not None]
            avg = f"{sum(scores)/len(scores):.1f}" if scores else "N/A"
            print(f"  {t:<8} {s['directional_signals']:>7} {s['correct_signals']:>7} {acc:>6} {avg:>9}")
            for p in r["periods"]:
                _update_matrix(sm, p)
                _update_matrix(overall, p)

        met = _metrics(sm)
        _print_matrix(met, sector.upper())

    omet = _metrics(overall)
    _print_matrix(omet, "OVERALL (TECH + ENERGY)")

    # Save JSON
    consolidated = {
        "meta": {"window": "Mar 2025 – Feb 2026", "months": 12,
                 "sectors": 2, "tickers": total, "elapsed_sec": round(elapsed, 1)},
        "overall": omet,
        "by_sector": {},
    }
    for sector, tickers in SECTORS.items():
        sm = _empty_matrix()
        for t in tickers:
            r = results.get(t)
            if r:
                for p in r["periods"]:
                    _update_matrix(sm, p)
        consolidated["by_sector"][sector] = _metrics(sm)

    with open("technical_2sector_backtest.json", "w") as fh:
        json.dump(consolidated, fh, indent=2, default=str)
    print(f"\n✓  Results saved to technical_2sector_backtest.json")
    print(f"✓  Per-ticker JSON in {output_dir}/")


if __name__ == "__main__":
    main()
