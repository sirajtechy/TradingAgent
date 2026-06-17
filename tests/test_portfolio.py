"""Unit tests for portfolio intelligence engine."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from agents.portfolio.config import load_rules
from agents.portfolio.metrics import build_summary, max_drawdown, monthly_returns_from_curve
from agents.portfolio.models import Holding
from agents.portfolio.rebalancer import frr_actions, rebalance_dates
from agents.portfolio.regime import compute_supertrend, is_bull_regime
from agents.portfolio.scorer import compute_momentum_score, rank_universe
from agents.portfolio.selector import select_portfolio
from agents.portfolio.sizer import size_positions, shares_from_allocation
from agents.portfolio.universe import exit_rank_threshold, load_universe


def _synthetic_df(start: float, daily_return: float, n: int = 260) -> pd.DataFrame:
    rows = []
    price = start
    for i in range(n):
        rows.append(
            {
                "Open": price,
                "High": price * 1.01,
                "Low": price * 0.99,
                "Close": price,
                "Volume": 2_000_000,
            }
        )
        price *= 1.0 + daily_return
    idx = pd.date_range(end=date(2025, 6, 1), periods=n, freq="B")
    return pd.DataFrame(rows, index=idx)


def test_load_universe_top10():
    tickers, sectors = load_universe("top10")
    assert len(tickers) >= 50
    assert "NVDA" in tickers
    assert sectors["NVDA"] == "Information Technology"


def test_exit_rank_threshold():
    assert exit_rank_threshold(500, 0.10) == 50
    assert exit_rank_threshold(120, 0.10) == 12


def test_momentum_score_uptrend():
    rules = load_rules()
    df = _synthetic_df(100.0, 0.002, n=260)
    score, parts = compute_momentum_score(df, rules)
    assert score is not None
    assert score > 0
    assert "return_6m" in parts


def test_rank_universe_orders_by_momentum():
    rules = load_rules()
    rules.min_avg_dollar_volume = 0
    fast = _synthetic_df(50.0, 0.003, n=260)
    slow = _synthetic_df(50.0, 0.0005, n=260)
    spy = _synthetic_df(400.0, 0.001, n=260)
    ranked = rank_universe(
        price_data={"FAST": fast, "SLOW": slow},
        spy_df=spy,
        ticker_to_sector={"FAST": "Information Technology", "SLOW": "Energy"},
        rules=rules,
        as_of=date(2025, 6, 1),
    )
    assert ranked[0].ticker == "FAST"
    assert ranked[0].rank == 1


def test_sector_cap_selection():
    rules = load_rules()
    rules.budget = 100_000
    rules.sector_cap_pct = 0.25
    rules.num_stocks = 4
    from agents.portfolio.models import TickerScore

    ranked = [
        TickerScore("A", "IT", 1, 90, 1.0),
        TickerScore("B", "IT", 2, 85, 0.9),
        TickerScore("C", "IT", 3, 80, 0.8),
        TickerScore("D", "Energy", 4, 75, 0.7),
        TickerScore("E", "Health Care", 5, 70, 0.6),
    ]
    selected = select_portfolio(ranked, num_stocks=4, rules=rules)
    sectors = {s.sector for s in selected}
    assert len(selected) <= 4
    assert "Energy" in sectors or "Health Care" in sectors


def test_frr_remove_below_exit_rank():
    holdings = {
        "AAA": Holding("AAA", "IT", 10, date(2025, 1, 1), 100, 1000, 1, 90),
        "BBB": Holding("BBB", "Energy", 5, date(2025, 1, 1), 50, 250, 2, 85),
    }
    from agents.portfolio.models import TickerScore

    ranked = [
        TickerScore("AAA", "IT", 60, 50, 0.1),
        TickerScore("BBB", "Energy", 5, 80, 0.8),
        TickerScore("CCC", "IT", 1, 95, 1.2),
    ]
    to_remove, to_hold, replacements = frr_actions(holdings, ranked, exit_rank=50, num_stocks=2)
    assert "AAA" in to_remove
    assert "BBB" in to_hold


def test_rebalance_dates_monthly():
    dates = rebalance_dates(date(2025, 1, 1), date(2025, 3, 31), day_of_month=21)
    assert len(dates) == 3
    assert dates[0] == date(2025, 1, 21)


def test_size_positions_equal_weight():
    rules = load_rules()
    from agents.portfolio.models import TickerScore

    selected = [
        TickerScore("A", "IT", 1, 90, 1.0),
        TickerScore("B", "Energy", 2, 85, 0.9),
    ]
    allocs = size_positions(selected, budget=200_000, rules=rules)
    assert sum(allocs.values()) == pytest.approx(200_000, rel=1e-6)
    assert allocs["A"] == pytest.approx(100_000)


def test_shares_from_allocation():
    assert shares_from_allocation(10_000, 250.0) == 40
    assert shares_from_allocation(10_000, 0) == 0


def test_metrics_max_drawdown():
    curve = [
        {"total_value": 100_000},
        {"total_value": 120_000},
        {"total_value": 90_000},
    ]
    assert max_drawdown(curve) == pytest.approx(25.0)


def test_metrics_summary():
    curve = [
        {"as_of": date(2025, 1, 31), "total_value": 100_000},
        {"as_of": date(2025, 2, 28), "total_value": 110_000},
    ]
    summary = build_summary(
        initial=100_000,
        final=110_000,
        start=date(2025, 1, 1),
        end=date(2025, 2, 28),
        equity_curve=curve,
        trade_count=4,
        regime_cash_months=0,
    )
    assert summary["total_return_pct"] == pytest.approx(10.0)


def test_supertrend_bull_on_uptrend():
    df = _synthetic_df(100.0, 0.005, n=60)
    assert is_bull_regime(df, period=10, multiplier=2.5) is True


def test_monthly_returns_from_curve():
    curve = [
        {"as_of": date(2025, 1, 31), "total_value": 100_000},
        {"as_of": date(2025, 2, 28), "total_value": 105_000},
    ]
    monthly = monthly_returns_from_curve(curve)
    assert len(monthly) == 2
    assert monthly[1]["return_pct"] == pytest.approx(5.0)


def test_enrich_top_candidates_parallel_respects_max_workers(monkeypatch):
    import threading
    import time

    import agents.orchestrator.pipeline_full as pipeline_full
    import agents.portfolio.enrich as enrich_mod

    session_calls: list[str] = []
    monkeypatch.setattr(
        pipeline_full,
        "load_or_run_session_context",
        lambda as_of_date: session_calls.append(as_of_date) or {},
    )

    lock = threading.Lock()
    active = [0]
    max_concurrent = {"max": 0}

    def fake_full(sym, as_of_date, *, strategy_profile):
        with lock:
            active[0] += 1
            max_concurrent["max"] = max(max_concurrent["max"], active[0])
        try:
            time.sleep(0.02)
            return {
                "phoenix_fusion_score": 72.0,
                "strategy_blend_score": 55.0,
                "intelligence_consensus": 60.0,
                "smoothness": 50.0,
                "phoenix_signal": "BUY",
            }
        finally:
            with lock:
                active[0] -= 1

    monkeypatch.setattr(enrich_mod, "_enrich_one_full", fake_full)

    tickers = [f"T{i}" for i in range(12)]
    result = enrich_mod.enrich_top_candidates(
        tickers,
        "2026-06-13",
        max_tickers=12,
        full_agents=True,
        max_workers=4,
    )

    assert len(result) == 12
    assert session_calls == ["2026-06-13"]
    assert max_concurrent["max"] <= 4
    assert max_concurrent["max"] > 1
    assert result["T0"]["phoenix_fusion_score"] == pytest.approx(72.0)
