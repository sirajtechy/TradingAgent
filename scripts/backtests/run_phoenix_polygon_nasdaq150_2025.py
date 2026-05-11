#!/usr/bin/env python3
"""
run_phoenix_polygon_nasdaq150_2025.py
=====================================
Calendar 2025 monthly Phoenix + Fund orchestrator backtest:

  - Monthly anchors Jan–Dec 2025; outcome window signal_date + 30 days.
  - Universe: 150 tickers = top 50 by market_cap per sector among **NASDAQ**
    listings in halal_master.json:
      Health Care | Industrials | Information Technology
  - Polygon-only OHLC for entry close + target-hit highs (via backtest_phoenix).
  - Confusion matrices (overall + by sector) use **Phoenix** directional signal
    (phoenix_signal vs signal_correct_phoenix). Fusion CM included for reference.

Runs parallel **threads** across tickers (Polygon rate limit shared in-process).

Usage::
    cd MyTradingSpace && python scripts/backtests/run_phoenix_polygon_nasdaq150_2025.py \\
        --workers 12 --period-workers 8 --resume
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import paths  # noqa: E402

HALAL_MASTER = paths.HALAL_MASTER

SECTOR_KEYS = ("Health Care", "Industrials", "Information Technology")
NASDAQ = "NASDAQ"
PER_SECTOR_N = 50


def parse_market_cap(s: Optional[str]) -> float:
    if not s:
        return 0.0
    s = s.strip().replace("$", "").replace(",", "")
    m = re.match(r"([\d.]+)\s*([TBMKtbm])?", s)
    if not m:
        return 0.0
    val = float(m.group(1))
    u = (m.group(2) or "B").upper()
    mult = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}
    return val * mult.get(u, 1e9)


def load_nasdaq_universe(master_path: Path = HALAL_MASTER) -> Dict[str, List[str]]:
    raw = json.loads(master_path.read_text())
    stocks_by_sector: Dict[str, List[Dict[str, Any]]] = raw["stocks_by_sector"]
    out: Dict[str, List[str]] = {}
    for sec in SECTOR_KEYS:
        rows = stocks_by_sector.get(sec) or []
        nasdaq_rows = [
            r for r in rows if str(r.get("exchange") or "").strip().upper() == NASDAQ
        ]
        nasdaq_rows.sort(key=lambda r: -parse_market_cap(r.get("market_cap")))
        seen_sym: set = set()
        tickers: List[str] = []
        for r in nasdaq_rows:
            t = str(r["ticker"]).strip().upper()
            if not t or t in seen_sym:
                continue
            seen_sym.add(t)
            tickers.append(t)
            if len(tickers) >= PER_SECTOR_N:
                break
        if len(tickers) < PER_SECTOR_N:
            raise RuntimeError(f"Sector {sec!r}: only {len(tickers)} unique NASDAQ names (need {PER_SECTOR_N})")
        out[sec] = tickers
    return out


def _months_2025() -> List[Tuple[date, date]]:
    months: List[Tuple[date, date]] = []
    for m in range(1, 13):
        signal_date = date(2025, m, 1)
        months.append((signal_date, signal_date + timedelta(days=30)))
    return months


MONTHS_2025 = _months_2025()


@dataclass(frozen=True)
class TickerTask:
    sector: str
    ticker: str


def _cache_path(out_dir: Path, sector: str, ticker: str) -> Path:
    return out_dir / "cache" / sector.replace(" ", "_") / f"{ticker.upper()}.json"


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


def _confusion_from_periods(df: pd.DataFrame, sig_col: str, corr_col: str) -> Dict[str, Any]:
    TP = FP = TN = FN = neutral = errors = 0
    for _, r in df.iterrows():
        sig = r.get(sig_col)
        corr = r.get(corr_col)
        if pd.isna(corr):
            neutral += 1
            continue
        corr = bool(corr)
        if sig not in ("bullish", "bearish"):
            neutral += 1
            continue
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

    def pct(v: Optional[float]) -> Optional[float]:
        return round(v * 100, 1) if v is not None else None

    acc = correct / directional if directional else None
    prec = TP / (TP + FP) if (TP + FP) else None
    rec = TP / (TP + FN) if (TP + FN) else None
    spec = TN / (TN + FP) if (TN + FP) else None
    f1 = (
        (2 * prec * rec / (prec + rec))
        if (prec is not None and rec is not None and (prec + rec) > 0)
        else None
    )
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
    parser = argparse.ArgumentParser(
        description="Phoenix Polygon NASDAQ-150 backtest with Phoenix confusion matrix(s)."
    )
    parser.add_argument("--workers", type=int, default=12, help="Parallel threads across tickers (default: 12).")
    parser.add_argument("--resume", action="store_true", help="Resume from per-ticker cache.")
    parser.add_argument(
        "--period-workers",
        type=int,
        default=8,
        help="Parallel month evaluations inside run_monthly_backtest (default: 8).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(paths.BACKTEST_DIR / "phoenix_polygon_nasdaq150_2025"),
        help="Output directory.",
    )
    parser.add_argument(
        "--master-json",
        type=str,
        default=str(HALAL_MASTER),
        help="Path to halal_master.json.",
    )
    parser.add_argument(
        "--max-tickers",
        type=int,
        default=0,
        help="If >0, only run first N tasks (debug/smoke); 0 means all.",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    universe = load_nasdaq_universe(Path(args.master_json))
    tasks: List[TickerTask] = []
    for sector, tickers in universe.items():
        for t in tickers:
            tasks.append(TickerTask(sector=sector, ticker=t))

    mx = max(0, int(args.max_tickers))
    if mx and len(tasks) > mx:
        tasks = tasks[:mx]

    univ_path = out_dir / "universe_nasdaq150.json"
    univ_path.write_text(json.dumps(universe, indent=2))

    print()
    print("=" * 72)
    print("PHOENIX + FUND ORCHESTRATOR — POLYGON PRICE — NASDAQ 150 — 2025")
    print(
        f"Tickers: {len(tasks)}  |  Months: {len(MONTHS_2025)}  |  Workers: {args.workers}",
        flush=True,
    )
    print(f"Period workers / ticker : {max(1, int(args.period_workers))}", flush=True)
    print(f"Universe snapshot       : {univ_path}")
    print(f"Output                  : {out_dir}")
    print("=" * 72)

    t0 = time.time()
    results: Dict[str, Any] = {}
    errors = 0

    with ThreadPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
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
            s = (res or {}).get("summary_phoenix") or {}
            acc = s.get("accuracy_pct")
            acc_s = f"{acc:.1f}%" if isinstance(acc, (int, float)) else "N/A"
            print(f"  ✓ {task.ticker:<6} [{task.sector}] Phoenix acc={acc_s}", flush=True)

    elapsed = time.time() - t0
    print()
    print("=" * 72)
    print(f"Done in {elapsed:.1f}s | Errors: {errors}")
    print("=" * 72)

    results_path = out_dir / "results.json"
    results_path.write_text(json.dumps(results, indent=2, default=str))

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
                    "error": p.get("error"),
                    "phoenix_signal": p.get("phoenix_signal"),
                    "signal_correct_phoenix": p.get("signal_correct_phoenix"),
                    "orchestrator_signal": p.get("signal"),
                    "signal_correct_orchestrator": p.get("signal_correct"),
                    "orchestrator_score": p.get("orchestrator_score"),
                    "confidence": p.get("confidence"),
                    "phoenix_score": p.get("phoenix_score"),
                    "fund_score": p.get("fund_score"),
                    "start_price": p.get("start_price"),
                    "target_price": p.get("target_price"),
                    "target_hit": p.get("target_hit"),
                    "target_hit_date": p.get("target_hit_date"),
                    "target_eval_error": p.get("target_eval_error"),
                    "start_price_source": p.get("start_price_source"),
                    "target_data_source": p.get("target_data_source"),
                }
            )
    df = pd.DataFrame(rows)

    sum_rows: List[Dict[str, Any]] = []
    for key, r in sorted(results.items()):
        if not r:
            continue
        sector, ticker = key.split(":", 1)
        s_p = r.get("summary_phoenix") or {}
        s_o = r.get("summary") or {}
        sum_rows.append(
            {
                "sector": sector,
                "ticker": ticker,
                "phoenix_directional": s_p.get("directional_signals"),
                "phoenix_correct": s_p.get("correct_signals"),
                "phoenix_accuracy_pct": s_p.get("accuracy_pct"),
                "fusion_directional": s_o.get("directional_signals"),
                "fusion_correct": s_o.get("correct_signals"),
                "fusion_accuracy_pct": s_o.get("accuracy_pct"),
            }
        )
    df_sum = pd.DataFrame(sum_rows)

    cm_px_overall = _confusion_from_periods(df, "phoenix_signal", "signal_correct_phoenix") if not df.empty else {}
    cm_px_sector = (
        {sec: _confusion_from_periods(g, "phoenix_signal", "signal_correct_phoenix") for sec, g in df.groupby("sector")}
        if not df.empty
        else {}
    )
    cm_f_overall = _confusion_from_periods(df, "orchestrator_signal", "signal_correct_orchestrator") if not df.empty else {}
    cm_f_sector = (
        {
            sec: _confusion_from_periods(g, "orchestrator_signal", "signal_correct_orchestrator")
            for sec, g in df.groupby("sector")
        }
        if not df.empty
        else {}
    )

    cm_payload = {
        "meta": {
            "window": "Jan 2025 – Dec 2025 (monthly anchors, +30d outcome)",
            "universe": str(univ_path),
            "sectors": list(SECTOR_KEYS),
            "tickers_total": len(tasks),
            "price_and_target_source": "polygon",
            "elapsed_sec": round(elapsed, 1),
            "errors": errors,
            "results_json": str(results_path),
            "workers": int(args.workers),
            "period_workers": max(1, int(args.period_workers)),
        },
        "phoenix_directional_vs_target": {
            "overall": cm_px_overall,
            "by_sector": cm_px_sector,
        },
        "orchestrator_fusion_vs_target": {
            "overall": cm_f_overall,
            "by_sector": cm_f_sector,
        },
    }

    cm_json_path = out_dir / "confusion_matrices.json"
    cm_json_path.write_text(json.dumps(cm_payload, indent=2))

    xlsx_path = out_dir / "backtest_2025.xlsx"
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
            pd.DataFrame(list(cm_payload["meta"].items()), columns=["key", "value"]).to_excel(
                w, sheet_name="Meta", index=False
            )
            df_sum.to_excel(w, sheet_name="Summary", index=False)
            df.to_excel(w, sheet_name="Periods", index=False)
            cm_px_rows = [{"scope": "overall", "sector": "ALL", **cm_px_overall}]
            for sec, met in cm_px_sector.items():
                cm_px_rows.append({"scope": "sector", "sector": sec, **met})
            pd.DataFrame(cm_px_rows).to_excel(w, sheet_name="CM Phoenix", index=False)
            cm_f_rows = [{"scope": "overall", "sector": "ALL", **cm_f_overall}]
            for sec, met in cm_f_sector.items():
                cm_f_rows.append({"scope": "sector", "sector": sec, **met})
            pd.DataFrame(cm_f_rows).to_excel(w, sheet_name="CM Fusion", index=False)
        print(f"Wrote Excel         : {xlsx_path}")
    except ImportError:
        csv_dir = out_dir / "csv_export"
        csv_dir.mkdir(parents=True, exist_ok=True)
        df_sum.to_csv(csv_dir / "summary.csv", index=False)
        df.to_csv(csv_dir / "periods.csv", index=False)
        print(f"Wrote CSV export    : {csv_dir} (install openpyxl for .xlsx)")

    print(f"Wrote results JSON  : {results_path}")
    print(f"Wrote CM JSON       : {cm_json_path}")

    px = cm_payload["phoenix_directional_vs_target"]["overall"]
    if px:
        print(
            "\nPhoenix CM (overall): "
            f"TP={px.get('TP')} FP={px.get('FP')} TN={px.get('TN')} FN={px.get('FN')} "
            f"acc={px.get('accuracy_pct')}%"
        )


if __name__ == "__main__":
    main()
