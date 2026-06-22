"""Ingest master_pilot.json and related artifacts into SQLite registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.evaluation.pit_policy import pit_manifest_for_date
from core.paths import ROOT, TRADING_RUNS_DIR

from .backtest_store import BacktestStore, get_default_store

_DASHBOARD_BASE = __import__("os").environ.get("MTS_DASHBOARD_URL", "http://localhost:3055")


def dashboard_backtest_url(run_key: str) -> str:
    """Deep link into Research Lab → Backtest registry for one run."""
    from urllib.parse import quote

    return f"{_DASHBOARD_BASE.rstrip('/')}/research/backtests?run={quote(run_key, safe='')}"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _run_key(artifact_path: str) -> str:
    return artifact_path.replace("\\", "/")


def is_ephemeral_artifact(path: Path) -> bool:
    """Skip unified staging dirs — per-sector masters are deleted after merge."""
    rel = _rel(path.expanduser().resolve())
    return "_staging_" in rel or "/_staging_" in f"/{rel}"


def ingest_master_pilot(
    path: Path,
    *,
    store: Optional[BacktestStore] = None,
    run_type: str = "master_pilot",
) -> Optional[str]:
    """Ingest a master_pilot.json file."""
    if not path.is_file():
        return None
    st = path.stat()
    doc = json.loads(path.read_text(encoding="utf-8"))
    manifest = doc.get("manifest") or {}
    signal_date = manifest.get("signal_date") or _infer_signal_date(path)
    if not signal_date:
        return None

    tickers = doc.get("tickers") or {}
    cm = doc.get("confusion_matrix") or {}
    by_agent = (cm.get("cumulative") or {}).get("by_agent") or {}
    if not by_agent and (cm.get("cumulative") or {}).get("overall"):
        by_agent = {"fusion": (cm.get("cumulative") or {}).get("overall")}

    pass_count = sum(
        1 for row in tickers.values() if isinstance(row, dict) and row.get("pass_enrichment") is True
    )

    rel = _rel(path)
    rk = _run_key(rel)
    store = store or get_default_store()
    store.upsert_run(
        run_key=rk,
        run_id=doc.get("run_id"),
        signal_date=str(signal_date),
        result_date=_result_date_from_manifest(manifest),
        run_type=run_type,
        artifact_path=rel,
        artifact_mtime=st.st_mtime,
        ticker_count=len(tickers),
        pass_count=pass_count,
        meta={
            "manifest": manifest,
            "elapsed_sec": doc.get("elapsed_sec"),
            "confusion_meta": cm.get("meta"),
            "mode": (cm.get("meta") or {}).get("mode") or manifest.get("backtest_mode"),
            "backtest_signal_profile": manifest.get("backtest_signal_profile")
            or (cm.get("meta") or {}).get("backtest_signal_profile"),
            "backtest_mode": manifest.get("backtest_mode"),
            "sector": manifest.get("sector"),
            "diagnostics": cm.get("diagnostics"),
        },
        pit_manifest=pit_manifest_for_date(str(signal_date)),
        agent_matrices=by_agent,
        tickers=tickers if isinstance(tickers, dict) else {},
    )
    return rk


def ingest_confusion_matrix(
    path: Path,
    *,
    store: Optional[BacktestStore] = None,
    signal_date: Optional[str] = None,
    run_type: str = "sector_pilot",
) -> Optional[str]:
    """Ingest standalone confusion_matrix.json + sibling master if present."""
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    parent = path.parent
    master = parent / "master_pilot.json"
    if master.is_file():
        return ingest_master_pilot(master, store=store, run_type=run_type)

    meta = doc.get("meta") or {}
    sd = signal_date or meta.get("signal_date") or _infer_signal_date(parent)
    if not sd:
        return None
    by_agent = (doc.get("cumulative") or {}).get("by_agent") or {}
    overall = (doc.get("cumulative") or {}).get("overall")
    if overall and "fusion" not in by_agent:
        by_agent = {"fusion": overall, **by_agent}

    rel = _rel(path)
    rk = _run_key(rel)
    st = path.stat()
    store = store or get_default_store()
    store.upsert_run(
        run_key=rk,
        run_id=None,
        signal_date=str(sd),
        result_date=None,
        run_type=run_type,
        artifact_path=rel,
        artifact_mtime=st.st_mtime,
        ticker_count=int(meta.get("tickers") or 0),
        pass_count=0,
        meta={
            "confusion_meta": meta,
            "mode": meta.get("mode"),
            "backtest_signal_profile": meta.get("backtest_signal_profile"),
            "backtest_mode": meta.get("mode"),
            "diagnostics": doc.get("diagnostics"),
        },
        pit_manifest=pit_manifest_for_date(str(sd)),
        agent_matrices=by_agent,
        tickers={},
    )
    return rk


def finalize_backtest_ingest(
    path: Path,
    *,
    store: Optional[BacktestStore] = None,
) -> Optional[str]:
    """Ingest one backtest artifact after a pilot completes (no-op for staging paths)."""
    path = path.expanduser().resolve()
    if is_ephemeral_artifact(path):
        return None
    return ingest_artifact_path(path, store=store)


def ingest_artifact_path(path: Path, *, store: Optional[BacktestStore] = None) -> Optional[str]:
    path = path.expanduser().resolve()
    if is_ephemeral_artifact(path):
        return None
    name = path.name.lower()
    if name == "master_pilot.json":
        run_type = "unified" if "unified_master" in str(path) else "sector_master"
        return ingest_master_pilot(path, store=store, run_type=run_type)
    if name == "confusion_matrix.json":
        return ingest_confusion_matrix(path, store=store)
    return None


def _infer_signal_date(path: Path) -> Optional[str]:
    for part in path.parts:
        if part.startswith("unified_master_"):
            return part.replace("unified_master_", "")[:10]
        if part.startswith("sector_") and "_" in part[7:]:
            bits = part.split("_")
            if len(bits) >= 2 and len(bits[-1]) == 10:
                try:
                    from datetime import date

                    date.fromisoformat(bits[-1])
                    return bits[-1]
                except ValueError:
                    pass
    return None


def _result_date_from_manifest(manifest: Dict[str, Any]) -> Optional[str]:
    if manifest.get("result_date"):
        return str(manifest["result_date"])
    sd = manifest.get("signal_date")
    ev = manifest.get("eval_days")
    if sd and ev:
        from datetime import date, timedelta

        try:
            return (date.fromisoformat(str(sd)[:10]) + timedelta(days=int(ev))).isoformat()
        except (ValueError, TypeError):
            pass
    return None


def purge_orphan_runs(*, store: Optional[BacktestStore] = None) -> List[str]:
    """Remove registry rows whose artifact file no longer exists (e.g. deleted staging)."""
    store = store or get_default_store()
    removed: List[str] = []
    for run in store.list_runs(limit=10_000):
        rel = run.get("artifact_path")
        if not rel:
            continue
        if not (ROOT / str(rel)).is_file():
            store.delete_run(str(run["run_key"]))
            removed.append(str(run["run_key"]))
    return removed


def scan_and_ingest_trading_runs(
    *,
    root: Optional[Path] = None,
    store: Optional[BacktestStore] = None,
    purge_orphans: bool = True,
) -> Dict[str, Any]:
    """Scan data/output/trading_runs and upsert new/changed artifacts."""
    scan_root = root or TRADING_RUNS_DIR
    store = store or get_default_store()
    ingested: List[str] = []
    skipped: List[str] = []
    removed: List[str] = []

    if purge_orphans:
        removed = purge_orphan_runs(store=store)

    if not scan_root.is_dir():
        return {
            "ingested": ingested,
            "skipped": skipped,
            "removed": removed,
            "count": len(ingested),
        }

    candidates: List[Path] = []
    for pattern in ("master_pilot.json", "confusion_matrix.json"):
        candidates.extend(scan_root.rglob(pattern))

    seen_keys: set = set()
    for path in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
        if is_ephemeral_artifact(path):
            continue
        rel = _rel(path)
        key = _run_key(rel)
        if key in seen_keys and path.name == "confusion_matrix.json":
            continue
        try:
            rk = ingest_artifact_path(path, store=store)
            if rk:
                ingested.append(rk)
                seen_keys.add(key)
            else:
                skipped.append(rel)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            skipped.append(f"{rel}: {exc}")

    return {
        "ingested": ingested,
        "skipped": skipped,
        "removed": removed,
        "count": len(ingested),
    }
