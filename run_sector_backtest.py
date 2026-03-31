#!/usr/bin/env python3
"""
Sector-wide 12-month fundamental backtest.

Covers March 2025 – February 2026 (12 complete months).
Five sectors, 12 hand-picked large/mid-cap stocks each = 60 tickers.

Outputs:
  - Per-ticker results JSON
  - sector_backtest_results.json  (all raw data)
  - sector_confusion_matrix.json  (matrix + metrics per sector + overall)
  - Console report with confusion matrices formatted as tables

Usage:
    python run_sector_backtest.py
    python run_sector_backtest.py --sector Technology
    python run_sector_backtest.py --resume   # skip tickers whose JSON already exists
"""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from fundamental_agent.backtest import build_backtest_report, run_monthly_backtest

# ---------------------------------------------------------------------------
# 12-month window: March 2025 – February 2026
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Sector universe  —  12 large/mid-cap tickers per sector
# Chosen for: index representation, data availability on yfinance,
# and sector diversity within each group.
# ---------------------------------------------------------------------------
SECTORS: Dict[str, List[str]] = {
    "Technology": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "META",
        "AMZN", "TSLA", "ORCL", "ANET", "CRM",
        "AMD",  "INTC",
    ],
    "Healthcare": [
        "JNJ",  "UNH",  "LLY",  "ABBV", "MRK",
        "PFE",  "BMY",  "CVS",  "CI",   "MDT",
        "ABT",  "HUM",
    ],
    "Financials": [
        "JPM",  "BAC",  "WFC",  "GS",   "MS",
        "V",    "MA",   "AXP",  "BLK",  "C",
        "USB",  "PNC",
    ],
    "Consumer_Staples": [
        "PEP",  "KO",   "PG",   "WMT",  "COST",
        "MCD",  "PM",   "MO",   "GIS",  "K",
        "CL",   "CLX",
    ],
    "Energy": [
        "XOM",  "CVX",  "COP",  "SLB",  "OXY",
        "PSX",  "VLO",  "MPC",  "EOG",  "HAL",
        "BKR",  "DVN",
    ],
}


# ---------------------------------------------------------------------------
# Confusion matrix helpers
# ---------------------------------------------------------------------------

def _empty_matrix() -> Dict[str, int]:
    """TP / FP / TN / FN — directional signals only (neutral excluded)."""
    return {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "neutral": 0, "errors": 0}


def _update_matrix(matrix: Dict[str, int], period: Dict[str, Any]) -> None:
    signal = period.get("signal", "neutral")
    correct = period.get("signal_correct")

    if correct is None:
        # neutral abstention
        matrix["neutral"] += 1
        return

    if signal == "bullish":
        if correct:
            matrix["TP"] += 1
        else:
            matrix["FP"] += 1
    elif signal == "bearish":
        if correct:
            matrix["TN"] += 1
        else:
            matrix["FN"] += 1
    # If somehow another value, just skip


def _matrix_metrics(m: Dict[str, int]) -> Dict[str, Any]:
    tp, fp, tn, fn = m["TP"], m["FP"], m["TN"], m["FN"]
    directional = tp + fp + tn + fn
    correct = tp + tn

    precision      = tp / (tp + fp) if (tp + fp) > 0 else None
    recall         = tp / (tp + fn) if (tp + fn) > 0 else None
    specificity    = tn / (tn + fp) if (tn + fp) > 0 else None
    f1             = (2 * precision * recall / (precision + recall)
                      if precision and recall else None)
    accuracy       = correct / directional if directional > 0 else None
    abstention_rate = m["neutral"] / (directional + m["neutral"]) if (directional + m["neutral"]) > 0 else None

    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "neutral_count": m["neutral"],
        "error_count": m["errors"],
        "directional_signals": directional,
        "correct_signals": correct,
        "accuracy_pct":       round(accuracy       * 100, 1) if accuracy       is not None else None,
        "precision_pct":      round(precision      * 100, 1) if precision      is not None else None,
        "recall_pct":         round(recall         * 100, 1) if recall         is not None else None,
        "specificity_pct":    round(specificity    * 100, 1) if specificity    is not None else None,
        "f1_pct":             round(f1             * 100, 1) if f1             is not None else None,
        "abstention_rate_pct": round(abstention_rate * 100, 1) if abstention_rate is not None else None,
    }


# ---------------------------------------------------------------------------
# Per-ticker backtest runner (with resume support)
# ---------------------------------------------------------------------------

def run_ticker(
    ticker: str,
    data_source: str,
    resume: bool,
    output_dir: Path,
) -> Optional[Dict[str, Any]]:
    out_file = output_dir / f"{ticker}_backtest_results.json"

    if resume and out_file.exists():
        print(f"    [{ticker}] Resuming from cached result.")
        with open(out_file) as fh:
            return json.load(fh)

    try:
        result = run_monthly_backtest(
            ticker=ticker,
            months=MONTHS,
            shariah_standard="aaoifi",
            data_source=data_source,
        )
        with open(out_file, "w") as fh:
            json.dump(result, fh, indent=2)
        acc = result["summary"]["accuracy_pct"]
        sigs = result["summary"]["directional_signals"]
        hit_str = f"{acc}% ({result['summary']['correct_signals']}/{sigs})" if acc is not None else "N/A (all neutral)"
        print(f"    [{ticker}] done — hit rate: {hit_str}")
        return result
    except Exception as exc:
        print(f"    [{ticker}] ERROR: {exc}")
        return None


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _render_matrix_table(metrics: Dict[str, Any], label: str) -> str:
    lines = []
    lines.append(f"\n{'─'*60}")
    lines.append(f"  CONFUSION MATRIX  —  {label}")
    lines.append(f"{'─'*60}")

    tp, fp, tn, fn = metrics["TP"], metrics["FP"], metrics["TN"], metrics["FN"]
    # 2×2 table: rows = Predicted, cols = Actual
    lines.append("")
    lines.append("                  Actual UP   Actual DOWN")
    lines.append(f"  Pred BULLISH  │  TP={tp:>5}   FP={fp:>5}")
    lines.append(f"  Pred BEARISH  │  FN={fn:>5}   TN={tn:>5}")
    lines.append("")

    def _fmt(v):
        return f"{v:.1f}%" if v is not None else "N/A"

    lines.append(f"  Directional signals : {metrics['directional_signals']}")
    lines.append(f"  Neutral abstentions : {metrics['neutral_count']}  ({_fmt(metrics['abstention_rate_pct'])} of all decisions)")
    lines.append(f"  Accuracy            : {_fmt(metrics['accuracy_pct'])}")
    lines.append(f"  Precision  (TP/(TP+FP)): {_fmt(metrics['precision_pct'])}")
    lines.append(f"  Recall     (TP/(TP+FN)): {_fmt(metrics['recall_pct'])}")
    lines.append(f"  Specificity(TN/(TN+FP)): {_fmt(metrics['specificity_pct'])}")
    lines.append(f"  F1 Score            : {_fmt(metrics['f1_pct'])}")
    if metrics["error_count"] > 0:
        lines.append(f"  ⚠  Tickers with errors (excluded): {metrics['error_count']}")

    return "\n".join(lines)


def _render_ticker_summary_table(sector_results: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"\n  {'TICKER':<8}  {'SIGNALS':>7}  {'CORRECT':>7}  {'HIT%':>6}  "
                 f"{'NEUTRAL':>7}  {'AVG SCORE':>9}  {'BAND':<15}")
    lines.append("  " + "─" * 70)
    for ticker, data in sorted(sector_results.items()):
        if data is None:
            lines.append(f"  {ticker:<8}  {'ERROR':>7}")
            continue
        s = data["summary"]
        acc   = f"{s['accuracy_pct']}%" if s["accuracy_pct"] is not None else "N/A"
        sigs  = s["directional_signals"]
        corr  = s["correct_signals"]
        neut  = s["total_periods"] - sigs
        scores = [p["experimental_score"] for p in data["periods"] if p["experimental_score"] is not None]
        avg_score = f"{sum(scores)/len(scores):.1f}" if scores else "N/A"
        bands  = [p["score_band"] for p in data["periods"] if p["score_band"]]
        common_band = max(set(bands), key=bands.count) if bands else "N/A"
        lines.append(f"  {ticker:<8}  {sigs:>7}  {corr:>7}  {acc:>6}  {neut:>7}  "
                     f"{avg_score:>9}  {common_band:<15}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Sector-wide 12-month backtest with confusion matrices.")
    parser.add_argument("--sector", help="Run only this sector (default: all five)")
    parser.add_argument("--data-source", default="yfinance", choices=["fmp", "yfinance"])
    parser.add_argument("--resume", action="store_true",
                        help="Skip tickers whose JSON result file already exists")
    parser.add_argument("--output-dir", default="sector_results",
                        help="Directory for per-ticker JSON files (default: sector_results/)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    sectors_to_run = (
        {args.sector: SECTORS[args.sector]}
        if args.sector and args.sector in SECTORS
        else SECTORS
    )

    total_tickers = sum(len(v) for v in sectors_to_run.values())
    print(f"\n{'='*64}")
    print(f"  SECTOR BACKTEST — 12 months (Mar 2025 – Feb 2026)")
    print(f"  Sectors: {len(sectors_to_run)}   Tickers: {total_tickers}")
    print(f"  Data source: {args.data_source}   Output: {output_dir}/")
    print(f"{'='*64}\n")

    all_results: Dict[str, Dict[str, Any]] = {}   # sector → {ticker → result}
    overall_matrix = _empty_matrix()

    for sector_name, tickers in sectors_to_run.items():
        print(f"\n►  {sector_name.upper()} ({len(tickers)} tickers)\n")
        sector_results: Dict[str, Any] = {}
        sector_matrix = _empty_matrix()

        for i, ticker in enumerate(tickers, 1):
            print(f"  {i}/{len(tickers)}", end=" ")
            result = run_ticker(ticker, args.data_source, args.resume, output_dir)
            sector_results[ticker] = result

            if result is not None:
                for period in result["periods"]:
                    _update_matrix(sector_matrix, period)
                    _update_matrix(overall_matrix, period)
            else:
                sector_matrix["errors"] += 1
                overall_matrix["errors"] += 1

            # Brief pause to avoid hammering yfinance
            time.sleep(0.5)

        all_results[sector_name] = sector_results

        # Per-sector ticker table
        print(_render_ticker_summary_table(sector_results))

        # Per-sector confusion matrix
        metrics = _matrix_metrics(sector_matrix)
        print(_render_matrix_table(metrics, sector_name.upper()))
        all_results[f"_matrix_{sector_name}"] = metrics

    # Overall confusion matrix
    overall_metrics = _matrix_metrics(overall_matrix)
    print(_render_matrix_table(overall_metrics, "ALL SECTORS COMBINED"))

    # Save consolidated outputs
    consolidated = {
        "meta": {
            "window": "Mar 2025 – Feb 2026",
            "months": 12,
            "sectors": len(sectors_to_run),
            "tickers": total_tickers,
            "data_source": args.data_source,
        },
        "sectors": {
            sector: {
                "tickers": results,
                "confusion_matrix": _matrix_metrics(
                    # recompute cleanly from stored periods
                    _build_matrix_from_results(results)
                ),
            }
            for sector, results in all_results.items()
            if not sector.startswith("_")
        },
        "overall_confusion_matrix": overall_metrics,
    }

    with open("sector_backtest_results.json", "w") as fh:
        json.dump(consolidated, fh, indent=2, default=str)
    print(f"\n✓  Full results saved to sector_backtest_results.json")

    # Concise confusion matrix JSON
    cm_output = {
        "meta": consolidated["meta"],
        "overall": overall_metrics,
        "by_sector": {
            sector: data["confusion_matrix"]
            for sector, data in consolidated["sectors"].items()
        },
    }
    with open("sector_confusion_matrix.json", "w") as fh:
        json.dump(cm_output, fh, indent=2)
    print(f"✓  Confusion matrices saved to sector_confusion_matrix.json")

    # ── Generate HTML dashboard ──────────────────────────────────────────
    try:
        from fundamental_agent.dashboard import generate_dashboard
        dashboard_path = generate_dashboard(
            results_json="sector_backtest_results.json",
            output_html="backtest_dashboard.html",
        )
        print(f"✓  Dashboard generated → {dashboard_path.resolve()}")
    except Exception as exc:
        print(f"⚠  Dashboard generation failed: {exc}")


def _build_matrix_from_results(sector_results: Dict[str, Any]) -> Dict[str, int]:
    m = _empty_matrix()
    for ticker_data in sector_results.values():
        if ticker_data is None:
            m["errors"] += 1
            continue
        for period in ticker_data["periods"]:
            _update_matrix(m, period)
    return m


if __name__ == "__main__":
    main()
