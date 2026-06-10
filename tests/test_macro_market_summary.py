from __future__ import annotations

from agents.macro.fred_client import _cpi_yoy_pct, _parse_observations
from agents.macro.models import MacroSeriesPoint
from agents.macro.rules import evaluate_metrics
from agents.market_summary.models import MarketDataSnapshot, TickerPerformance
from agents.market_summary.rules import evaluate_market_summary


def test_parse_fred_observations_skips_missing_values():
    payload = {
        "observations": [
            {"date": "2026-05-01", "value": "5.25"},
            {"date": "2026-04-01", "value": "."},
            {"date": "2026-03-01", "value": "5.00"},
        ]
    }
    rows = _parse_observations("DFF", payload)
    assert len(rows) == 2
    assert rows[0].value == 5.25


def test_cpi_yoy_pct_computation():
    from datetime import date

    rows = [MacroSeriesPoint("CPIAUCSL", date(2026, 1, 1), 299.0) for _ in range(13)]
    rows[0] = MacroSeriesPoint("CPIAUCSL", date(2026, 6, 1), 310.0)
    rows[12] = MacroSeriesPoint("CPIAUCSL", date(2025, 6, 1), 300.0)
    yoy = _cpi_yoy_pct(rows)
    assert yoy is not None
    assert round(yoy, 1) == 3.3


def test_macro_evaluate_metrics_bullish_when_disinflation_and_positive_curve():
    metrics = {
        "as_of_date": "2026-06-01",
        "fed_funds": 5.0,
        "prior_fed_funds": 5.0,
        "cpi_yoy_pct": 2.4,
        "prior_cpi_yoy_pct": 3.1,
        "unemployment": 3.8,
        "yield_spread_10y2y": 0.4,
    }
    result = evaluate_metrics(metrics, [], ["fred:DFF", "fred:CPIAUCSL"])
    assert result["signal"] in {"bullish", "neutral"}
    assert result["score"] >= 50
    assert len(result["bullets"]) <= 3


def test_market_summary_extreme_vix_caps_signal():
    snapshot = MarketDataSnapshot(
        as_of_date=__import__("datetime").date(2026, 6, 1),
        vix=32.0,
        vix_regime="extreme",
        spy=TickerPerformance("SPY", "S&P 500", 500.0, 1.0, 2.0, None),
        sectors=[
            TickerPerformance("XLK", "Information Technology", 200.0, 1.0, 3.0, 1.0),
        ],
    )
    macro_eval = {"score": 60, "signal": "bullish", "confidence": "medium", "metrics": {}, "warnings": [], "data_sources": ["fred:DFF"]}
    result = evaluate_market_summary(market_snapshot=snapshot, macro_eval=macro_eval)
    assert result["vix_regime"] == "extreme"
    assert result["market_wide_signal"] in {"neutral", "bearish"}
