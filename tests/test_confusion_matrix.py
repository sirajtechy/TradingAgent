"""Confusion matrix evaluation tests."""

from __future__ import annotations

from core.evaluation.confusion import build_confusion_payload, confusion_from_rows, mcc
from core.evaluation.walk_forward import split_walk_forward_windows
from core.universe import empty_matrix, matrix_metrics, update_matrix
from datetime import date


def test_mcc_perfect():
    assert mcc(10, 0, 10, 0) == 1.0


def test_matrix_metrics_includes_mcc():
    m = empty_matrix()
    update_matrix(m, {"signal": "bullish", "signal_correct": True})
    update_matrix(m, {"signal": "bearish", "signal_correct": True})
    met = matrix_metrics(m)
    assert met.get("mcc") is not None


def test_build_confusion_payload_by_agent():
    rows = [
        {
            "signal": "bullish",
            "signal_correct": True,
            "phoenix_signal": "bullish",
            "signal_correct_phoenix": True,
            "technical_signal": "bullish",
            "signal_correct_technical": False,
        },
        {
            "signal": "bearish",
            "signal_correct": True,
            "phoenix_signal": "neutral",
            "signal_correct_phoenix": None,
            "technical_signal": "neutral",
            "signal_correct_technical": None,
        },
    ]
    payload = build_confusion_payload(rows)
    by_agent = payload["cumulative"]["by_agent"]
    assert "fusion" in by_agent
    assert "technical" in by_agent
    assert by_agent["technical"]["TP"] + by_agent["technical"]["FP"] >= 1


def test_confusion_from_rows_fundamental():
    rows = [
        {"fund_signal": "bullish", "signal_correct_fundamental": True},
        {"fund_signal": "bullish", "signal_correct_fundamental": False},
    ]
    met = confusion_from_rows(rows, signal_key="fund_signal", correct_key="signal_correct_fundamental")
    assert met["TP"] == 1
    assert met["FP"] == 1


def test_walk_forward_splits():
    months = [(date(2025, m, 1), date(2025, m, 28)) for m in range(1, 13)]
    splits = split_walk_forward_windows(months, train_size=6, test_size=1)
    assert len(splits) >= 1
    train, test = splits[0]
    assert len(train) == 6
    assert len(test) == 1
