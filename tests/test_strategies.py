"""Unit tests for trader strategy intelligence layer."""

from __future__ import annotations

from datetime import date

from agents.phoenix.models import OHLCVBar, PhoenixRequest, PhoenixSnapshot, SMABundle
from agents.strategies.common.features import compute_rmv, compute_rs_rank, is_rangebound
from agents.strategies.common.models import StrategyContext, bars_from_closes
from agents.strategies.common.registry import resolve_profile, run_strategies
from agents.strategies.fusion import build_meta_signals
from agents.strategies.minervini.chase_guard import evaluate_chase_guard
from agents.strategies.minervini.service import analyze as minervini_analyze
from agents.strategies.moglen.service import analyze as moglen_analyze
from agents.strategies.breitstein.service import analyze as breitstein_analyze
from agents.strategies.mcintosh.service import analyze as mcintosh_analyze


def _uptrend_closes(n: int = 260, start: float = 50.0, step_scale: float = 0.002) -> list[float]:
    closes = []
    price = start
    for _ in range(n):
        price *= 1.0 + step_scale
        closes.append(round(price, 2))
    return closes


def _make_snapshot(ticker: str = "TEST", closes: list[float] | None = None) -> PhoenixSnapshot:
    closes = closes or _uptrend_closes()
    bars = bars_from_closes(closes)
    req = PhoenixRequest(ticker=ticker, as_of_date=bars[-1].bar_date)
    price = bars[-1].close
    return PhoenixSnapshot(
        request=req,
        bars=bars,
        smas=SMABundle(
            sma10=price * 0.99,
            sma20=price * 0.97,
            sma50=price * 0.92,
            sma200=price * 0.80,
            sma40w=price * 0.82,
            sma10_prior=price * 0.985,
            sma20_prior=price * 0.965,
            sma50_prior=price * 0.915,
            sma200_prior=price * 0.795,
        ),
        vol_avg_20=1_000_000,
        high_52w=price * 1.05,
        low_52w=price * 0.55,
        as_of_price=price,
        as_of_price_date=bars[-1].bar_date,
    )


def _phoenix_result(*, signal: str = "BUY", stage: int = 2) -> dict:
    return {
        "signal": signal,
        "score": 78.0,
        "stage": {"stage": stage, "label": "Momentum", "action": "TRADE"},
        "pattern": {
            "pattern_name": "VCP",
            "confirmed": True,
            "volume_confirmed": True,
            "pivot_price": 100.0,
            "confidence": 0.85,
            "vcp_contractions": 3,
            "description": "Textbook VCP.",
        },
        "entry": {"entry_price": 101.0, "entry_type": "pivot_breakout"},
        "risk": {"stop_price": 94.0, "stop_pct": 7.0},
        "extension_guardrail": {
            "chase_risk": "low",
            "metrics": {"pct_from_pivot": 1.0},
            "flags": [],
            "summary": "Low extension.",
        },
    }


def test_resolve_profile_blend():
    assert resolve_profile("blend") == ["minervini", "moglen", "breitstein", "mcintosh"]
    assert resolve_profile("minervini") == ["minervini"]


def test_compute_rmv_bounded():
    bars = bars_from_closes(_uptrend_closes(40))
    rmv = compute_rmv(bars)
    assert rmv is not None
    assert 0.0 <= rmv <= 100.0


def test_compute_rs_rank_outperformer():
    ticker = bars_from_closes(_uptrend_closes(80, 100.0, step_scale=0.008))
    spy = bars_from_closes(_uptrend_closes(80, 100.0, step_scale=0.001))
    rs = compute_rs_rank(ticker, spy)
    assert rs is not None
    assert rs > 50.0


def test_chase_guard_flags_extended_pivot():
    chase = evaluate_chase_guard(
        {
            "extension_guardrail": {
                "chase_risk": "elevated",
                "metrics": {"pct_from_pivot": 8.0},
                "flags": ["extended_from_pivot"],
            }
        }
    )
    assert chase["invalid_if_chasing"] is True


def test_minervini_analyze_stage2_vcp():
    snap = _make_snapshot()
    ctx = StrategyContext(
        ticker="NVDA",
        as_of_date=snap.as_of_price_date.isoformat(),
        snapshot=snap,
        spy_snapshot=snap,
        phoenix_result=_phoenix_result(),
        fund_result={"frameworks": {"growth_profile": {"eps_qoq_growth_pct": 12.0}}},
    )
    sig = minervini_analyze(ctx)
    assert sig.strategy_id == "minervini"
    assert sig.setup_detected is True
    assert sig.subscores["vcp_quality"] > 0
    d = sig.to_dict()
    assert "trend_template" in d["subscores"]


def test_moglen_regime_and_setup():
    snap = _make_snapshot()
    ctx = StrategyContext(
        ticker="NVDA",
        as_of_date=snap.as_of_price_date.isoformat(),
        snapshot=snap,
        spy_snapshot=snap,
        phoenix_result=_phoenix_result(),
    )
    sig = moglen_analyze(ctx)
    assert sig.strategy_id == "moglen"
    assert sig.regime_ok is True
    assert sig.setup_type == "vcp_base_breakout"


def test_breitstein_rangebound_disqualifies():
    flat = [100.0] * 40
    snap = _make_snapshot(closes=flat)
    ctx = StrategyContext(
        ticker="XYZ",
        as_of_date=snap.as_of_price_date.isoformat(),
        snapshot=snap,
        phoenix_result=_phoenix_result(signal="BUY"),
    )
    assert is_rangebound(snap.bars) is True
    sig = breitstein_analyze(ctx)
    assert any("Rangebound" in d for d in sig.disqualifiers)


def test_mcintosh_leader_tiers():
    snap = _make_snapshot()
    ctx = StrategyContext(
        ticker="NVDA",
        as_of_date=snap.as_of_price_date.isoformat(),
        snapshot=snap,
        spy_snapshot=snap,
        phoenix_result=_phoenix_result(),
    )
    sig = mcintosh_analyze(ctx)
    assert sig.strategy_id == "mcintosh"
    assert sig.subscores["starter_position_pct"] >= 3.0


def test_run_strategies_blend_and_meta():
    snap = _make_snapshot()
    ctx = StrategyContext(
        ticker="NVDA",
        as_of_date=snap.as_of_price_date.isoformat(),
        snapshot=snap,
        spy_snapshot=snap,
        phoenix_result=_phoenix_result(),
        fund_result={"frameworks": {"growth_profile": {"revenue_yoy_growth_pct": 25.0}}},
    )
    layers = run_strategies(ctx, "blend")
    assert set(layers.keys()) == {"minervini", "moglen", "breitstein", "mcintosh"}
    meta = build_meta_signals(layers)
    assert "blend_score" in meta
    assert "high_conviction_swing" in meta
    assert meta["consensus_total"] == 4
