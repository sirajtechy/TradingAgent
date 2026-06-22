"""Tests for SQLite backtest registry."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.persistence.backtest_store import BacktestStore
from core.persistence.ingest import ingest_master_pilot


@pytest.fixture
def store(tmp_path: Path) -> BacktestStore:
    return BacktestStore(db_path=tmp_path / "test.sqlite")


def test_upsert_and_get_run(store: BacktestStore, tmp_path: Path) -> None:
    master = tmp_path / "master_pilot.json"
    master.write_text(
        json.dumps(
            {
                "run_id": "test_run",
                "manifest": {"signal_date": "2025-04-01", "eval_days": 15},
                "confusion_matrix": {
                    "cumulative": {
                        "by_agent": {
                            "fusion": {"TP": 2, "FP": 1, "TN": 0, "FN": 0, "accuracy_pct": 66.7},
                            "technical": {"TP": 3, "FP": 0, "TN": 0, "FN": 0, "accuracy_pct": 100.0},
                        }
                    }
                },
                "tickers": {
                    "AAPL": {
                        "sector": "Technology",
                        "fusion_final_signal": "bullish",
                        "signal_correct": True,
                        "pass_enrichment": True,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    rk = ingest_master_pilot(master, store=store)
    assert rk is not None

    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0]["signal_date"] == "2025-04-01"
    assert runs[0]["ticker_count"] == 1
    assert runs[0]["pass_count"] == 1

    detail = store.get_run(rk)
    assert detail is not None
    by_agent = detail["confusion_matrix"]["cumulative"]["by_agent"]
    assert by_agent["fusion"]["TP"] == 2
    assert "AAPL" in detail["tickers"]


def test_timeline_summary(store: BacktestStore, tmp_path: Path) -> None:
    for sd in ("2025-01-01", "2025-02-01"):
        p = tmp_path / f"master_{sd}.json"
        p.write_text(
            json.dumps(
                {
                    "manifest": {"signal_date": sd},
                    "confusion_matrix": {
                        "cumulative": {
                            "by_agent": {"fusion": {"accuracy_pct": 55.0, "TP": 1, "FP": 1, "TN": 0, "FN": 0}}
                        }
                    },
                    "tickers": {"X": {}},
                }
            ),
            encoding="utf-8",
        )
        ingest_master_pilot(p, store=store)

    timeline = store.timeline_summary()
    assert len(timeline) == 2
    assert timeline[0]["signal_date"] == "2025-01-01"
