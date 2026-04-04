#!/usr/bin/env python3
"""
run_oneil.py — O'Neil CAN SLIM sector backtest runner.

12 months (Mar 2025 – Feb 2026) × 50 tickers (5 sectors × 10) = 600 data points.
Parallel via ThreadPoolExecutor (8 workers, IO-bound — yfinance end-price fetches).

Data: Polygon.io OHLCV bars (US only, fetched once per ticker), yfinance fallback.

Outputs (all written to --output-dir, default: oneil_results/)
─────────────────────────────────────────────────────────────
  {TICKER}_oneil_backtest_results.json   — per-ticker full backtest data
  oneil_sector_backtest_results.json     — combined raw results for all tickers
  oneil_sector_confusion_matrix.json     — confusion matrix + O'Neil pattern metrics

Usage
─────
    python backtests/run_oneil.py
    python backtests/run_oneil.py --sector Technology
    python backtests/run_oneil.py --ticker AAPL
    python backtests/run_oneil.py --resume
    python backtests/run_oneil.py --workers 4
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make project root importable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paths
from backtests.common import (
    ALL_TICKERS, MONTHS, SECTORS,
    empty_matrix, matrix_metrics, print_matrix, update_matrix,
)
from agents.oneil.backtest import build_backtest_report, run_monthly_backtest


# ─────────────────────────────────────────────────────────────────────────────
# Per-ticker worker
# ─────────────────────────────────────────────────────────────────────────────

def _run_ticker(
    ticker: str,
    resume: bool,
    output_dir: Path,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Run (or resume from cache) a 12-month O'Neil backtest for *ticker*."""
    cache = output_dir / f"{ticker}_oneil_backtest_results.json"

    if resume and cache.exists():
        print(f"    [{ticker}] ← resumed from cache", flush=True)
        return ticker, json.loads(cache.read_text())

    try:
        result = run_monthly_backtest(ticker=ticker, months=MONTHS, exchange="US")
        cache.write_text(json.dumps(result, indent=2))
        s   = result["summary"]
        acc = f"{s['accuracy_pct']:.1f}%" if s.get("accuracy_pct") is not None else "N/A"
        dir_str = f"{s['directional_signals']}/{s['total_periods']}"
        print(f"    ✓ {ticker:<6}  dir={dir_str}  acc={acc}", flush=True)
        return ticker, result
    except Exception as exc:
        print(f"    ✗ {ticker:<6}  ERROR: {exc}", flush=True)
        return ticker, None


# ─────────────────────────────────────────────────────────────────────────────
# O'Neil-specific aggregate: pattern stats across all tickers
# ─────────────────────────────────────────────────────────────────────────────

def _aggregate_pattern_stats(
    all_results: Dict[str, Optional[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Aggregate pattern-recognition metrics across the full sector universe.

    Returns a dict keyed by pattern name (or "No Pattern") with:
      total, directional, correct, accuracy_pct
    """
    combined: Dict[str, Dict[str, int]] = {}

    for ticker_data in all_results.values():
        if not ticker_data:
            continue
        for p in ticker_data.get("periods", []):
            pat     = p.get("pattern_detected")
            pat_key = pat.split("—")[0].strip() if pat else "No Pattern"
            if pat_key not in combined:
                combined[pat_key] = {"total": 0, "directional": 0, "correct": 0}
            s = combined[pat_key]
            s["total"] += 1
            if p.get("signal_correct") is not None:
                s["directional"] += 1
            if p.get("signal_correct"):
                s["correct"] += 1

    return {
        name: {
            **s,
            "accuracy_pct": round(s["correct"] / s["directional"] * 100, 1) if s["directional"] else None,
        }
        for name, s in sorted(combined.items(), key=lambda kv: kv[1]["total"], reverse=True)
    }


def _aggregate_stage_stats(
    all_results: Dict[str, Optional[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Aggregate hit rate by Weinstein market stage."""
    combined: Dict[int, Dict[str, int]] = {}

    for ticker_data in all_results.values():
        if not ticker_data:
            continue
        for p in ticker_data.get("periods", []):
            st = p.get("market_stage", 0)
            if st not in combined:
                combined[st] = {"total": 0, "directional": 0, "correct": 0}
            s = combined[st]
            s["total"] += 1
            if p.get("signal_correct") is not None:
                s["directional"] += 1
            if p.get("signal_correct"):
                s["correct"] += 1

    stage_labels = {
        1: "Stage 1 — Basing", 2: "Stage 2 — Uptrend",
        3: "Stage 3 — Distribution", 4: "Stage 4 — Decline",
    }
    return {
        stage_labels.get(st, f"Stage {st}"): {
            **s,
            "accuracy_pct": round(s["correct"] / s["directional"] * 100, 1) if s["directional"] else None,
        }
        for st, s in sorted(combined.items())
    }


def _aggregate_late_early(
    all_results: Dict[str, Optional[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Compute late-stage vs early-stage accuracy across the universe."""
    late_d = late_c = early_d = early_c = 0

    for ticker_data in all_results.values():
        if not ticker_data:
            continue
        for p in ticker_data.get("periods", []):
            if p.get("signal_correct") is None:
                continue
            if p.get("is_late_stage"):
                late_d += 1
                if p["signal_correct"]:
                    late_c += 1
            elif p.get("pattern_detected"):
                early_d += 1
                if p["signal_correct"]:
                    early_c += 1

    return {
        "late_stage":  {
            "directional": late_d,
            "correct": late_c,
            "accuracy_pct": round(late_c / late_d * 100, 1) if late_d else None,
        },
        "early_stage": {
            "directional": early_d,
            "correct": early_c,
            "accuracy_pct": round(early_c / early_d * 100, 1) if early_d else None,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="O'Neil CAN SLIM sector backtest — 50 tickers × 12 months"
    )
    parser.add_argument("--sector",     default=None, help="Run one sector only (e.g. Technology)")
    parser.add_argument("--ticker",     default=None, help="Run a single ticker")
    parser.add_argument("--resume",     action="store_true", help="Skip tickers with cached JSON files")
    parser.add_argument("--workers",    type=int, default=8, help="Parallel workers (default 8)")
    parser.add_argument("--output-dir", default=str(paths.BACKTEST_DIR / "oneil"), help="Output directory for JSON files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build ticker list
    if args.ticker:
        tickers_to_run = [args.ticker.upper()]
    elif args.sector:
        if args.sector not in SECTORS:
            print(f"ERROR: Unknown sector '{args.sector}'. Options: {list(SECTORS)}", file=sys.stderr)
            sys.exit(1)
        tickers_to_run = SECTORS[args.sector]
    else:
        tickers_to_run = ALL_TICKERS

    total = len(tickers_to_run)
    print(f"\n{'═'*60}")
    print(f"  O'Neil CAN SLIM Sector Backtest")
    print(f"  Tickers  : {total}")
    print(f"  Months   : {len(MONTHS)} (Mar 2025 – Feb 2026)")
    print(f"  Workers  : {args.workers}")
    print(f"  Resume   : {args.resume}")
    print(f"  Output   : {output_dir.resolve()}")
    print(f"{'═'*60}\n")

    all_results: Dict[str, Optional[Dict[str, Any]]] = {}
    t0 = time.time()

    # Sector-by-sector progress
    if args.sector:
        sector_map = {args.sector: SECTORS[args.sector]}
    else:
        sector_map = SECTORS

    for sector, sector_tickers in sector_map.items():
        run_these = [t for t in sector_tickers if t in tickers_to_run]
        if not run_these:
            continue
        print(f"\n▶  {sector}  ({len(run_these)} tickers)")

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            fut_map = {
                pool.submit(_run_ticker, ticker, args.resume, output_dir): ticker
                for ticker in run_these
            }
            for fut in as_completed(fut_map):
                ticker, result = fut.result()
                all_results[ticker] = result

    elapsed = time.time() - t0
    print(f"\n{'─'*60}")
    print(f"  Completed in {elapsed:.0f}s. Building aggregate metrics…")

    # ── Aggregate confusion matrix ────────────────────────────────────────
    overall_m = empty_matrix()
    sector_matrices: Dict[str, Any] = {}

    for sector, sector_tickers in SECTORS.items():
        sm = empty_matrix()
        for ticker in sector_tickers:
            td = all_results.get(ticker)
            if not td:
                sm["errors"] += 1
                overall_m["errors"] += 1
                continue
            for p in td.get("periods", []):
                update_matrix(sm, p)
                update_matrix(overall_m, p)
        sector_matrices[sector] = matrix_metrics(sm)

    overall_metrics = matrix_metrics(overall_m)

    # ── Pattern & stage stats ─────────────────────────────────────────────
    pattern_stats = _aggregate_pattern_stats(all_results)
    stage_stats   = _aggregate_stage_stats(all_results)
    late_early    = _aggregate_late_early(all_results)

    confusion_output = {
        "overall":              overall_metrics,
        "by_sector":            sector_matrices,
        "pattern_recognition":  pattern_stats,
        "stage_analysis":       stage_stats,
        "late_vs_early_stage":  late_early,
    }

    # ── Write output files ────────────────────────────────────────────────
    combined_path = output_dir / "oneil_sector_backtest_results.json"
    matrix_path   = output_dir / "oneil_sector_confusion_matrix.json"

    combined_path.write_text(json.dumps(all_results, indent=2, default=str))
    matrix_path.write_text(json.dumps(confusion_output, indent=2))
    print(f"  Wrote: {combined_path}")
    print(f"  Wrote: {matrix_path}")

    # ── Print confusion matrices ──────────────────────────────────────────
    print_matrix(overall_metrics, "OVERALL  (50 tickers × 12 months)")
    for sector, sm in sector_matrices.items():
        print_matrix(sm, f"{sector}")

    # ── Print pattern recognition results ────────────────────────────────
    print(f"\n{'─'*60}")
    print("  PATTERN RECOGNITION ACCURACY")
    print(f"{'─'*60}")
    print(f"  {'Pattern':<35} {'Dir/Total':>10}  {'Accuracy':>10}")
    print(f"  {'─'*35} {'─'*10}  {'─'*10}")
    for name, ps in pattern_stats.items():
        acc_s = f"{ps['accuracy_pct']:.1f}%" if ps["accuracy_pct"] is not None else "N/A"
        print(f"  {name:<35} {ps['directional']:>5}/{ps['total']:<5}  {acc_s:>10}")

    # ── Stage accuracy ────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("  ACCURACY BY WEINSTEIN STAGE")
    print(f"{'─'*60}")
    for stage_name, ss in stage_stats.items():
        acc_s = f"{ss['accuracy_pct']:.1f}%" if ss["accuracy_pct"] is not None else "N/A"
        print(f"  {stage_name:<35} {ss['directional']:>5}/{ss['total']:<5}  {acc_s:>10}")

    # ── Late vs Early ─────────────────────────────────────────────────────
    le = late_early
    print(f"\n  Late-stage accuracy : {le['late_stage']['accuracy_pct'] or 'N/A'}%"
          f"  ({le['late_stage']['directional']} directional signals)")
    print(f"  Early-stage accuracy: {le['early_stage']['accuracy_pct'] or 'N/A'}%"
          f"  ({le['early_stage']['directional']} directional signals)")
    print()


if __name__ == "__main__":
    main()
