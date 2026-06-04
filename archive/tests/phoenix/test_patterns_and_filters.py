"""
Tests for Phoenix hard filters and pattern dispatch.

All inputs are synthetic OHLCV bars so these tests never touch the network.
"""

from datetime import date, timedelta
from typing import List, Optional

from agents.phoenix.config import PhoenixSettings
from agents.phoenix.filters import apply_hard_filters
from agents.phoenix.models import OHLCVBar, PhoenixRequest, PhoenixSnapshot, SMABundle
from agents.phoenix.patterns import detect_all_patterns


def _bar(day: int, close: float, volume: float = 1_000_000.0) -> OHLCVBar:
    return OHLCVBar(
        bar_date=date(2025, 1, 1) + timedelta(days=day),
        open=close - 0.2,
        high=close + 0.5,
        low=close - 0.5,
        close=close,
        volume=volume,
    )


def _snapshot(
    bars: List[OHLCVBar],
    *,
    sma200: Optional[float] = 80.0,
    low_52w: float = 50.0,
    sma10: Optional[float] = None,
    sma20: Optional[float] = None,
) -> PhoenixSnapshot:
    last = bars[-1]
    return PhoenixSnapshot(
        request=PhoenixRequest(ticker="TEST", as_of_date=last.bar_date),
        bars=bars,
        smas=SMABundle(
            sma10=sma10,
            sma20=sma20,
            sma50=90.0,
            sma200=sma200,
            sma40w=sma200,
        ),
        vol_avg_20=sum(b.volume for b in bars[-20:]) / min(len(bars), 20),
        high_52w=max(b.high for b in bars),
        low_52w=low_52w,
        as_of_price=last.close,
        as_of_price_date=last.bar_date,
        warnings=[],
    )


class TestPhoenixHardFilters:
    def test_passes_when_above_sma200_and_52w_low_threshold(self):
        snapshot = _snapshot([_bar(0, 100.0)], sma200=80.0, low_52w=50.0)

        result = apply_hard_filters(snapshot)

        assert result.passed is True
        assert result.failure_reason is None
        assert len(result.checks) == 2

    def test_fails_when_price_below_sma200(self):
        snapshot = _snapshot([_bar(0, 75.0)], sma200=80.0, low_52w=40.0)

        result = apply_hard_filters(snapshot)

        assert result.passed is False
        assert "below 200-day SMA" in result.failure_reason

    def test_fails_when_not_far_enough_above_52w_low(self):
        snapshot = _snapshot([_bar(0, 120.0)], sma200=80.0, low_52w=100.0)

        result = apply_hard_filters(snapshot)

        assert result.passed is False
        assert "52w-low" in result.failure_reason


class TestPhoenixPatternDispatcher:
    def test_detects_confirmed_flat_base_breakout(self):
        base_bars = [
            _bar(i, 100.0 + ((i % 5) - 2) * 0.2, volume=1_200_000.0 - i * 10_000.0)
            for i in range(25)
        ]
        breakout = _bar(25, 102.0, volume=3_000_000.0)
        snapshot = _snapshot(base_bars + [breakout], sma10=100.0, sma20=100.0)

        match = detect_all_patterns(snapshot, PhoenixSettings())

        assert match.pattern_name == "Flat Base"
        assert match.confirmed is True
        assert match.volume_confirmed is True
        assert match.pivot_price > 0

    def test_returns_none_pattern_when_history_is_too_short(self):
        snapshot = _snapshot([_bar(0, 100.0), _bar(1, 100.5)])

        match = detect_all_patterns(snapshot)

        assert match.pattern_name == "None"
        assert match.confidence == 0.0
