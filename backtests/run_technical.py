#!/usr/bin/env python3
"""
run_technical.py — Canonical Technical Agent sector backtest runner.

12 months (Mar 2025 – Feb 2026) × 50 tickers (5 sectors × 10).
Delegates to technical_agent.backtest for the core engine.

Usage
─────
    python backtests/run_technical.py
    python backtests/run_technical.py --sector Technology
    python backtests/run_technical.py --resume
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtests.common import (
    ALL_TICKERS, MONTHS, SECTORS,
    empty_matrix, matrix_metrics, print_matrix, update_matrix,
)
from technical_agent.backtest import run_monthly_backtest


def _run_ticker(
    ticker: str, resume: bool, output_dir: Path,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    cache = output_dir / f"{ticker}_technical_backtest_results.json"
    if resume and cache.exists():
        print(f"    [{ticker}] ← resumed", flush=True)
        return ticker, json.loads(cache.read_text())
    try:
        result = run_monthly_backtest(ticker=ticker, months=MONTHS)
        cache.write_text(json.dumps(result, indent=2, default=str))
        s = result["summary"]
        acc = f"{s['accuracy_pct']:.1f}%" if s.get("accuracy_pct") is not None else "N/A"
        print(f"    ✓ {ticker:<6}  dir={s['directional_signals']}/{s['total_periods']}  acc={acc}", flush=True)
        return ticker, result
    except Exception as exc:
        print(f"    ✗ {ticker:<6}  ERROR: {exc}", flush=True)
        return ticker, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Technical Agent sector backtest")
    parser.add_argument("--sector",     default=None)
    parser.add_argument("--resume",     action="store_true")
    parser.add_argument("--workers",    type=int, default=8)
    parser.add_argument("--output-dir", default="technical_results")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sector_map = {args.sector: SECTORS[args.sector]} if args.sector else SECTORS
    print(f"\nTechnical Agent Sector Backtest — {sum(len(v) for v in sector_map.values())} tickers × {len(MONTHS)} months")

    all_results: Dict[str, Any] = {}
    t0 = time.time()
    for sector, sector_tickers in sector_map.items():
        print(f"\n▶  {sector}")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            fut_map = {pool.submit(_run_ticker, t, args.resume, output_dir): t for t in sector_tickers}
            for fut in as_completed(fut_map):
                ticker, result = fut.result()
                all_results[ticker] = result

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
    (output_dir / "technical_sector_backtest_results.json").write_text(json.dumps(all_results, indent=2, default=str))
    (output_dir / "technical_sector_confusion_matrix.json").write_text(json.dumps({"overall": overall, "by_sector": sector_matrices}, indent=2))

    print_matrix(overall, "OVERALL")
    for sector, sm in sector_matrices.items():
        print_matrix(sm, sector)
    print(f"\nDone in {time.time()-t0:.0f}s\n")


if __name__ == "__main__":
    main()
