"""
test_technical_rules.py — Tests for the technical rules engine.

Uses a synthetic OHLCV dataset so no network calls are needed.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional

import pytest

from agents.technical.indicators import compute_all_indicators
from agents.technical.models import (
    OHLCVBar,
    PatternSignal,
    RawTechnicalSnapshot,
    TechnicalRequest,
)
from agents.technical.rules import (
    build_composite_score,
    evaluate_adx_stochastic,
    evaluate_bollinger,
    evaluate_ema_trend,
    evaluate_ichimoku,
    evaluate_macd,
    evaluate_momentum,
    evaluate_patterns,
    evaluate_rsi,
    evaluate_snapshot,
    evaluate_volume,
)


# ====================================================================== #
# Fixtures                                                                 #
# ====================================================================== #

def _rising_bars(n: int = 250, base: float = 100.0) -> List[OHLCVBar]:
    """Generate ``n`` bars with a gentle uptrend."""
    bars = []
    start = date(2024, 1, 2)
    for i in range(n):
        close = base + i * 0.5
        bars.append(
            OHLCVBar(
                bar_date=start + timedelta(days=i),
                open=close - 0.3,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=1_000_000.0 + i * 1000,
            )
        )
    return bars


def _flat_bars(n: int = 250, base: float = 100.0) -> List[OHLCVBar]:
    """Generate ``n`` bars that oscillate around *base*."""
    bars = []
    start = date(2024, 1, 2)
    for i in range(n):
        delta = ((i % 5) - 2) * 0.3
        close = base + delta
        bars.append(
            OHLCVBar(
                bar_date=start + timedelta(days=i),
                open=close - 0.1,
                high=close + 0.5,
                low=close - 0.5,
                close=close,
                volume=1_000_000.0,
            )
        )
    return bars


def _make_snapshot(bars: List[OHLCVBar]) -> RawTechnicalSnapshot:
    """Wrap bars into a RawTechnicalSnapshot."""
    return RawTechnicalSnapshot(
        request=TechnicalRequest(ticker="TEST", as_of_date=bars[-1].bar_date),
        company_name="Test Inc.",
        sector="Technology",
        industry="Software",
        bars=bars,
        as_of_price=bars[-1].close,
        as_of_price_date=bars[-1].bar_date,
        warnings=[],
    )


def _indicators_from_bars(bars: List[OHLCVBar]) -> Dict[str, List[Optional[float]]]:
    """Compute all indicators from raw bars."""
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]
    return compute_all_indicators(closes, highs, lows, volumes)


def _sample_pattern() -> PatternSignal:
    """Return a single bullish pattern for testing."""
    return PatternSignal(
        pattern_name="Bull Flag",
        direction="bullish",
        confidence=0.72,
        start_date=date(2024, 7, 1),
        end_date=date(2024, 8, 15),
        breakout_confirmed=True,
        volume_confirmation=True,
        description="Bull flag with confirmed breakout.",
    )


# ====================================================================== #
# Individual framework tests                                               #
# ====================================================================== #

class TestEMATrend:
    """Tests for evaluate_ema_trend."""

    def test_rising_trend_above_50(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_ema_trend(closes, indicators)
        assert result["applicable"] is True
        assert result["score_pct"] >= 50  # uptrend → should score well

    def test_flat_market(self):
        bars = _flat_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_ema_trend(closes, indicators)
        assert result["applicable"] is True
        assert result["score_pct"] is not None


class TestMACD:
    """Tests for evaluate_macd."""

    def test_applicable_with_enough_data(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_macd(closes, indicators)
        assert result["applicable"] is True

    def test_score_bounded(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_macd(closes, indicators)
        assert 0 <= result["score_pct"] <= 100


class TestRSI:
    """Tests for evaluate_rsi."""

    def test_rising_rsi_above_50(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_rsi(closes, indicators)
        assert result["applicable"] is True
        # In an uptrend RSI should be above 50 → score should reflect that
        assert result["score_pct"] >= 40

    def test_score_bounded(self):
        bars = _flat_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_rsi(closes, indicators)
        assert 0 <= result["score_pct"] <= 100


class TestBollinger:
    """Tests for evaluate_bollinger."""

    def test_applicable(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_bollinger(closes, indicators)
        assert result["applicable"] is True

    def test_score_bounded(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_bollinger(closes, indicators)
        assert 0 <= result["score_pct"] <= 100


class TestVolume:
    """Tests for evaluate_volume (OBV)."""

    def test_rising_volume_in_uptrend(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_volume(closes, indicators)
        assert result["applicable"] is True


class TestADXStochastic:
    """Tests for evaluate_adx_stochastic."""

    def test_applicable(self):
        bars = _rising_bars()
        indicators = _indicators_from_bars(bars)
        result = evaluate_adx_stochastic(indicators)
        assert result["applicable"] is True


class TestPatterns:
    """Tests for evaluate_patterns."""

    def test_no_patterns(self):
        result = evaluate_patterns([])
        assert result["applicable"] is True
        assert result["score_pct"] == 50  # neutral baseline

    def test_bullish_pattern_raises_score(self):
        patterns = [_sample_pattern()]
        result = evaluate_patterns(patterns)
        assert result["score_pct"] > 50  # bullish should push above neutral


# ====================================================================== #
# Ichimoku framework                                                       #
# ====================================================================== #

class TestIchimokuFramework:
    """Tests for evaluate_ichimoku."""

    def test_rising_bars_applicable(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_ichimoku(closes, indicators)
        assert result["applicable"] is True
        assert isinstance(result["score_pct"], (int, float))

    def test_score_bounded(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_ichimoku(closes, indicators)
        assert 0 <= result["score_pct"] <= 100

    def test_insufficient_data(self):
        """With only 10 bars, Ichimoku should be inapplicable (needs 52+)."""
        bars = _rising_bars(n=10)
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_ichimoku(closes, indicators)
        assert result["applicable"] is False

    def test_details_keys(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_ichimoku(closes, indicators)
        if result["applicable"]:
            assert "tenkan" in result["details"]
            assert "price_vs_cloud" in result["details"]


# ====================================================================== #
# Momentum framework                                                       #
# ====================================================================== #

class TestMomentumFramework:
    """Tests for evaluate_momentum."""

    def test_rising_bars_applicable(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_momentum(closes, indicators)
        assert result["applicable"] is True
        assert isinstance(result["score_pct"], (int, float))

    def test_score_bounded(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_momentum(closes, indicators)
        assert 0 <= result["score_pct"] <= 100

    def test_flat_market_near_neutral(self):
        bars = _flat_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_momentum(closes, indicators)
        if result["applicable"]:
            # Flat market shouldn't produce extreme momentum scores
            assert 20 <= result["score_pct"] <= 80

    def test_details_keys(self):
        bars = _rising_bars()
        closes = [b.close for b in bars]
        indicators = _indicators_from_bars(bars)
        result = evaluate_momentum(closes, indicators)
        if result["applicable"]:
            assert "roc_12" in result["details"]
            assert "williams_r_14" in result["details"]
            assert "cci_20" in result["details"]


# ====================================================================== #
# Composite score                                                          #
# ====================================================================== #

class TestCompositeScore:
    """Tests for build_composite_score."""

    def test_all_100_gives_strong(self):
        frameworks = {
            "ema_trend": {"applicable": True, "score_pct": 100},
            "macd_system": {"applicable": True, "score_pct": 100},
            "rsi_regime": {"applicable": True, "score_pct": 100},
            "bollinger": {"applicable": True, "score_pct": 100},
            "volume_obv": {"applicable": True, "score_pct": 100},
            "adx_stochastic": {"applicable": True, "score_pct": 100},
            "pattern_recognition": {"applicable": True, "score_pct": 100},
            "ichimoku": {"applicable": True, "score_pct": 100},
            "momentum": {"applicable": True, "score_pct": 100},
        }
        result = build_composite_score(frameworks, adx_value=50.0)
        assert result["available"] is True
        assert result["score"] == 100.0
        assert result["band"] == "strong"

    def test_all_0_gives_weak(self):
        frameworks = {
            "ema_trend": {"applicable": True, "score_pct": 0},
            "macd_system": {"applicable": True, "score_pct": 0},
            "rsi_regime": {"applicable": True, "score_pct": 0},
            "bollinger": {"applicable": True, "score_pct": 0},
            "volume_obv": {"applicable": True, "score_pct": 0},
            "adx_stochastic": {"applicable": True, "score_pct": 0},
            "pattern_recognition": {"applicable": True, "score_pct": 0},
            "ichimoku": {"applicable": True, "score_pct": 0},
            "momentum": {"applicable": True, "score_pct": 0},
        }
        result = build_composite_score(frameworks, adx_value=50.0)
        assert result["available"] is True
        assert result["score"] == 0.0
        assert result["band"] == "weak"

    def test_band_thresholds(self):
        """Spot-check the band thresholds."""
        fw = {k: {"applicable": True, "score_pct": 0} for k in [
            "ema_trend", "macd_system", "rsi_regime", "bollinger",
            "volume_obv", "adx_stochastic", "pattern_recognition",
            "ichimoku", "momentum",
        ]}

        # Score 75 → strong (≥75)
        for k in fw:
            fw[k]["score_pct"] = 75
        result = build_composite_score(fw, adx_value=50.0)
        assert result["band"] == "strong"

        # Score 65 → good (≥60 and <75)
        for k in fw:
            fw[k]["score_pct"] = 65
        result = build_composite_score(fw, adx_value=50.0)
        assert result["band"] == "good"

    def test_confidence_levels(self):
        """ADX drives confidence: ≥40 = high, ≥20 = medium, <20 = low."""
        fw = {k: {"applicable": True, "score_pct": 70} for k in [
            "ema_trend", "macd_system", "rsi_regime", "bollinger",
            "volume_obv", "adx_stochastic", "pattern_recognition",
            "ichimoku", "momentum",
        ]}
        assert build_composite_score(fw, adx_value=45.0)["confidence"] == "high"
        assert build_composite_score(fw, adx_value=25.0)["confidence"] == "medium"
        assert build_composite_score(fw, adx_value=15.0)["confidence"] == "low"


# ====================================================================== #
# Full evaluate_snapshot                                                   #
# ====================================================================== #

class TestEvaluateSnapshot:
    """Integration test using evaluate_snapshot with synthetic data."""

    def test_returns_expected_keys(self):
        bars = _rising_bars()
        snapshot = _make_snapshot(bars)
        indicators = _indicators_from_bars(bars)
        patterns = [_sample_pattern()]

        result = evaluate_snapshot(snapshot, indicators, patterns)

        expected_keys = {
            "request", "company", "as_of_price", "frameworks",
            "experimental_score", "patterns", "key_indicators", "warnings",
        }
        assert expected_keys <= set(result.keys())

    def test_all_frameworks_present(self):
        bars = _rising_bars()
        snapshot = _make_snapshot(bars)
        indicators = _indicators_from_bars(bars)

        result = evaluate_snapshot(snapshot, indicators, [])

        expected_frameworks = {
            "ema_trend", "macd_system", "rsi_regime", "bollinger",
            "volume_obv", "adx_stochastic", "pattern_recognition",
            "ichimoku", "momentum",
        }
        assert expected_frameworks == set(result["frameworks"].keys())

    def test_score_bounded(self):
        bars = _rising_bars()
        snapshot = _make_snapshot(bars)
        indicators = _indicators_from_bars(bars)

        result = evaluate_snapshot(snapshot, indicators, [])
        score = result["experimental_score"]
        assert score["available"] is True
        assert 0.0 <= score["score"] <= 100.0
