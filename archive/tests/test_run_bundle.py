"""run_bundle aggregate + compare (no I/O)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.run_bundle import (
    SCHEMA_VERSION,
    build_run_bundle,
    compare_bundles,
    row_from_labeled_backtest_period,
)


def test_row_from_labeled_backtest_period_sets_evaluation():
    row = row_from_labeled_backtest_period(
        "XOM",
        "2024-12-31",
        "Energy",
        {
            "signal": "bullish",
            "orchestrator_score": 70.0,
            "conflict_detected": False,
            "phoenix_signal": "bullish",
            "phoenix_score": 72.0,
            "fund_score": 65.0,
            "signal_correct": True,
            "signal_date": "2024-12-31",
            "result_date": "2025-01-30",
            "start_price": 100.0,
            "exit_reference_price": 102.5,
            "exit_reference_date": "2025-01-30",
            "target_price": 105.0,
            "target_hit": True,
            "target_hit_date": "2025-01-10",
            "trade_levels": {"pattern_name": "VCP", "exit_reference_price": 102.5},
        },
        "per_ticker/XOM.json",
    )
    assert row["phoenix_signal"] == "BUY"
    assert row["evaluation"]["signal_correct"] is True
    assert row["evaluation"]["directional_labels_available"] is True
    assert row["backtest"]["entry_price"] == 100.0


def test_compare_bundles_normalizes_ticker_case():
    a = build_run_bundle(
        run_id="a",
        as_of_date="2026-01-01",
        fusion="phoenix-fa",
        universe_label="u",
        fund_data_source="yfinance",
        rows=[
            {
                "ticker": "xom",
                "sector": "Energy",
                "as_of_date": "2026-01-01",
                "fusion_mode": "phoenix-fa",
                "fusion_final_signal": "bullish",
                "fusion_orchestrator_score": 70.0,
                "fusion_conflict": False,
                "phoenix_signal": "BUY",
                "phoenix_score": 80,
                "fund_signal_normalized": "bullish",
                "fund_score": 65,
                "hard_filter_passed": True,
                "artifact_relative": "x.json",
                "error": None,
                "evaluation": {},
            }
        ],
        halal_universe_mode="full",
    )
    b = build_run_bundle(
        run_id="b",
        as_of_date="2026-01-02",
        fusion="phoenix-fa",
        universe_label="u",
        fund_data_source="yfinance",
        rows=[
            {
                "ticker": "XOM",
                "sector": "Energy",
                "as_of_date": "2026-01-02",
                "fusion_mode": "phoenix-fa",
                "fusion_final_signal": "neutral",
                "fusion_orchestrator_score": 55.0,
                "fusion_conflict": False,
                "phoenix_signal": "WATCH",
                "phoenix_score": 50,
                "fund_signal_normalized": "neutral",
                "fund_score": 50,
                "hard_filter_passed": True,
                "artifact_relative": "x.json",
                "error": None,
                "evaluation": {},
            }
        ],
        halal_universe_mode="full",
    )
    c = compare_bundles(a, b)
    assert c["per_ticker"]["XOM"]["changed"] is True
    assert SCHEMA_VERSION == "1.1.0"
