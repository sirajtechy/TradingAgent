"""
Daily pre-market pipeline — unified pilot + optional BUY excel + notify.

Shell schedulers (launchd) call ``python -m pipelines daily`` for 24/7 operation.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from core.paths import ROOT, TRADING_RUNS_LOGS, unified_master_dir
from pipelines.backtest import run_unified_pilot


def run_daily(
    *,
    signal_date: str | None = None,
    export_buy: bool = True,
    send_telegram: bool = True,
    eval_days: int = 15,
    sector_jobs: int | None = None,
    workers: int | None = None,
    period_workers: int | None = None,
) -> int:
    sig = signal_date or os.environ.get("SIGNAL_DATE") or date.today().isoformat()
    sj = sector_jobs if sector_jobs is not None else int(os.environ.get("SECTOR_JOBS", "11"))
    wk = workers if workers is not None else int(os.environ.get("WORKERS", "8"))
    pw = period_workers if period_workers is not None else int(os.environ.get("PERIOD_WORKERS", "2"))
    log_dir = TRADING_RUNS_LOGS
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"daily_pipeline_{sig}.log"

    master = unified_master_dir(sig) / "master_pilot.json"
    excel = ROOT / "data" / "output" / "trading_runs" / f"phoenix_buy_{sig}.xlsx"
    py = os.environ.get("MYTRADING_PYTHON") or str(ROOT / ".venv" / "bin" / "python")

    print(f"=== daily pipeline signal_date={sig} ===", flush=True)

    rc = run_unified_pilot(
        signal_date=sig,
        eval_days=eval_days,
        sector_jobs=sj,
        workers=wk,
        period_workers=pw,
    )
    if rc != 0:
        return rc

    if export_buy:
        print("--- export Phoenix BUY excel ---", flush=True)
        export_script = ROOT / "scripts" / "dashboard" / "export_phoenix_buy_from_masters.py"
        rc = subprocess.call(
            [
                py,
                str(export_script),
                "--from-date",
                sig,
                "--to-date",
                sig,
                "--output",
                str(excel),
            ],
            cwd=str(ROOT),
        )
        if rc != 0:
            return rc

    notify = ROOT / "apps" / "openclaw" / "scripts" / "notify_daily_summary.py"
    if notify.is_file():
        print("--- notify ---", flush=True)
        tg_args = [py, str(notify), "--master-pilot", str(master)]
        if excel.is_file():
            tg_args.extend(["--excel", str(excel)])
        if not send_telegram:
            tg_args.append("--no-telegram")
        rc = subprocess.call(tg_args, cwd=str(ROOT))
        if rc != 0:
            return rc

    print(f"=== pipeline done (log: {log_path}) ===", flush=True)
    return 0
