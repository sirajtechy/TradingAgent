"""
test_trade_filter.py — Tests for the post-fusion trade quality gate.

Verifies each individual check and the composite gate function.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.orchestrator.trade_filter import (
    check_base_tightness,
    check_volume_contraction,
    check_liquidity,
    check_relative_strength,
    check_trend_alignment,
    evaluate_trade_quality,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_closes(n: int = 60, start: float = 100.0, slope: float = 0.2) -> list:
    return [start + i * slope for i in range(n)]


def _make_hvl(closes: list, spread: float = 0.5) -> tuple:
    highs   = [c + spread for c in closes]
    lows    = [c - spread for c in closes]
    return highs, lows


def _make_volumes(n: int = 60, base: float = 2_000_000.0) -> list:
    return [base] * n


# ---------------------------------------------------------------------------
# check_base_tightness
# ---------------------------------------------------------------------------

class TestCheckBaseTightness:

    def test_tight_base_passes(self):
        closes = _make_closes(20)
        highs, lows = _make_hvl(closes, spread=0.1)  # ~0.2% range on $100 stock
        result = check_base_tightness(highs, lows, closes)
        assert result["passed"] is True

    def test_wide_base_fails(self):
        closes = _make_closes(20)
        highs, lows = _make_hvl(closes, spread=5.0)  # ~10% range → fails 3% threshold
        result = check_base_tightness(highs, lows, closes)
        assert result["passed"] is False

    def test_insufficient_bars_passes_by_default(self):
        result = check_base_tightness([101.0], [99.0], [100.0])
        assert result["passed"] is True
        assert "note" in result

    def test_custom_threshold(self):
        closes = _make_closes(20)
        highs, lows = _make_hvl(closes, spread=0.5)  # ~1% range
        # Should fail with max_range_pct=0.5
        result = check_base_tightness(highs, lows, closes, max_range_pct=0.5)
        assert result["passed"] is False


# ---------------------------------------------------------------------------
# check_volume_contraction
# ---------------------------------------------------------------------------

class TestCheckVolumeContraction:

    def test_contracting_volume_passes(self):
        # Recent 5 days at half the prior 10-day average
        volumes = [2_000_000.0] * 10 + [1_000_000.0] * 5
        result = check_volume_contraction(volumes)
        assert result["passed"] is True
        assert result["ratio"] < 1.0

    def test_expanding_volume_fails(self):
        # Recent 5 days twice the prior average
        volumes = [1_000_000.0] * 10 + [2_000_000.0] * 5
        result = check_volume_contraction(volumes)
        assert result["passed"] is False
        assert result["ratio"] > 1.0

    def test_insufficient_bars_passes_by_default(self):
        result = check_volume_contraction([1_000_000.0] * 5)
        assert result["passed"] is True
        assert "note" in result


# ---------------------------------------------------------------------------
# check_liquidity
# ---------------------------------------------------------------------------

class TestCheckLiquidity:

    def test_liquid_name_passes(self):
        closes  = [150.0] * 20
        volumes = [100_000.0] * 20  # $15M/day
        result = check_liquidity(closes, volumes)
        assert result["passed"] is True

    def test_illiquid_name_fails(self):
        closes  = [5.0] * 20
        volumes = [10_000.0] * 20   # $50K/day — far below $5M
        result = check_liquidity(closes, volumes)
        assert result["passed"] is False

    def test_insufficient_bars_passes_by_default(self):
        result = check_liquidity([100.0] * 3, [1_000.0] * 3)
        assert result["passed"] is True
        assert "note" in result


# ---------------------------------------------------------------------------
# check_relative_strength
# ---------------------------------------------------------------------------

class TestCheckRelativeStrength:

    def test_outperforming_spy_passes(self):
        # Ticker up 20%, SPY up 10%
        ticker_closes = [100.0 + i * 0.32 for i in range(65)]
        spy_closes    = [100.0 + i * 0.16 for i in range(65)]
        result = check_relative_strength(ticker_closes, spy_closes)
        assert result["passed"] is True
        assert result["rs_spread_pct"] > 0

    def test_underperforming_spy_fails(self):
        # Ticker flat, SPY up
        ticker_closes = [100.0] * 65
        spy_closes    = [100.0 + i * 0.15 for i in range(65)]
        result = check_relative_strength(ticker_closes, spy_closes)
        assert result["passed"] is False

    def test_insufficient_data_passes_by_default(self):
        result = check_relative_strength([100.0] * 10, [100.0] * 10)
        assert result["passed"] is True
        assert "note" in result

    def test_spy_closes_none_handled_in_gate(self):
        """evaluate_trade_quality with spy_closes=None passes RS check by default."""
        closes = _make_closes(80)
        highs, lows = _make_hvl(closes, 0.3)
        volumes = _make_volumes(80)
        result = evaluate_trade_quality("bullish", closes, highs, lows, volumes,
                                       spy_closes=None)
        # RS check should show "note" and passed=True
        rs = result["checks"]["relative_strength"]
        assert rs.get("passed", True) is True


# ---------------------------------------------------------------------------
# check_trend_alignment
# ---------------------------------------------------------------------------

class TestCheckTrendAlignment:

    def test_uptrend_passes(self):
        # Rising prices well above MA
        closes = [100.0 + i * 0.5 for i in range(60)]
        result = check_trend_alignment(closes)
        assert result["passed"] is True
        assert result["price_above_ma"] is True
        assert result["ma_slope_positive"] is True

    def test_price_below_ma_declining_fails(self):
        # Declining prices, below MA
        closes = [200.0 - i * 0.5 for i in range(60)]
        result = check_trend_alignment(closes)
        assert result["passed"] is False

    def test_insufficient_bars_passes_by_default(self):
        result = check_trend_alignment([100.0] * 30)
        assert result["passed"] is True
        assert "note" in result


# ---------------------------------------------------------------------------
# evaluate_trade_quality (composite gate)
# ---------------------------------------------------------------------------

class TestEvaluateTradeQuality:

    def _ideal_bullish_data(self):
        n = 80
        closes  = [100.0 + i * 0.3 for i in range(n)]
        highs   = [c + 0.2 for c in closes]
        lows    = [c - 0.2 for c in closes]
        # Contracting volume: higher in first half, lower in recent 5 bars
        volumes = [1_500_000.0] * (n - 5) + [800_000.0] * 5
        spy     = [100.0 + i * 0.1 for i in range(n)]
        return closes, highs, lows, volumes, spy

    def test_high_quality_bullish_trade_allowed(self):
        closes, highs, lows, volumes, spy = self._ideal_bullish_data()
        result = evaluate_trade_quality("bullish", closes, highs, lows, volumes, spy)
        assert result["trade_allowed"] is True
        assert result["failed_checks"] == []
        assert result["veto_reason"] is None

    def test_bearish_signal_always_allowed(self):
        closes, highs, lows, volumes, spy = self._ideal_bullish_data()
        result = evaluate_trade_quality("bearish", closes, highs, lows, volumes, spy)
        assert result["trade_allowed"] is True
        assert result["checks"] == {}

    def test_neutral_signal_always_allowed(self):
        closes, highs, lows, volumes, spy = self._ideal_bullish_data()
        result = evaluate_trade_quality("neutral", closes, highs, lows, volumes, spy)
        assert result["trade_allowed"] is True

    def test_illiquid_stock_vetoed(self):
        n = 80
        closes  = [5.0] * n          # $5 stock
        highs   = [5.1] * n
        lows    = [4.9] * n
        volumes = [10_000.0] * n     # $50K/day
        result = evaluate_trade_quality("bullish", closes, highs, lows, volumes)
        assert "liquidity" in result["failed_checks"]
        assert result["trade_allowed"] is False
        assert result["veto_reason"] is not None

    def test_failed_checks_listed(self):
        n = 80
        closes  = [5.0] * n
        highs   = [5.5] * n          # 10% range — wide base
        lows    = [4.5] * n
        volumes = [10_000.0] * n     # $50K/day — illiquid
        result = evaluate_trade_quality("bullish", closes, highs, lows, volumes)
        # Multiple checks should fail
        assert len(result["failed_checks"]) >= 2

    def test_result_has_all_expected_check_keys(self):
        closes, highs, lows, volumes, spy = self._ideal_bullish_data()
        result = evaluate_trade_quality("bullish", closes, highs, lows, volumes, spy)
        expected_keys = {
            "tightness", "volume_contraction", "liquidity",
            "relative_strength", "trend_alignment",
        }
        assert expected_keys == set(result["checks"].keys())
