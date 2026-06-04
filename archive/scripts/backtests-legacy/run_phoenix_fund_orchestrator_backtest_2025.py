#!/usr/bin/env python3
"""
run_phoenix_fund_orchestrator_backtest_2025.py
=============================================
Backtest the **Phoenix + Fundamental Orchestrator** across calendar year 2025:

  - Monthly anchors: 2025-01-01, 2025-02-01, ..., 2025-12-01
  - Evaluation window: +30 calendar days after signal_date.
  - Sectors: Technology + Energy
  - Universe: 10 tickers per sector (20 total)

Runs in **parallel (processes)** across tickers for speed and writes:
  - per-ticker cache JSON
  - consolidated results JSON
  - Excel workbook (summary + periods)
  - cumulative confusion matrix (overall + by sector)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import paths  # noqa: E402


HALAL_SECTOR_TICKERS = paths.HALAL_UNIVERSE / "halal_sector_tickers.json"


def _clean_ticker(t: str) -> Optional[str]:
    t = (t or "").strip().upper()
    if not t:
        return None
    # Skip weird tickers (spaces / WI / etc.)
    if " " in t or len(t) > 6:
        return None
    return t


def load_universe_it_energy(total: int = 150) -> Dict[str, List[str]]:
    """
    Build a ticker universe for:
      - Information Technology
      - Energy

    Uses the repo's halal sector list. Selection policy:
      - Take as many Energy tickers as available (up to total).
      - Fill the remainder from Information Technology.
    """
    raw: Dict[str, List[str]] = json.loads(HALAL_SECTOR_TICKERS.read_text())
    energy_raw = raw.get("Energy") or []
    it_raw = raw.get("Information Technology") or []

    energy = []
    seen = set()
    for t in energy_raw:
        tt = _clean_ticker(t)
        if not tt or tt in seen:
            continue
        seen.add(tt)
        energy.append(tt)
        if len(energy) >= total:
            break

    remaining = max(0, total - len(energy))
    it = []
    for t in it_raw:
        tt = _clean_ticker(t)
        if not tt or tt in seen:
            continue
        seen.add(tt)
        it.append(tt)
        if len(it) >= remaining:
            break

    return {"Information Technology": it, "Energy": energy}


def _months_2025() -> List[Tuple[date, date]]:
    months: List[Tuple[date, date]] = []
    for m in range(1, 13):
        signal_date = date(2025, m, 1)
        # evaluation window end = signal_date + 30 calendar days
        months.append((signal_date, signal_date + timedelta(days=30)))
    return months


MONTHS_2025 = _months_2025()


@dataclass(frozen=True)
class TickerTask:
    sector: str
    ticker: str


def _cache_path(out_dir: Path, sector: str, ticker: str) -> Path:
    return out_dir / "cache" / sector / f"{ticker.upper()}.json"


def _load_cached(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        return None
    return None


def _save_cached(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str))


def _run_one(
    task: TickerTask,
    out_dir_str: str,
    resume: bool,
    period_workers: int,
) -> Tuple[TickerTask, Optional[Dict[str, Any]], Optional[str]]:
    out_dir = Path(out_dir_str)
    cp = _cache_path(out_dir, task.sector, task.ticker)
    if resume:
        cached = _load_cached(cp)
        if cached is not None:
            return task, cached, None
    try:
        from agents.orchestrator.backtest_phoenix import run_monthly_backtest

        r = run_monthly_backtest(
            ticker=task.ticker,
            months=MONTHS_2025,
            period_workers=max(1, int(period_workers)),
        )
        _save_cached(cp, r)
        return task, r, None
    except Exception as exc:
        return task, None, str(exc)


def _confusion_from_periods(df: pd.DataFrame) -> Dict[str, Any]:
    TP = FP = TN = FN = neutral = errors = 0
    for _, r in df.iterrows():
        sig = r.get("signal")
        corr = r.get("signal_correct")
        if pd.isna(corr):
            neutral += 1
            continue
        corr = bool(corr)
        if sig not in ("bullish", "bearish"):
            neutral += 1
            continue
        # We evaluate correctness against 30-day target-hit.
        # signal_correct is already computed in the backtest engine using target_hit.
        if sig == "bullish" and corr is True:
            TP += 1
        elif sig == "bullish" and corr is False:
            FP += 1
        elif sig == "bearish" and corr is True:
            TN += 1
        elif sig == "bearish" and corr is False:
            FN += 1
        else:
            errors += 1

    directional = TP + FP + TN + FN
    correct = TP + TN

    def pct(v):
        return round(v * 100, 1) if v is not None else None

    acc = correct / directional if directional else None
    prec = TP / (TP + FP) if (TP + FP) else None
    rec = TP / (TP + FN) if (TP + FN) else None
    spec = TN / (TN + FP) if (TN + FP) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec is not None and rec is not None and (prec + rec) > 0) else None
    abst = neutral / (neutral + directional) if (neutral + directional) else None

    return {
        "TP": TP,
        "FP": FP,
        "TN": TN,
        "FN": FN,
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Phoenix+Fund Orchestrator backtest (2025 monthly) with confusion matrix.")
    parser.add_argument("--workers", type=int, default=6, help="Parallel processes (default: 6).")
    parser.add_argument("--resume", action="store_true", help="Resume from per-ticker cache.")
    parser.add_argument(
        "--executor",
        choices=["thread", "process"],
        default="thread",
        help="Parallelism mode. 'thread' is more stable for network-bound workloads (default).",
    )
    parser.add_argument(
        "--total-tickers",
        type=int,
        default=150,
        help="Total tickers across IT+Energy (default: 150).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(paths.BACKTEST_DIR / "phoenix_fund_orchestrator_2025_large"),
        help="Output directory.",
    )
    parser.add_argument(
        "--period-workers",
        type=int,
        default=1,
        help="Parallel month evaluations per ticker (threads; default 1). Use ~8–12 to speed up.",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    universe = load_universe_it_energy(total=max(1, int(args.total_tickers)))
    tasks: List[TickerTask] = []
    for sector, tickers in universe.items():
        for t in tickers:
            tasks.append(TickerTask(sector=sector, ticker=t))

    print()
    print("=" * 72)
    print("PHOENIX + FUND ORCHESTRATOR BACKTEST — 2025 (monthly anchors)")
    print(
        f"Tickers: {len(tasks)}  |  Months: {len(MONTHS_2025)}  |  Workers: {args.workers}",
        flush=True,
    )
    print(f"Period workers / ticker : {max(1, int(args.period_workers))}", flush=True)
    print(f"Output : {out_dir}")
    print("=" * 72)

    t0 = time.time()
    results: Dict[str, Any] = {}
    errors = 0

    Executor = ThreadPoolExecutor if args.executor == "thread" else ProcessPoolExecutor
    with Executor(max_workers=int(args.workers)) as pool:
        futs = [
            pool.submit(
                _run_one,
                task,
                str(out_dir),
                bool(args.resume),
                int(args.period_workers),
            )
            for task in tasks
        ]
        for fut in as_completed(futs):
            task, res, err = fut.result()
            key = f"{task.sector}:{task.ticker}"
            if err:
                errors += 1
                print(f"  ✗ {task.ticker:<6} [{task.sector}] ERROR: {err[:140]}", flush=True)
                continue
            results[key] = res
            s = (res or {}).get("summary") or {}
            acc = s.get("accuracy_pct")
            acc_s = f"{acc:.1f}%" if isinstance(acc, (int, float)) else "N/A"
            print(f"  ✓ {task.ticker:<6} [{task.sector}] acc={acc_s}", flush=True)

    elapsed = time.time() - t0
    print()
    print("=" * 72)
    print(f"Done in {elapsed:.1f}s | Errors: {errors}")
    print("=" * 72)

    # Consolidate JSON
    results_path = out_dir / "phoenix_fund_orchestrator_results.json"
    results_path.write_text(json.dumps(results, indent=2, default=str))

    # Flatten periods
    rows: List[Dict[str, Any]] = []
    for key, r in results.items():
        if not r:
            continue
        sector, ticker = key.split(":", 1)
        for p in r.get("periods", []):
            rows.append(
                {
                    "sector": sector,
                    "ticker": ticker,
                    "month": p.get("month"),
                    "signal_date": p.get("signal_date"),
                    "result_date": p.get("result_date"),
                    "signal": p.get("signal"),
                    "orchestrator_score": p.get("orchestrator_score"),
                    "confidence": p.get("confidence"),
                    "phoenix_score": p.get("phoenix_score"),
                    "fund_score": p.get("fund_score"),
                    "target_price": p.get("target_price"),
                    "target_hit": p.get("target_hit"),
                    "target_hit_date": p.get("target_hit_date"),
                    "target_eval_error": p.get("target_eval_error"),
                    "signal_correct": p.get("signal_correct"),
                    "conflict_detected": p.get("conflict_detected"),
                }
            )
    df = pd.DataFrame(rows)

    # Summary per ticker
    sum_rows: List[Dict[str, Any]] = []
    for key, r in sorted(results.items()):
        if not r:
            continue
        sector, ticker = key.split(":", 1)
        s = r.get("summary") or {}
        sum_rows.append(
            {
                "sector": sector,
                "ticker": ticker,
                "directional_signals": s.get("directional_signals"),
                "correct_signals": s.get("correct_signals"),
                "accuracy_pct": s.get("accuracy_pct"),
            }
        )
    df_sum = pd.DataFrame(sum_rows)

    # Confusion matrices (cumulative)
    cm_overall = _confusion_from_periods(df) if not df.empty else {}
    cm_by_sector = {sec: _confusion_from_periods(g) for sec, g in df.groupby("sector")} if not df.empty else {}
    cm_payload = {
        "meta": {
            "window": "Jan 2025 – Dec 2025 (monthly anchors)",
            "tickers": len(tasks),
            "months": [d.isoformat() for d, _ in MONTHS_2025],
            "elapsed_sec": round(elapsed, 1),
            "errors": errors,
            "results_json": str(results_path),
            "executor": str(args.executor),
            "workers": int(args.workers),
            "period_workers": max(1, int(args.period_workers)),
        },
        "cumulative": {
            "overall": cm_overall,
            "by_sector": cm_by_sector,
        },
    }
    cm_json_path = out_dir / "cumulative_confusion_matrix.json"
    cm_json_path.write_text(json.dumps(cm_payload, indent=2))

    # Excel
    xlsx_path = out_dir / "phoenix_fund_orchestrator_backtest_2025.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        pd.DataFrame(list(cm_payload["meta"].items()), columns=["key", "value"]).to_excel(w, sheet_name="Meta", index=False)
        df_sum.to_excel(w, sheet_name="Summary", index=False)
        df.to_excel(w, sheet_name="Periods", index=False)
        # Confusion matrix sheet
        cm_rows = [{"scope": "overall", "sector": "ALL", **cm_overall}]
        for sec, met in cm_by_sector.items():
            cm_rows.append({"scope": "sector", "sector": sec, **met})
        pd.DataFrame(cm_rows).to_excel(w, sheet_name="Cumulative CM", index=False)

    print(f"Wrote results JSON: {results_path}")
    print(f"Wrote CM JSON     : {cm_json_path}")
    print(f"Wrote Excel       : {xlsx_path}")


if __name__ == "__main__":
    main()

