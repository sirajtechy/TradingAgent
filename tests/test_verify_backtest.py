"""Unit tests for isolated backtest verification utility."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from scripts.verify.artifact_loader import (
    detect_artifact_type,
    discover_artifacts,
    load_rows_from_artifact,
    load_verify_rows,
)
from scripts.verify.diff_report import build_summary, verify_row
from scripts.verify.models import VerifyRow
from scripts.verify.polygon_checks import (
    close_on_or_before,
    correctness_for_signal,
    target_hit_within_window,
)
from scripts.verify.runner import run_verification


@pytest.fixture
def sample_bars() -> pd.DataFrame:
    """Daily bars spanning a 15-day eval window."""
    idx = pd.DatetimeIndex(
        [
            "2025-04-01",
            "2025-04-02",
            "2025-04-03",
            "2025-04-04",
            "2025-04-07",
            "2025-04-08",
            "2025-04-09",
            "2025-04-10",
            "2025-04-11",
            "2025-04-14",
            "2025-04-15",
            "2025-04-16",
            "2025-04-17",
        ]
    )
    return pd.DataFrame(
        {
            "Open": [100.0] * len(idx),
            "High": [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 130.0, 108.0, 109.0, 110.0, 111.0, 112.0],
            "Low": [99.0] * len(idx),
            "Close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 128.0, 107.5, 108.5, 109.5, 110.5, 111.5],
            "Volume": [1_000_000] * len(idx),
        },
        index=idx,
    )


def test_close_on_or_before(sample_bars: pd.DataFrame) -> None:
    px, dt = close_on_or_before(sample_bars, date(2025, 4, 2))
    assert px == 101.5
    assert dt == "2025-04-02"


def test_target_hit_within_window(sample_bars: pd.DataFrame) -> None:
    hit = target_hit_within_window(date(2025, 4, 2), date(2025, 4, 17), 125.0, sample_bars)
    assert hit["target_hit"] is True
    assert hit["target_hit_date"] == "2025-04-10"

    miss = target_hit_within_window(date(2025, 4, 2), date(2025, 4, 17), 200.0, sample_bars)
    assert miss["target_hit"] is False
    assert miss["target_hit_date"] is None


def test_correctness_for_signal() -> None:
    te_hit = {"target_hit": True}
    te_miss = {"target_hit": False}
    assert correctness_for_signal("bullish", te_hit) is True
    assert correctness_for_signal("bullish", te_miss) is False
    assert correctness_for_signal("bearish", te_hit) is False
    assert correctness_for_signal("bearish", te_miss) is True
    assert correctness_for_signal("neutral", te_hit) is None


def test_load_master_pilot(tmp_path: Path) -> None:
    master = tmp_path / "master_pilot.json"
    master.write_text(
        json.dumps(
            {
                "manifest": {
                    "signal_date": "2025-04-02",
                    "result_date": "2025-04-17",
                    "eval_days": 15,
                },
                "tickers": {
                    "AAPL": {
                        "entry_price": 101.5,
                        "exit_price": 111.5,
                        "exit_reference_date": "2025-04-17",
                        "backtest_target_price": 125.0,
                        "target_hit": True,
                        "target_hit_date": "2025-04-08",
                        "fusion_final_signal": "bullish",
                        "technical_signal": "bullish",
                        "signal_correct": True,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    assert detect_artifact_type(json.loads(master.read_text()), master) == "master_pilot"
    rows, manifest = load_rows_from_artifact(master)
    assert len(rows) == 1
    assert rows[0].ticker == "AAPL"
    assert rows[0].entry_price == 101.5
    assert rows[0].target_hit is True
    assert manifest["signal_date"] == "2025-04-02"


def test_load_pilot_results(tmp_path: Path) -> None:
    pilot = tmp_path / "pilot_results.json"
    pilot.write_text(
        json.dumps(
            {
                "manifest": {"signal_date": "2025-04-02", "eval_days": 15},
                "results": {
                    "MSFT": {
                        "periods": [
                            {
                                "signal_date": "2025-04-02",
                                "result_date": "2025-04-17",
                                "start_price": 400.0,
                                "start_price_date": "2025-04-02",
                                "exit_reference_price": 410.0,
                                "target_price": 420.0,
                                "target_hit": False,
                                "signal": "bullish",
                                "technical_signal": "bullish",
                                "signal_correct": False,
                            }
                        ]
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    rows, _ = load_rows_from_artifact(pilot)
    assert len(rows) == 1
    assert rows[0].ticker == "MSFT"
    assert rows[0].start_price_date == "2025-04-02"


def test_discover_prefers_master_pilot(tmp_path: Path) -> None:
    run_dir = tmp_path / "sector_it_2025-04-02"
    run_dir.mkdir()
    (run_dir / "pilot_results.json").write_text(json.dumps({"results": {}}), encoding="utf-8")
    (run_dir / "master_pilot.json").write_text(
        json.dumps({"manifest": {"signal_date": "2025-04-02"}, "tickers": {}}),
        encoding="utf-8",
    )
    found = discover_artifacts(tmp_path)
    assert len(found) == 1
    assert found[0].name == "master_pilot.json"


def test_verify_row_pass() -> None:
    row = VerifyRow(
        ticker="AAPL",
        signal_date="2025-04-02",
        result_date="2025-04-17",
        entry_price=101.5,
        target_hit=True,
        target_hit_date="2025-04-08",
        signal_correct=True,
        technical_signal="bullish",
    )
    recomputed = {
        "entry_price": 101.5,
        "target_hit": True,
        "target_hit_date": "2025-04-08",
        "signal_correct": True,
        "signal_correct_technical": True,
    }
    rv = verify_row(row, recomputed)
    assert rv.status == "PASS"


def test_verify_row_fail_target_hit() -> None:
    row = VerifyRow(
        ticker="AAPL",
        signal_date="2025-04-02",
        result_date="2025-04-17",
        target_hit=True,
    )
    recomputed = {"target_hit": False}
    rv = verify_row(row, recomputed)
    assert rv.status == "FAIL"
    assert any(c.field == "target_hit" and c.status == "FAIL" for c in rv.checks)


def test_build_summary() -> None:
    row = VerifyRow(ticker="X", signal_date="2025-01-01", result_date="2025-01-15", target_hit=True)
    from scripts.verify.models import CheckResult, RowVerification

    results = [
        RowVerification(row=row, status="PASS", checks=[CheckResult(field="target_hit", status="PASS")]),
        RowVerification(
            row=row,
            status="FAIL",
            checks=[CheckResult(field="entry_price", status="FAIL", expected=1.0, actual=2.0)],
        ),
    ]
    summary = build_summary(results)
    assert summary["rows_total"] == 2
    assert summary["rows_pass"] == 1
    assert summary["rows_fail"] == 1
    assert summary["mismatch_by_field"]["entry_price"] == 1


def test_dry_run(tmp_path: Path) -> None:
    master = tmp_path / "master_pilot.json"
    master.write_text(
        json.dumps({"manifest": {"signal_date": "2025-04-02"}, "tickers": {"A": {"entry_price": 1.0}}}),
        encoding="utf-8",
    )
    report = run_verification(master, dry_run=True)
    assert report.summary["dry_run"] is True
    assert report.summary["rows_skip"] == 1


def test_build_verified_summary_tp() -> None:
    from scripts.verify.models import CheckResult, RowVerification
    from scripts.verify.verified_summary import build_verified_summary

    row = VerifyRow(
        ticker="INLX",
        signal_date="2025-04-01",
        result_date="2025-04-16",
        entry_price=14.21,
        target_price=14.92,
        target_hit=True,
        target_hit_date="2025-04-10",
        fusion_final_signal="bullish",
        signal_correct=True,
    )
    rv = RowVerification(
        row=row,
        status="PASS",
        checks=[
            CheckResult(field="entry_price", status="PASS", expected=14.21, actual=14.21),
            CheckResult(field="target_hit", status="PASS", expected=True, actual=True),
        ],
    )
    vs = build_verified_summary([rv])
    assert vs["artifact_claimed"]["bullish_tp"] == 1
    assert vs["polygon_verified"]["confirmed_tp"] == 1
    assert vs["verified_tp_tickers"][0]["ticker"] == "INLX"


def test_load_verify_rows_directory(tmp_path: Path) -> None:
    d1 = tmp_path / "sector_a_2025-04-02"
    d2 = tmp_path / "sector_a_2025-04-15"
    for d in (d1, d2):
        d.mkdir()
        (d / "master_pilot.json").write_text(
            json.dumps({"manifest": {"signal_date": d.name[-10:]}, "tickers": {"T": {}}}),
            encoding="utf-8",
        )
    rows, manifests = load_verify_rows(tmp_path)
    assert len(rows) == 2
    assert len(manifests) == 2
