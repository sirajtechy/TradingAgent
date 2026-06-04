"""
Reconcile Phoenix BUY/WATCH signals from master_pilot.json across runs.

Scans active ``data/output/trading_runs`` and optionally ``data/archive/trading_runs``,
dedupes by (signal_date, ticker) using source priority, writes Excel + JSON.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from core.paths import ROOT, TRADING_RUNS_DIR

DEFAULT_XLSX = TRADING_RUNS_DIR / "phoenix_signals_reconciled.xlsx"
DEFAULT_JSON = TRADING_RUNS_DIR / "phoenix_signals_reconciled.json"

SIGNAL_COLUMNS = [
    "signal_date",
    "ticker",
    "phoenix_signal",
    "sector",
    "source_json",
    "source_priority",
    "run_type",
    "fusion_final_signal",
    "fusion_orchestrator_score",
    "phoenix_score",
    "fund_score",
    "fusion_conflict",
    "entry_price",
    "exit_price",
    "exit_reference_date",
    "stop_price",
    "target_t1",
    "target_t2",
    "backtest_target_price",
    "target_hit",
    "target_hit_date",
    "signal_correct",
    "pattern_name",
]


@dataclass
class SourceRecord:
    path: Path
    rel_to_root: str
    rel_to_runs: str
    signal_date: str
    ticker_count: int
    buy_count: int
    watch_count: int
    priority: int
    run_type: str


@dataclass
class ReconcileResult:
    signals: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    reconciliation_log: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


def _source_priority(rel_runs: str, signal_date: str) -> Tuple[int, str]:
    """Higher wins for (signal_date, ticker) dedup."""
    r = rel_runs.replace("\\", "/")
    sig = signal_date
    if r == f"unified_master_{sig}/master_pilot.json":
        return 300, "unified_master"
    if r.startswith(f"unified_master_{sig}/") and r.endswith("/master_pilot.json"):
        return 250, "unified_sector_shard"
    if r == f"master_data_all_sectors_{sig}/master_pilot.json":
        return 200, "master_data_merged"
    if f"master_data_all_sectors_{sig}/" in f"/{r}" and r.endswith("master_pilot.json"):
        return 180, "master_data_sector"
    if r.startswith("sector_") and r.endswith("/master_pilot.json"):
        return 120, "sector_pilot"
    if re.search(rf"/{re.escape(sig)}/master_pilot\.json$", f"/{r}"):
        return 100, "dated_run"
    return 50, "other"


def _iter_master_pilots(
    *,
    include_archive: bool,
) -> Iterable[Tuple[Path, str]]:
    """Yield (path, root_label) where root_label is output or archive."""
    roots: List[Tuple[Path, str]] = [(TRADING_RUNS_DIR, "output")]
    archive = ROOT / "data" / "archive" / "trading_runs"
    if include_archive and archive.is_dir():
        roots.append((archive, "archive"))
    for root, label in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("master_pilot.json"):
            yield p, label


def _flatten_rows(
    *,
    sig_date: str,
    rel_runs: str,
    rel_root: str,
    doc: Dict[str, Any],
    priority: int,
    run_type: str,
    allowed_signals: Set[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    tickers = doc.get("tickers") or {}
    for sym, row in tickers.items():
        if not isinstance(row, dict) or row.get("error"):
            continue
        px = str(row.get("phoenix_signal") or "").strip().upper()
        if px not in allowed_signals:
            continue
        rows.append(
            {
                "signal_date": sig_date,
                "ticker": str(sym).upper(),
                "phoenix_signal": row.get("phoenix_signal"),
                "sector": row.get("sector"),
                "source_json": rel_root,
                "source_priority": priority,
                "run_type": run_type,
                "fusion_final_signal": row.get("fusion_final_signal"),
                "fusion_orchestrator_score": row.get("fusion_orchestrator_score"),
                "phoenix_score": row.get("phoenix_score"),
                "fund_score": row.get("fund_score"),
                "fusion_conflict": row.get("fusion_conflict"),
                "entry_price": row.get("entry_price"),
                "exit_price": row.get("exit_price"),
                "exit_reference_date": row.get("exit_reference_date"),
                "stop_price": row.get("stop_price"),
                "target_t1": row.get("target_t1"),
                "target_t2": row.get("target_t2"),
                "backtest_target_price": row.get("backtest_target_price"),
                "target_hit": row.get("target_hit"),
                "target_hit_date": row.get("target_hit_date"),
                "signal_correct": row.get("signal_correct"),
                "pattern_name": row.get("pattern_name"),
            }
        )
    return rows


def reconcile_signals(
    *,
    date_from: date,
    date_to: date,
    signals: Sequence[str] = ("BUY", "WATCH"),
    include_archive: bool = True,
) -> ReconcileResult:
    if date_from > date_to:
        raise ValueError("date_from must be <= date_to")

    allowed = {s.strip().upper() for s in signals if s.strip()}
    if not allowed:
        allowed = {"BUY", "WATCH"}

    source_records: List[SourceRecord] = []
    all_candidates: List[Dict[str, Any]] = []

    for path, storage in _iter_master_pilots(include_archive=include_archive):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            sig = (doc.get("manifest") or {}).get("signal_date")
            if not sig:
                continue
            sig = str(sig)[:10]
            d = date.fromisoformat(sig)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if d < date_from or d > date_to:
            continue

        if storage == "archive":
            rel_root = str(path.relative_to(ROOT)).replace("\\", "/")
            rel_runs = rel_root.replace("data/archive/trading_runs/", "")
        else:
            rel_root = str(path.relative_to(ROOT)).replace("\\", "/")
            rel_runs = str(path.relative_to(TRADING_RUNS_DIR)).replace("\\", "/")

        priority, run_type = _source_priority(rel_runs, sig)
        tickers = doc.get("tickers") or {}
        buy = watch = 0
        for row in tickers.values():
            if not isinstance(row, dict) or row.get("error"):
                continue
            ps = str(row.get("phoenix_signal") or "").upper()
            if ps == "BUY":
                buy += 1
            elif ps == "WATCH":
                watch += 1

        source_records.append(
            SourceRecord(
                path=path,
                rel_to_root=rel_root,
                rel_to_runs=rel_runs,
                signal_date=sig,
                ticker_count=len(tickers),
                buy_count=buy,
                watch_count=watch,
                priority=priority,
                run_type=run_type,
            )
        )
        all_candidates.extend(
            _flatten_rows(
                sig_date=sig,
                rel_runs=rel_runs,
                rel_root=rel_root,
                doc=doc,
                priority=priority,
                run_type=run_type,
                allowed_signals=allowed,
            )
        )

    best: Dict[Tuple[str, str], Dict[str, Any]] = {}
    log: List[Dict[str, Any]] = []

    for row in all_candidates:
        key = (row["signal_date"], row["ticker"])
        cur = best.get(key)
        if cur is None:
            best[key] = row
            continue
        if row["source_priority"] > cur["source_priority"]:
            log.append(
                {
                    "signal_date": key[0],
                    "ticker": key[1],
                    "kept_source": row["source_json"],
                    "kept_priority": row["source_priority"],
                    "dropped_source": cur["source_json"],
                    "dropped_priority": cur["source_priority"],
                }
            )
            best[key] = row
        elif row["source_priority"] == cur["source_priority"] and row["source_json"] != cur["source_json"]:
            log.append(
                {
                    "signal_date": key[0],
                    "ticker": key[1],
                    "kept_source": cur["source_json"],
                    "kept_priority": cur["source_priority"],
                    "dropped_source": row["source_json"],
                    "dropped_priority": row["source_priority"],
                    "note": "same_priority",
                }
            )

    signals_out = sorted(best.values(), key=lambda r: (r["signal_date"], r["ticker"]))
    buy_n = sum(1 for r in signals_out if str(r.get("phoenix_signal", "")).upper() == "BUY")
    watch_n = sum(1 for r in signals_out if str(r.get("phoenix_signal", "")).upper() == "WATCH")

    sources_out = [
        {
            "signal_date": s.signal_date,
            "source_json": s.rel_to_root,
            "storage": "archive" if "data/archive/" in s.rel_to_root else "output",
            "run_type": s.run_type,
            "priority": s.priority,
            "tickers": s.ticker_count,
            "buy": s.buy_count,
            "watch": s.watch_count,
        }
        for s in sorted(source_records, key=lambda x: (x.signal_date, -x.priority, x.rel_to_root))
    ]

    return ReconcileResult(
        signals=signals_out,
        sources=sources_out,
        reconciliation_log=log,
        summary={
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "signals_filter": sorted(allowed),
            "include_archive": include_archive,
            "sources_scanned": len(source_records),
            "signals_deduped": len(signals_out),
            "buy": buy_n,
            "watch": watch_n,
            "reconciliation_conflicts": len(log),
            "signal_dates": sorted({r["signal_date"] for r in signals_out}),
        },
    )


def build_json_document(result: ReconcileResult) -> Dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": result.summary,
        "sources": result.sources,
        "reconciliation_log": result.reconciliation_log,
        "signals": result.signals,
    }


def write_signals_excel(
    result: ReconcileResult,
    path: Path,
    *,
    signals_filter: Set[str],
) -> None:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    df_all = pd.DataFrame(result.signals)
    if df_all.empty:
        df_all = pd.DataFrame(columns=SIGNAL_COLUMNS)

    df_buy = df_all[df_all["phoenix_signal"].astype(str).str.upper() == "BUY"] if not df_all.empty else df_all
    df_watch = df_all[df_all["phoenix_signal"].astype(str).str.upper() == "WATCH"] if not df_all.empty else df_all
    df_sources = pd.DataFrame(result.sources)
    df_log = pd.DataFrame(result.reconciliation_log)
    df_summary = pd.DataFrame([result.summary])

    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        if "BUY" in signals_filter:
            df_buy.to_excel(xw, sheet_name="BUY", index=False)
        if "WATCH" in signals_filter:
            df_watch.to_excel(xw, sheet_name="WATCH", index=False)
        df_all.to_excel(xw, sheet_name="All_Signals", index=False)
        df_sources.to_excel(xw, sheet_name="Sources", index=False)
        if not df_log.empty:
            df_log.to_excel(xw, sheet_name="Reconciliation_Log", index=False)
        df_summary.to_excel(xw, sheet_name="Summary", index=False)


def export_signals(
    *,
    date_from: date,
    date_to: date,
    signals: Sequence[str] = ("BUY", "WATCH"),
    include_archive: bool = True,
    output_xlsx: Optional[Path] = None,
    output_json: Optional[Path] = None,
    write_excel: bool = True,
    write_json: bool = True,
) -> ReconcileResult:
    result = reconcile_signals(
        date_from=date_from,
        date_to=date_to,
        signals=signals,
        include_archive=include_archive,
    )
    allowed = {s.strip().upper() for s in signals if s.strip()}

    if write_json:
        jp = output_json or DEFAULT_JSON
        if not jp.is_absolute():
            jp = ROOT / jp
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(build_json_document(result), indent=2), encoding="utf-8")

    if write_excel:
        xp = output_xlsx or DEFAULT_XLSX
        if not xp.is_absolute():
            xp = ROOT / xp
        write_signals_excel(result, xp, signals_filter=allowed)

    return result
