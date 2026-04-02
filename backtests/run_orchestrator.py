#!/usr/bin/env python3
"""
run_orchestrator.py — Canonical Orchestrator (CWAF) sector backtest runner.

12 months (Mar 2025 – Feb 2026) × 50 tickers (5 sectors × 10).
Delegates to orchestrator_agent.backtest for the core CWAF fusion logic.

Usage
─────
    python backtests/run_orchestrator.py
    python backtests/run_orchestrator.py --sector Technology
    python backtests/run_orchestrator.py --resume
    python backtests/run_orchestrator.py --workers 6
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtests.common import (
    ALL_TICKERS, MONTHS, SECTORS,
    empty_matrix, matrix_metrics, print_matrix, update_matrix,
)


def _run_ticker(ticker: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Worker function — must be importable at module level for ProcessPoolExecutor."""
    from orchestrator_agent.backtest import run_monthly_backtest
    try:
        result = run_monthly_backtest(ticker=ticker, months=MONTHS)
        s = result["summary"]
        acc = f"{s['accuracy_pct']:.1f}%" if s.get("accuracy_pct") is not None else "N/A"
        print(f"    ✓ {ticker:<6}  dir={s['directional_signals']}/{s['total_periods']}  acc={acc}", flush=True)
        return ticker, result
    except Exception as exc:
        print(f"    ✗ {ticker:<6}  ERROR: {exc}", flush=True)
        return ticker, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrator CWAF sector backtest")
    parser.add_argument("--sector",     default=None)
    parser.add_argument("--resume",     action="store_true")
    parser.add_argument("--workers",    type=int, default=6)
    parser.add_argument("--output-dir", default="orchestrator_results")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sector_map = {args.sector: SECTORS[args.sector]} if args.sector else SECTORS
    tickers    = [t for s in sector_map.values() for t in s]
    print(f"\nOrchestrator CWAF Sector Backtest — {len(tickers)} tickers × {len(MONTHS)} months")

    all_results: Dict[str, Any] = {}
    t0 = time.time()

    # ProcessPoolExecutor for CPU-bound CWAF fusion
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        fut_map = {pool.submit(_run_ticker, t): t for t in tickers}
        for fut in as_completed(fut_map):
            ticker, result = fut.result()
            all_results[ticker] = result
            if result:
                (output_dir / f"{ticker}_orchestrator_backtest_results.json").write_text(
                    json.dumps(result, indent=2, default=str)
                )

    m = empty_matrix()
    sector_matrices = {}
    for sector, tickers in SECTORS.items():
        sm = empty_matrix()
        for t in tickers:
            td = all_results.get(t)
            if not td:
                sm["errors"] += 1; m["errors"] += 1; continue
            for p in td.get("periods", []):
                update_matrix(sm, p); update_matrix(m, p)
        sector_matrices[sector] = matrix_metrics(sm)

    overall = matrix_metrics(m)
    (output_dir / "orchestrator_sector_backtest_results.json").write_text(json.dumps(all_results, indent=2, default=str))
    (output_dir / "orchestrator_sector_confusion_matrix.json").write_text(json.dumps({"overall": overall, "by_sector": sector_matrices}, indent=2))

    print_matrix(overall, "OVERALL")
    for sector, sm in sector_matrices.items():
        print_matrix(sm, sector)
    print(f"\nDone in {time.time()-t0:.0f}s\n")


if __name__ == "__main__":
    main()
