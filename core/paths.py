"""
Central path configuration — extends repo ``paths.py`` with pipeline output locations.
"""

from __future__ import annotations

from pathlib import Path

import paths as _legacy

ROOT = _legacy.ROOT
DATA_DIR = _legacy.DATA_DIR
OUTPUT_DIR = _legacy.OUTPUT_DIR
TRADING_RUNS_DIR = OUTPUT_DIR / "trading_runs"
TRADING_RUNS_LOGS = TRADING_RUNS_DIR / "logs"
HALAL_UNIVERSE = _legacy.HALAL_UNIVERSE
MASTER_DATA = _legacy.MASTER_DATA
ENV_FILE = _legacy.ENV_FILE


def ensure_dirs() -> None:
    _legacy.ensure_dirs()
    TRADING_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    TRADING_RUNS_LOGS.mkdir(parents=True, exist_ok=True)


def unified_master_dir(signal_date: str) -> Path:
    return TRADING_RUNS_DIR / f"unified_master_{signal_date}"


def sector_run_dir(sector_slug: str, signal_date: str) -> Path:
    return TRADING_RUNS_DIR / f"sector_{sector_slug}_{signal_date}"
