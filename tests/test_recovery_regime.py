"""Tests for Phase 2 post-correction recovery regime + Phoenix upgrade adapter."""

from __future__ import annotations

from datetime import date, timedelta

from agents.phoenix.models import OHLCVBar, PhoenixRequest, PhoenixSnapshot, SMABundle
from agents.strategies.common.recovery_regime import detect_recovery_regime
from agents.technical.recovery_upgrade import maybe_upgrade_phoenix


def _bars(closes: list[float], volumes: list[int] | None = None) -> list[OHLCVBar]:
    if volumes is None:
        volumes = [1_000_000] * len(closes)
    start = date(2023, 1, 1)
    out = []
    for i, c in enumerate(closes):
        out.append(OHLCVBar(
            bar_date=start + timedelta(days=i),
            open=c * 0.998,
            high=c * 1.005,
            low=c * 0.995,
            close=c,
            volume=volumes[i],
        ))
    return out


def _snapshot(closes: list[float], volumes: list[int] | None = None, ticker: str = "TEST") -> PhoenixSnapshot:
    bars = _bars(closes, volumes)
    last = bars[-1]
    return PhoenixSnapshot(
        request=PhoenixRequest(ticker=ticker, as_of_date=last.bar_date),
        bars=bars,
        smas=SMABundle(
            sma10=last.close, sma20=last.close, sma50=last.close, sma200=last.close,
            sma40w=last.close,
            sma10_prior=last.close, sma20_prior=last.close,
            sma50_prior=last.close, sma200_prior=last.close,
        ),
        vol_avg_20=1_000_000,
        high_52w=max(b.high for b in bars),
        low_52w=min(b.low for b in bars),
        as_of_price=last.close,
        as_of_price_date=last.bar_date,
    )


def _crash_then_recover_series(
    n_pre: int = 220,
    dd_pct: float = 18.0,
    recovery_days: int = 14,
) -> tuple[list[float], list[int]]:
    """Long uptrend → sharp drawdown → V-shape recovery with a follow-through day."""
    closes: list[float] = []
    volumes: list[int] = []
    p = 100.0
    for _ in range(n_pre):
        p *= 1.001
        closes.append(round(p, 2))
        volumes.append(1_000_000)
    peak = closes[-1]
    bottom = peak * (1.0 - dd_pct / 100.0)
    drop_days = 5
    for i in range(drop_days):
        p = peak - (peak - bottom) * ((i + 1) / drop_days)
        closes.append(round(p, 2))
        volumes.append(1_600_000)
    for i in range(recovery_days):
        gain = 1.012
        vol = 1_000_000
        if i == recovery_days - 3:
            gain = 1.025
            vol = 1_800_000
        p = closes[-1] * gain
        closes.append(round(p, 2))
        volumes.append(vol)
    return closes, volumes


def _crash_then_recover_closes(*args, **kwargs) -> list[float]:
    closes, _ = _crash_then_recover_series(*args, **kwargs)
    return closes


def _steady_uptrend_closes(n: int = 260) -> list[float]:
    p = 100.0
    closes = []
    for _ in range(n):
        p *= 1.0008
        closes.append(round(p, 2))
    return closes


def test_recovery_regime_fires_on_crash_then_rebound():
    closes, volumes = _crash_then_recover_series()
    snap = _snapshot(closes, volumes, ticker="SPY")
    regime = detect_recovery_regime(snap)
    assert regime["is_recovery"] is True, regime
    assert regime["max_drawdown_pct_in_window"] >= 8.0
    assert regime["follow_through_day"] is True
    assert regime["follow_through_still_valid"] is True
    assert regime["no_new_20d_low_in_last_5d"] is True


def test_recovery_regime_silent_during_steady_uptrend():
    snap = _snapshot(_steady_uptrend_closes(), ticker="SPY")
    regime = detect_recovery_regime(snap)
    assert regime["is_recovery"] is False
    assert "No recent correction" in regime["diagnostic"] or "criteria_unmet" in regime["reason"]


def test_recovery_regime_silent_during_active_drawdown():
    closes = [100.0]
    for _ in range(250):
        closes.append(closes[-1] * 0.998)
    snap = _snapshot(closes, ticker="SPY")
    regime = detect_recovery_regime(snap)
    assert regime["is_recovery"] is False


def test_phoenix_avoid_upgrades_to_watch_on_recovery():
    closes, vols = _crash_then_recover_series()
    spy_snap = _snapshot(closes, vols, ticker="SPY")
    ticker_snap = _snapshot(closes, vols, ticker="NVDA")

    px_avoid = {
        "signal": "AVOID",
        "score": 22.0,
        "hard_filter_passed": False,
        "hard_filter_reason": "Price below 200-day SMA",
        "stage": {"stage": 4, "label": "Decline", "action": "AVOID"},
        "pattern": {"pattern_name": "None", "confirmed": False},
        "warnings": [],
    }
    upgraded = maybe_upgrade_phoenix(px_avoid, ticker_snap, spy_snap)
    assert upgraded["signal"] == "WATCH"
    assert upgraded["phoenix_entry_mode"] == "recovery_upgrade"
    assert upgraded["recovery_regime"]["is_recovery"] is True
    assert upgraded["recovery_reclaim"]["passes"] is True


def test_phoenix_buy_never_modified_by_upgrade():
    closes = _crash_then_recover_closes()
    spy_snap = _snapshot(closes, ticker="SPY")
    ticker_snap = _snapshot(closes, ticker="NVDA")

    px_buy = {
        "signal": "BUY",
        "score": 88.0,
        "hard_filter_passed": True,
        "hard_filter_reason": None,
    }
    result = maybe_upgrade_phoenix(px_buy, ticker_snap, spy_snap)
    assert result["signal"] == "BUY"
    assert result["phoenix_entry_mode"] == "standard"


def test_phoenix_avoid_stays_when_regime_silent():
    closes = _steady_uptrend_closes()
    spy_snap = _snapshot(closes, ticker="SPY")
    ticker_snap = _snapshot([c * 0.5 for c in closes], ticker="BROKEN")

    px_avoid = {
        "signal": "AVOID",
        "score": 18.0,
        "hard_filter_passed": False,
        "hard_filter_reason": "Price 35% above 52-week low (need >= 50%)",
    }
    result = maybe_upgrade_phoenix(px_avoid, ticker_snap, spy_snap)
    assert result["signal"] == "AVOID"
    assert result["phoenix_entry_mode"] == "standard"


def test_recovery_upgrade_requires_both_regime_and_reclaim():
    """In a recovery regime, a ticker that is still making new 20d lows must NOT upgrade."""
    spy_closes, vols = _crash_then_recover_series()
    spy_snap = _snapshot(spy_closes, vols, ticker="SPY")
    falling = []
    p = 100.0
    for _ in range(260):
        p *= 0.997
        falling.append(round(p, 2))
    broken_snap = _snapshot(falling, ticker="BROKEN")

    px_avoid = {
        "signal": "AVOID",
        "score": 12.0,
        "hard_filter_passed": False,
        "hard_filter_reason": "Price below 200-day SMA",
    }
    result = maybe_upgrade_phoenix(px_avoid, broken_snap, spy_snap)
    assert result["signal"] == "AVOID", "Ticker still in downtrend must not upgrade."
    assert result["phoenix_entry_mode"] == "standard"
    assert result["recovery_regime"]["is_recovery"] is True
    assert result["recovery_reclaim"]["passes"] is False
