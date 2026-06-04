#!/usr/bin/env python3
"""
run_phoenix_orchestrator_backtest_2025.py
========================================
Monthly backtests for **Phoenix Agent** and **Orchestrator Agent** across:

  - Anchor (signal) dates: 2025-01-01, 2025-02-01, ..., 2025-12-01
  - Result dates: month-end (calendar end; data clients snap to last trading day)
  - Sectors: Technology + Energy
  - Universe: 10 tickers per sector (20 total)

Output:
  MyTradingSpace/data/output/backtests/phoenix_orchestrator_2025/
    phoenix_orchestrator_backtest_2025.xlsx
    phoenix_results.json
    orchestrator_results.json

Notes
-----
This is a *batch runner / exporter*. It intentionally reuses the existing
agent backtest engines:
  - agents.phoenix.backtest.run_monthly_backtest
  - agents.orchestrator.backtest.run_monthly_backtest

Phoenix signal semantics:
  BUY/WATCH/AVOID (WATCH treated as neutral for directional accuracy)

Orchestrator signal semantics:
  bullish/neutral/bearish (neutral excluded from directional accuracy)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from calendar import monthrange
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import paths  # noqa: E402


SECTOR_TICKERS: Dict[str, List[str]] = {
    # 10 per sector (matches the existing orchestrator sector backtest list)
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "ORCL", "ANET", "CRM"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "OXY", "PSX", "VLO", "MPC", "EOG", "HAL"],
}


def _months_2025_anchor_first_of_month() -> List[Tuple[date, date]]:
    months: List[Tuple[date, date]] = []
    for m in range(1, 13):
        signal_date = date(2025, m, 1)
        last_day = monthrange(2025, m)[1]
        result_date = date(2025, m, last_day)
        months.append((signal_date, result_date))
    return months


MONTHS_2025 = _months_2025_anchor_first_of_month()


@dataclass(frozen=True)
class TaskSpec:
    agent: str  # "phoenix" | "orchestrator"
    sector: str
    ticker: str


def _cache_path(out_dir: Path, agent: str, sector: str, ticker: str) -> Path:
    safe_sector = sector.replace("/", "_").replace(" ", "_")
    return out_dir / "cache" / agent / safe_sector / f"{ticker.upper()}.json"


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


def _flatten_phoenix_period(ticker: str, sector: str, period: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "agent": "phoenix",
        "sector": sector,
        "ticker": ticker,
        "signal_date": period.get("signal_date"),
        "result_date": period.get("result_date"),
        "signal": period.get("signal"),
        "score": period.get("score"),
        "stage": period.get("stage"),
        "pattern": period.get("pattern"),
        "hard_filter_passed": period.get("hard_filter_passed"),
        "entry_price": period.get("entry_price"),
        "stop_price": period.get("stop_price"),
        "target_1": period.get("target_1"),
        "reward_risk": period.get("reward_risk"),
        "signal_price": period.get("signal_price"),
        "result_price": period.get("result_price"),
        "pct_change": period.get("pct_change"),
        "actual_direction": period.get("actual_direction"),
        "signal_correct": period.get("signal_correct"),
    }


def _flatten_orchestrator_period(ticker: str, sector: str, period: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "agent": "orchestrator",
        "sector": sector,
        "ticker": ticker,
        "month": period.get("month"),
        "signal_date": period.get("signal_date"),
        "result_date": period.get("result_date"),
        "start_price": period.get("start_price"),
        "start_price_date": period.get("start_price_date"),
        "end_price": period.get("end_price"),
        "end_price_date": period.get("end_price_date"),
        "price_return_pct": period.get("price_return_pct"),
        "actual_direction": period.get("actual_direction"),
        "orchestrator_score": period.get("orchestrator_score"),
        "signal": period.get("signal"),
        "confidence": period.get("confidence"),
        "signal_correct": period.get("signal_correct"),
        "conflict_detected": period.get("conflict_detected"),
        "conflict_resolution": period.get("conflict_resolution"),
        "weights_tech": (period.get("weights_applied") or {}).get("tech"),
        "weights_fund": (period.get("weights_applied") or {}).get("fund"),
        "tech_score": period.get("tech_score"),
        "fund_score": period.get("fund_score"),
        "tech_error": period.get("tech_error"),
        "fund_error": period.get("fund_error"),
        "error": period.get("error"),
    }


def _run_phoenix_for_ticker(ticker: str, sector: str, months: List[Tuple[date, date]]) -> Dict[str, Any]:
    from agents.phoenix.backtest import run_monthly_backtest  # noqa: E402

    return run_monthly_backtest(ticker=ticker, months=months)


def _run_orchestrator_for_ticker(ticker: str, sector: str, months: List[Tuple[date, date]]) -> Dict[str, Any]:
    from agents.orchestrator.backtest import run_monthly_backtest  # noqa: E402

    return run_monthly_backtest(ticker=ticker, months=months)


def _build_summary(df_periods: pd.DataFrame, agent: str) -> pd.DataFrame:
    if df_periods.empty:
        return pd.DataFrame()

    correct_col = "signal_correct"
    score_col = "score" if agent == "phoenix" else "orchestrator_score"
    signal_col = "signal"

    def _directional_mask(d: pd.DataFrame) -> pd.Series:
        if agent == "phoenix":
            return d[signal_col].isin(["BUY", "AVOID"])
        return d[signal_col].isin(["bullish", "bearish"])

    def _acc(d: pd.DataFrame) -> Optional[float]:
        dm = _directional_mask(d)
        dd = d[dm]
        if dd.empty:
            return None
        # signal_correct can be bool or None
        vals = dd[correct_col].dropna()
        if vals.empty:
            return None
        return float(vals.mean() * 100.0)

    rows: List[Dict[str, Any]] = []
    for (sector, ticker), g in df_periods.groupby(["sector", "ticker"], dropna=False):
        dm = _directional_mask(g)
        dd = g[dm]
        directional = int(dd.shape[0])
        correct = int(dd[correct_col].fillna(False).sum()) if directional else 0
        acc = _acc(g)
        avg_score = None
        if score_col in g.columns:
            s = pd.to_numeric(g[score_col], errors="coerce").dropna()
            avg_score = float(s.mean()) if not s.empty else None

        rows.append(
            {
                "agent": agent,
                "sector": sector,
                "ticker": ticker,
                "months": int(g.shape[0]),
                "directional_signals": directional,
                "correct_signals": correct,
                "accuracy_pct": round(acc, 1) if acc is not None else None,
                "avg_score": round(avg_score, 2) if avg_score is not None else None,
            }
        )

    out = pd.DataFrame(rows).sort_values(["sector", "ticker"])
    return out


def _autofit_ish(writer: pd.ExcelWriter, sheet_names: List[str], max_rows: int = 2000) -> None:
    # Basic "autofit" for readability; avoids iterating huge sheets too long.
    book = writer.book
    for sn in sheet_names:
        if sn not in book.sheetnames:
            continue
        ws = book[sn]
        for col in ws.columns:
            try:
                col_letter = col[0].column_letter
            except Exception:
                continue
            max_len = 0
            for cell in col[: max_rows + 1]:
                v = "" if cell.value is None else str(cell.value)
                if len(v) > max_len:
                    max_len = len(v)
            ws.column_dimensions[col_letter].width = min(60, max(10, max_len + 2))
        ws.freeze_panes = "A2"


def _run_one_process(
    spec: TaskSpec,
    months: List[Tuple[date, date]],
    out_dir_str: str,
    resume: bool,
) -> Tuple[TaskSpec, Optional[Dict[str, Any]], Optional[str]]:
    """
    Process-safe worker entrypoint (must be module-level for pickling).
    Returns (spec, result, error).
    """
    out_dir = Path(out_dir_str)
    if resume:
        cp = _cache_path(out_dir, spec.agent, spec.sector, spec.ticker)
        cached = _load_cached(cp)
        if cached is not None:
            return spec, cached, None
    try:
        if spec.agent == "orchestrator":
            r = _run_orchestrator_for_ticker(spec.ticker, spec.sector, months)
            return spec, r, None
        if spec.agent == "phoenix":
            r = _run_phoenix_for_ticker(spec.ticker, spec.sector, months)
            return spec, r, None
        return spec, None, f"Unknown agent: {spec.agent}"
    except Exception as exc:
        return spec, None, str(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phoenix + Orchestrator monthly backtests for 2025 with Excel output.")
    parser.add_argument("--workers", type=int, default=6, help="Concurrency (default: 6).")
    parser.add_argument(
        "--sectors",
        default="Technology,Energy",
        help="Comma-separated sectors to run (default: Technology,Energy).",
    )
    parser.add_argument(
        "--tickers-per-sector",
        type=int,
        default=10,
        help="Tickers per sector (default: 10).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(paths.BACKTEST_DIR / "phoenix_orchestrator_2025"),
        help="Output directory for JSON + Excel.",
    )
    parser.add_argument(
        "--agents",
        default="both",
        choices=["phoenix", "orchestrator", "both"],
        help="Which agent backtests to run (default: both).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from per-ticker cache (skips completed tickers).",
    )
    parser.add_argument(
        "--orchestrator-processes",
        action="store_true",
        help="Run orchestrator in parallel processes (faster; recommended).",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sectors = [s.strip() for s in str(args.sectors).split(",") if s.strip()]
    if not sectors:
        raise SystemExit("No sectors provided.")

    tickers_per = max(1, int(args.tickers_per_sector))

    universe: List[Tuple[str, str]] = []
    for sec in sectors:
        if sec not in SECTOR_TICKERS:
            raise SystemExit(f"Sector not supported by this runner: {sec}")
        for t in SECTOR_TICKERS[sec][:tickers_per]:
            universe.append((sec, t))

    tasks: List[TaskSpec] = []
    for sec, t in universe:
        if args.agents in ("phoenix", "both"):
            tasks.append(TaskSpec(agent="phoenix", sector=sec, ticker=t))
        if args.agents in ("orchestrator", "both"):
            tasks.append(TaskSpec(agent="orchestrator", sector=sec, ticker=t))

    print()
    print("=" * 72)
    print("Phoenix + Orchestrator Backtests — 2025 (monthly anchors)")
    print(f"Sectors: {', '.join(sectors)}  |  Tickers: {len(universe)}  |  Months: {len(MONTHS_2025)}")
    print(f"Agents: {args.agents}  |  Workers: {args.workers}")
    print(f"Output: {out_dir}")
    print("=" * 72)

    phoenix_results: Dict[str, Any] = {}
    orchestrator_results: Dict[str, Any] = {}

    t0 = time.time()

    completed = 0
    errors = 0

    # Split pools: orchestrator uses processes (recommended), phoenix uses threads.
    orch_specs = [s for s in tasks if s.agent == "orchestrator"]
    phx_specs = [s for s in tasks if s.agent == "phoenix"]

    if orch_specs:
        use_procs = bool(args.orchestrator_processes) or args.agents == "orchestrator"
        if use_procs:
            with ProcessPoolExecutor(max_workers=int(args.workers)) as pool:
                futs = [
                    pool.submit(_run_one_process, spec, MONTHS_2025, str(out_dir), bool(args.resume))
                    for spec in orch_specs
                ]
                for fut in as_completed(futs):
                    spec, res, err = fut.result()
                    completed += 1
                    if err:
                        errors += 1
                        print(f"  ✗ orchestrator  {spec.ticker:<6} [{spec.sector}] ERROR: {err[:140]}", flush=True)
                        continue
                    orchestrator_results[f"{spec.sector}:{spec.ticker}"] = res
                    if res is not None:
                        _save_cached(_cache_path(out_dir, "orchestrator", spec.sector, spec.ticker), res)
                    s = (res or {}).get("summary") or {}
                    acc = s.get("accuracy_pct")
                    acc_s = f"{acc:.1f}%" if isinstance(acc, (int, float)) else "N/A"
                    print(f"  ✓ orchestrator  {spec.ticker:<6} [{spec.sector}] acc={acc_s}", flush=True)
        else:
            with ThreadPoolExecutor(max_workers=int(args.workers)) as pool:
                futs = [
                    pool.submit(_run_one_process, spec, MONTHS_2025, str(out_dir), bool(args.resume))
                    for spec in orch_specs
                ]
                for fut in as_completed(futs):
                    spec, res, err = fut.result()
                    completed += 1
                    if err:
                        errors += 1
                        print(f"  ✗ orchestrator  {spec.ticker:<6} [{spec.sector}] ERROR: {err[:140]}", flush=True)
                        continue
                    orchestrator_results[f"{spec.sector}:{spec.ticker}"] = res
                    if res is not None:
                        _save_cached(_cache_path(out_dir, "orchestrator", spec.sector, spec.ticker), res)
                    s = (res or {}).get("summary") or {}
                    acc = s.get("accuracy_pct")
                    acc_s = f"{acc:.1f}%" if isinstance(acc, (int, float)) else "N/A"
                    print(f"  ✓ orchestrator  {spec.ticker:<6} [{spec.sector}] acc={acc_s}", flush=True)

    if phx_specs:
        with ThreadPoolExecutor(max_workers=int(args.workers)) as pool:
            futs = [
                pool.submit(_run_one_process, spec, MONTHS_2025, str(out_dir), bool(args.resume))
                for spec in phx_specs
            ]
            for fut in as_completed(futs):
                spec, res, err = fut.result()
                completed += 1
                if err:
                    errors += 1
                    print(f"  ✗ phoenix       {spec.ticker:<6} [{spec.sector}] ERROR: {err[:140]}", flush=True)
                    continue
                phoenix_results[f"{spec.sector}:{spec.ticker}"] = res
                if res is not None:
                    _save_cached(_cache_path(out_dir, "phoenix", spec.sector, spec.ticker), res)
                s = (res or {}).get("summary") or {}
                acc = s.get("accuracy_pct")
                acc_s = f"{acc:.1f}%" if isinstance(acc, (int, float)) else "N/A"
                print(f"  ✓ phoenix       {spec.ticker:<6} [{spec.sector}] acc={acc_s}", flush=True)

    elapsed = time.time() - t0
    print()
    print("=" * 72)
    print(f"Done in {elapsed:.1f}s  |  Tasks: {len(tasks)}  |  Errors: {errors}")
    print("=" * 72)

    # Save raw JSON outputs
    phoenix_json_path = out_dir / "phoenix_results.json"
    orch_json_path = out_dir / "orchestrator_results.json"
    phoenix_json_path.write_text(json.dumps(phoenix_results, indent=2, default=str))
    orch_json_path.write_text(json.dumps(orchestrator_results, indent=2, default=str))

    # Build flattened period tables
    phoenix_rows: List[Dict[str, Any]] = []
    for k, r in phoenix_results.items():
        if not r:
            continue
        sec, tkr = k.split(":", 1)
        for p in r.get("periods", []):
            phoenix_rows.append(_flatten_phoenix_period(tkr, sec, p))
    orch_rows: List[Dict[str, Any]] = []
    for k, r in orchestrator_results.items():
        if not r:
            continue
        sec, tkr = k.split(":", 1)
        for p in r.get("periods", []):
            orch_rows.append(_flatten_orchestrator_period(tkr, sec, p))

    df_phx = pd.DataFrame(phoenix_rows)
    df_orch = pd.DataFrame(orch_rows)
    df_phx_summary = _build_summary(df_phx, agent="phoenix") if not df_phx.empty else pd.DataFrame()
    df_orch_summary = _build_summary(df_orch, agent="orchestrator") if not df_orch.empty else pd.DataFrame()

    # Meta sheet
    meta_rows = [
        {"key": "window", "value": "Jan 2025 – Dec 2025"},
        {"key": "months", "value": ", ".join([d.isoformat() for d, _ in MONTHS_2025])},
        {"key": "sectors", "value": ", ".join(sectors)},
        {"key": "tickers", "value": ", ".join([t for _, t in universe])},
        {"key": "agents", "value": args.agents},
        {"key": "workers", "value": int(args.workers)},
        {"key": "elapsed_sec", "value": round(elapsed, 1)},
        {"key": "errors", "value": errors},
        {"key": "phoenix_json", "value": str(phoenix_json_path)},
        {"key": "orchestrator_json", "value": str(orch_json_path)},
    ]
    df_meta = pd.DataFrame(meta_rows)

    # Excel export
    xlsx_path = out_dir / "phoenix_orchestrator_backtest_2025.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df_meta.to_excel(writer, sheet_name="Meta", index=False)
        if not df_phx_summary.empty:
            df_phx_summary.to_excel(writer, sheet_name="Phoenix Summary", index=False)
        if not df_orch_summary.empty:
            df_orch_summary.to_excel(writer, sheet_name="Orchestrator Summary", index=False)
        if not df_phx.empty:
            df_phx.to_excel(writer, sheet_name="Phoenix Periods", index=False)
        if not df_orch.empty:
            df_orch.to_excel(writer, sheet_name="Orchestrator Periods", index=False)

        _autofit_ish(
            writer,
            sheet_names=[
                "Meta",
                "Phoenix Summary",
                "Orchestrator Summary",
                "Phoenix Periods",
                "Orchestrator Periods",
            ],
        )

    print(f"Wrote Excel: {xlsx_path}")
    print(f"Wrote JSON : {phoenix_json_path}")
    print(f"Wrote JSON : {orch_json_path}")


if __name__ == "__main__":
    main()

