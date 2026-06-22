"""
Agnostic backtest pipelines — delegate to existing scripts (behavior unchanged).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from core.paths import ROOT, sector_run_dir, unified_master_dir
from core.io.master_pilot import slug_sector

_SECTOR_PILOT = ROOT / "scripts" / "backtests" / "run_halal_sector_month_pilot.py"
_UNIFIED_PILOT = ROOT / "scripts" / "backtests" / "run_master_data_parallel_pilot.py"
_DEFAULT_MASTER = ROOT / "data" / "input" / "master_data" / "halal_tickers_clean.json"


def _run(cmd: Sequence[str]) -> int:
    print("Pipeline:", " ".join(cmd), flush=True)
    return subprocess.call(list(cmd), cwd=str(ROOT))


def run_sector_pilot(
    *,
    sector: str,
    signal_date: str,
    eval_days: int = 15,
    output_dir: Optional[Path] = None,
    workers: int = 6,
    period_workers: int = 2,
    use_halal_json: bool = True,
    backtest_signal_profile: str = "phoenix_recall",
    full_sector: bool = False,
    limit: Optional[int] = None,
    max_tickers: Optional[int] = None,
    offset: int = 0,
) -> int:
    """Run one sector via ``run_halal_sector_month_pilot.py`` (--sector or --tickers)."""
    out = output_dir or sector_run_dir(slug_sector(sector), signal_date)
    out.mkdir(parents=True, exist_ok=True)
    cmd: List[str] = [
        sys.executable,
        str(_SECTOR_PILOT),
        "--signal-date",
        signal_date,
        "--eval-days",
        str(max(1, int(eval_days))),
        "--single-master-json",
        "--workers",
        str(max(1, workers)),
        "--period-workers",
        str(max(1, period_workers)),
        "--output-dir",
        str(out),
    ]
    cmd.extend(["--backtest-signal-profile", backtest_signal_profile])
    if full_sector:
        cmd.append("--full-sector")
    if limit is not None:
        cmd.extend(["--limit", str(limit)])
    if max_tickers is not None:
        cmd.extend(["--max-tickers", str(max_tickers)])
    if offset:
        cmd.extend(["--offset", str(offset)])
    if use_halal_json:
        cmd.extend(["--sector", sector])
    else:
        raise NotImplementedError("Explicit ticker list: pass output_dir and extend CLI")
    rc = _run(cmd)
    if rc != 0:
        return rc
    master = out / "master_pilot.json"
    if master.is_file():
        try:
            from core.persistence.ingest import finalize_backtest_ingest

            rk = finalize_backtest_ingest(master)
            if rk:
                from core.persistence.ingest import dashboard_backtest_url

                print(f"Registry ingested → {rk}", flush=True)
                print(f"Dashboard → {dashboard_backtest_url(rk)}", flush=True)
        except Exception as exc:
            print(f"Registry ingest warning: {exc}", flush=True)
    return rc


def run_unified_pilot(
    *,
    signal_date: str,
    eval_days: int = 15,
    merged_output: Optional[Path] = None,
    master_json: Optional[Path] = None,
    sector_jobs: int = 11,
    workers: int = 8,
    period_workers: int = 2,
    cleanup_staging: bool = True,
) -> int:
    """All-sector parallel pilot → ``unified_master_<date>/master_pilot.json``."""
    merged = merged_output or (unified_master_dir(signal_date) / "master_pilot.json")
    staging = ROOT / "data" / "output" / f"_staging_unified_master_{signal_date}"
    cmd: List[str] = [
        sys.executable,
        str(_UNIFIED_PILOT),
        "--signal-date",
        signal_date,
        "--eval-days",
        str(max(1, int(eval_days))),
        "--output-root",
        str(staging),
        "--merged-output",
        str(merged),
        "--sector-jobs",
        str(max(1, sector_jobs)),
        "--workers",
        str(max(1, workers)),
        "--period-workers",
        str(max(1, period_workers)),
    ]
    if master_json:
        cmd.extend(["--master-json", str(master_json)])
    elif _DEFAULT_MASTER.is_file():
        cmd.extend(["--master-json", str(_DEFAULT_MASTER)])
    if cleanup_staging:
        cmd.append("--cleanup-staging")
    rc = _run(cmd)
    if rc != 0:
        return rc
    merged_path = merged
    if merged_path.is_file():
        try:
            from core.persistence.ingest import finalize_backtest_ingest, purge_orphan_runs

            rk = finalize_backtest_ingest(merged_path)
            if rk:
                from core.persistence.ingest import dashboard_backtest_url

                print(f"Registry ingested → {rk}", flush=True)
                print(f"Dashboard → {dashboard_backtest_url(rk)}", flush=True)
            removed = purge_orphan_runs()
            if removed:
                print(f"Registry purged {len(removed)} orphan staging row(s)", flush=True)
        except Exception as exc:
            print(f"Registry ingest warning: {exc}", flush=True)
    return rc
