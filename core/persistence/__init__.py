"""Local persistence for backtest runs and confusion matrices."""

from .backtest_store import BacktestStore, get_default_store
from .ingest import (
    finalize_backtest_ingest,
    ingest_artifact_path,
    is_ephemeral_artifact,
    purge_orphan_runs,
    scan_and_ingest_trading_runs,
)

__all__ = [
    "BacktestStore",
    "get_default_store",
    "finalize_backtest_ingest",
    "ingest_artifact_path",
    "is_ephemeral_artifact",
    "purge_orphan_runs",
    "scan_and_ingest_trading_runs",
]
