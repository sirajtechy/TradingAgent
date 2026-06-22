"""SQLite registry for backtest runs, agent matrices, and ticker rows."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from core.paths import ROOT, TRADING_RUNS_DIR


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


DEFAULT_DB_PATH = ROOT / "data" / "output" / "backtest_registry" / "backtests.sqlite"


class BacktestStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS backtest_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_key TEXT NOT NULL UNIQUE,
                    run_id TEXT,
                    signal_date TEXT NOT NULL,
                    result_date TEXT,
                    run_type TEXT NOT NULL,
                    artifact_path TEXT NOT NULL,
                    artifact_mtime REAL,
                    ticker_count INTEGER DEFAULT 0,
                    pass_count INTEGER DEFAULT 0,
                    meta_json TEXT,
                    pit_manifest_json TEXT,
                    ingested_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_runs_signal_date ON backtest_runs(signal_date);
                CREATE INDEX IF NOT EXISTS idx_runs_ingested ON backtest_runs(ingested_at);

                CREATE TABLE IF NOT EXISTS agent_matrices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_key TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    tp INTEGER DEFAULT 0,
                    fp INTEGER DEFAULT 0,
                    tn INTEGER DEFAULT 0,
                    fn INTEGER DEFAULT 0,
                    neutral_count INTEGER DEFAULT 0,
                    metrics_json TEXT,
                    UNIQUE(run_key, agent_id),
                    FOREIGN KEY(run_key) REFERENCES backtest_runs(run_key) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS backtest_tickers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_key TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    sector TEXT,
                    row_json TEXT NOT NULL,
                    UNIQUE(run_key, ticker),
                    FOREIGN KEY(run_key) REFERENCES backtest_runs(run_key) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_tickers_run ON backtest_tickers(run_key);
                """
            )

    def upsert_run(
        self,
        *,
        run_key: str,
        signal_date: str,
        run_type: str,
        artifact_path: str,
        artifact_mtime: float,
        run_id: Optional[str] = None,
        result_date: Optional[str] = None,
        ticker_count: int = 0,
        pass_count: int = 0,
        meta: Optional[Dict[str, Any]] = None,
        pit_manifest: Optional[Dict[str, Any]] = None,
        agent_matrices: Optional[Dict[str, Dict[str, Any]]] = None,
        tickers: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> str:
        ingested_at = _utc_now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO backtest_runs (
                    run_key, run_id, signal_date, result_date, run_type,
                    artifact_path, artifact_mtime, ticker_count, pass_count,
                    meta_json, pit_manifest_json, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_key) DO UPDATE SET
                    run_id=excluded.run_id,
                    signal_date=excluded.signal_date,
                    result_date=excluded.result_date,
                    run_type=excluded.run_type,
                    artifact_mtime=excluded.artifact_mtime,
                    ticker_count=excluded.ticker_count,
                    pass_count=excluded.pass_count,
                    meta_json=excluded.meta_json,
                    pit_manifest_json=excluded.pit_manifest_json,
                    ingested_at=excluded.ingested_at
                """,
                (
                    run_key,
                    run_id,
                    signal_date,
                    result_date,
                    run_type,
                    artifact_path,
                    artifact_mtime,
                    ticker_count,
                    pass_count,
                    json.dumps(meta or {}, default=str),
                    json.dumps(pit_manifest or {}, default=str),
                    ingested_at,
                ),
            )
            conn.execute("DELETE FROM agent_matrices WHERE run_key = ?", (run_key,))
            conn.execute("DELETE FROM backtest_tickers WHERE run_key = ?", (run_key,))

            for agent_id, met in (agent_matrices or {}).items():
                conn.execute(
                    """
                    INSERT INTO agent_matrices (
                        run_key, agent_id, tp, fp, tn, fn, neutral_count, metrics_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_key,
                        agent_id,
                        int(met.get("TP") or 0),
                        int(met.get("FP") or 0),
                        int(met.get("TN") or 0),
                        int(met.get("FN") or 0),
                        int(met.get("neutral_count") or met.get("neutral") or 0),
                        json.dumps(met, default=str),
                    ),
                )

            for sym, row in (tickers or {}).items():
                conn.execute(
                    """
                    INSERT INTO backtest_tickers (run_key, ticker, sector, row_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        run_key,
                        str(sym).upper(),
                        row.get("sector") if isinstance(row, dict) else None,
                        json.dumps(row, default=str),
                    ),
                )
        return run_key

    def delete_run(self, run_key: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM backtest_runs WHERE run_key = ?", (run_key,))
            return cur.rowcount > 0

    def list_runs(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT r.run_key, r.run_id, r.signal_date, r.result_date, r.run_type,
                       r.artifact_path, r.ticker_count, r.pass_count, r.ingested_at, r.meta_json,
                       tm.tp AS technical_tp, tm.fn AS technical_fn, tm.fp AS technical_fp
                FROM backtest_runs r
                LEFT JOIN agent_matrices tm
                  ON tm.run_key = r.run_key AND tm.agent_id = 'technical'
                ORDER BY r.signal_date DESC, r.ingested_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            meta = {}
            try:
                meta = json.loads(r["meta_json"] or "{}")
            except json.JSONDecodeError:
                pass
            manifest = meta.get("manifest") or {}
            confusion_meta = meta.get("confusion_meta") or {}
            out.append(
                {
                    "run_key": r["run_key"],
                    "run_id": r["run_id"],
                    "signal_date": r["signal_date"],
                    "result_date": r["result_date"],
                    "run_type": r["run_type"],
                    "artifact_path": r["artifact_path"],
                    "ticker_count": r["ticker_count"],
                    "pass_count": r["pass_count"],
                    "ingested_at": r["ingested_at"],
                    "meta": meta,
                    "sector": meta.get("sector") or manifest.get("sector"),
                    "backtest_mode": meta.get("backtest_mode") or meta.get("mode") or manifest.get("backtest_mode"),
                    "backtest_signal_profile": meta.get("backtest_signal_profile")
                    or manifest.get("backtest_signal_profile")
                    or confusion_meta.get("backtest_signal_profile"),
                    "technical_only": (
                        meta.get("mode") == "technical_only"
                        or meta.get("backtest_mode") == "technical_only"
                        or manifest.get("backtest_mode") == "technical_only"
                    ),
                    "technical_tp": r["technical_tp"],
                    "technical_fp": r["technical_fp"],
                    "technical_fn": r["technical_fn"],
                }
            )
        return out

    def get_run(self, run_key: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM backtest_runs WHERE run_key = ?",
                (run_key,),
            ).fetchone()
            if not row:
                return None
            matrices = conn.execute(
                "SELECT agent_id, tp, fp, tn, fn, neutral_count, metrics_json FROM agent_matrices WHERE run_key = ? ORDER BY agent_id",
                (run_key,),
            ).fetchall()
            tickers = conn.execute(
                "SELECT ticker, sector, row_json FROM backtest_tickers WHERE run_key = ? ORDER BY ticker",
                (run_key,),
            ).fetchall()

        by_agent: Dict[str, Any] = {}
        for m in matrices:
            try:
                met = json.loads(m["metrics_json"] or "{}")
            except json.JSONDecodeError:
                met = {}
            by_agent[m["agent_id"]] = met

        ticker_rows: Dict[str, Any] = {}
        for t in tickers:
            try:
                ticker_rows[t["ticker"]] = json.loads(t["row_json"] or "{}")
            except json.JSONDecodeError:
                ticker_rows[t["ticker"]] = {}

        try:
            meta = json.loads(row["meta_json"] or "{}")
        except json.JSONDecodeError:
            meta = {}
        manifest = meta.get("manifest") or {}

        return {
            "run_key": row["run_key"],
            "run_id": row["run_id"],
            "signal_date": row["signal_date"],
            "result_date": row["result_date"],
            "run_type": row["run_type"],
            "artifact_path": row["artifact_path"],
            "ticker_count": row["ticker_count"],
            "pass_count": row["pass_count"],
            "ingested_at": row["ingested_at"],
            "meta": meta,
            "backtest_mode": meta.get("backtest_mode") or meta.get("mode") or manifest.get("backtest_mode"),
            "backtest_signal_profile": meta.get("backtest_signal_profile")
            or manifest.get("backtest_signal_profile")
            or (meta.get("confusion_meta") or {}).get("backtest_signal_profile"),
            "sector": meta.get("sector") or manifest.get("sector"),
            "technical_only": (
                meta.get("mode") == "technical_only"
                or meta.get("backtest_mode") == "technical_only"
                or manifest.get("backtest_mode") == "technical_only"
            ),
            "pit_manifest": json.loads(row["pit_manifest_json"] or "{}"),
            "confusion_matrix": {
                "cumulative": {
                    "overall": by_agent.get("technical") or by_agent.get("fusion") or {},
                    "by_agent": by_agent,
                },
                "meta": meta.get("confusion_meta") or {},
                "diagnostics": meta.get("diagnostics"),
            },
            "tickers": ticker_rows,
        }

    def timeline_summary(self) -> List[Dict[str, Any]]:
        """Per signal_date rollup for charting accuracy over time."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT r.signal_date, r.run_type, r.ticker_count, r.pass_count,
                       m.agent_id, m.metrics_json
                FROM backtest_runs r
                LEFT JOIN agent_matrices m ON m.run_key = r.run_key
                WHERE m.agent_id IN ('fusion', 'technical', 'fusion_full')
                   OR m.agent_id IS NULL
                ORDER BY r.signal_date ASC
                """
            ).fetchall()
        by_date: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            sd = r["signal_date"]
            if sd not in by_date:
                by_date[sd] = {
                    "signal_date": sd,
                    "ticker_count": r["ticker_count"],
                    "pass_count": r["pass_count"],
                    "agents": {},
                }
            if r["agent_id"]:
                try:
                    by_date[sd]["agents"][r["agent_id"]] = json.loads(r["metrics_json"] or "{}")
                except json.JSONDecodeError:
                    pass
        return list(by_date.values())

    def confusion_heatmap_data(
        self,
        *,
        period: str = "all",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Runs with full per-agent matrices, filtered by ingest day (UTC)."""
        runs = self.list_runs(limit=500)
        filtered = [r for r in runs if _ingested_period_match(str(r.get("ingested_at") or ""), period)]
        filtered.sort(key=lambda r: str(r.get("ingested_at") or ""), reverse=True)
        filtered = filtered[: max(1, int(limit))]
        if not filtered:
            return []

        keys = [str(r["run_key"]) for r in filtered]
        placeholders = ",".join("?" * len(keys))
        with self._conn() as conn:
            matrices = conn.execute(
                f"""
                SELECT run_key, agent_id, tp, fp, tn, fn, neutral_count, metrics_json
                FROM agent_matrices
                WHERE run_key IN ({placeholders})
                ORDER BY agent_id
                """,
                keys,
            ).fetchall()

        by_run: Dict[str, Dict[str, Any]] = {k: {} for k in keys}
        for m in matrices:
            try:
                met = json.loads(m["metrics_json"] or "{}")
            except json.JSONDecodeError:
                met = {}
            met["TP"] = int(m["tp"] or 0)
            met["FP"] = int(m["fp"] or 0)
            met["TN"] = int(m["tn"] or 0)
            met["FN"] = int(m["fn"] or 0)
            met["neutral_count"] = int(m["neutral_count"] or 0)
            by_run[str(m["run_key"])][str(m["agent_id"])] = met

        out: List[Dict[str, Any]] = []
        for r in filtered:
            row = dict(r)
            row["by_agent"] = by_run.get(str(r["run_key"]), {})
            out.append(row)
        return out


def _ingested_period_match(ingested_at: str, period: str) -> bool:
    """Match ingest timestamp to today / yesterday / week (UTC boundaries)."""
    if not period or period == "all":
        return True
    try:
        from datetime import datetime, timedelta, timezone

        raw = ingested_at.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "today":
            return day >= today_start
        if period == "yesterday":
            return yesterday_start <= day < today_start
        if period == "week":
            return day >= week_start
        return True
    except (ValueError, TypeError):
        return True


def get_default_store() -> BacktestStore:
    return BacktestStore()
