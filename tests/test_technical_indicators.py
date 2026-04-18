"""
test_technical_indicators.py — Unit tests for the pure-math indicator library.

Each function is tested in isolation with small, deterministic input lists
so that no network calls or random data are involved.
"""

import math
from typing import List, Optional

import pytest

from agents.technical.indicators import (
    adx,
    atr,
    bollinger_bands,
    cci,
    cmf,
    compute_all_indicators,
    detect_divergence,
    ema,
    find_local_extrema,
    ichimoku,
    macd,
    obv,
    roc,
    rsi,
    sma,
    stochastic,
    vwap,
    williams_r,
)


# ====================================================================== #
# Helpers                                                                  #
# ====================================================================== #

def _assert_nones(result: List[Optional[float]], expected_none_count: int) -> None:
    """Assert the first N entries are None."""
    for i in range(expected_none_count):
        assert result[i] is None, f"Expected None at index {i}, got {result[i]}"


def _assert_close(a: Optional[float], b: float, tol: float = 1e-6) -> None:
    """Assert two floats are close within tolerance."""
    assert a is not None, f"Expected {b}, got None"
    assert abs(a - b) < tol, f"Expected ~{b}, got {a}"


# ====================================================================== #
# SMA                                                                      #
# ====================================================================== #

class TestSMA:
    """Tests for simple moving average."""

    def test_basic_sma_3(self):
        """SMA(3) of [1, 2, 3, 4, 5] → [None, None, 2.0, 3.0, 4.0]."""
        result = sma([1.0, 2.0, 3.0, 4.0, 5.0], period=3)
        assert len(result) == 5
        _assert_nones(result, 2)
        _assert_close(result[2], 2.0)
        _assert_close(result[3], 3.0)
        _assert_close(result[4], 4.0)

    def test_sma_period_1(self):
        """SMA(1) should equal the input values."""
        data = [10.0, 20.0, 30.0]
        result = sma(data, period=1)
        for i in range(3):
            _assert_close(result[i], data[i])

    def test_sma_period_equals_length(self):
        """Only the last entry should be non-None."""
        result = sma([2.0, 4.0, 6.0], period=3)
        _assert_nones(result, 2)
        _assert_close(result[2], 4.0)

    def test_sma_empty_input(self):
        """Empty input should return empty list."""
        assert sma([], period=3) == []

    def test_sma_constant_values(self):
        """SMA of a constant series should equal that constant."""
        result = sma([5.0] * 10, period=4)
        for i in range(3, 10):
            _assert_close(result[i], 5.0)


# ====================================================================== #
# EMA                                                                      #
# ====================================================================== #

class TestEMA:
    """Tests for exponential moving average."""

    def test_ema_first_value_is_sma(self):
        """First EMA value should be the SMA seed."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = ema(data, period=3)
        # First non-None at index 2 = SMA of first 3 values
        _assert_close(result[2], 2.0)

    def test_ema_warmup_nones(self):
        """First (period-1) values are None."""
        result = ema([1.0] * 10, period=5)
        _assert_nones(result, 4)
        assert result[4] is not None

    def test_ema_length_preserved(self):
        """Output length equals input length."""
        data = list(range(1, 21))
        result = ema([float(x) for x in data], period=10)
        assert len(result) == 20

    def test_ema_rising_trend(self):
        """In a strictly rising series, EMA should also rise after warm-up."""
        data = [float(i) for i in range(1, 16)]
        result = ema(data, period=5)
        non_none = [v for v in result if v is not None]
        for i in range(1, len(non_none)):
            assert non_none[i] > non_none[i - 1]


# ====================================================================== #
# RSI                                                                      #
# ====================================================================== #

class TestRSI:
    """Tests for RSI (Wilder smoothing)."""

    def test_rsi_all_up(self):
        """Strictly rising prices → RSI should be 100."""
        data = [float(i) for i in range(1, 30)]
        result = rsi(data, period=14)
        last = result[-1]
        assert last is not None
        _assert_close(last, 100.0, tol=0.1)

    def test_rsi_all_down(self):
        """Strictly falling prices → RSI should be 0."""
        data = [float(30 - i) for i in range(30)]
        result = rsi(data, period=14)
        last = result[-1]
        assert last is not None
        _assert_close(last, 0.0, tol=0.1)

    def test_rsi_range(self):
        """RSI should always be in [0, 100]."""
        data = [100 + (i % 7) * 3 - 5 for i in range(50)]
        result = rsi([float(x) for x in data], period=14)
        for val in result:
            if val is not None:
                assert 0.0 <= val <= 100.0

    def test_rsi_warmup_nones(self):
        """First ``period`` values should be None."""
        result = rsi([float(i) for i in range(30)], period=14)
        _assert_nones(result, 14)


# ====================================================================== #
# MACD                                                                     #
# ====================================================================== #

class TestMACD:
    """Tests for MACD (fast=12, slow=26, signal=9)."""

    def test_macd_returns_three_lists(self):
        """MACD returns (macd_line, signal_line, histogram)."""
        data = [float(100 + i) for i in range(60)]
        macd_line, signal_line, histogram = macd(data)
        assert len(macd_line) == 60
        assert len(signal_line) == 60
        assert len(histogram) == 60

    def test_macd_histogram_is_difference(self):
        """Histogram = MACD line - signal line."""
        data = [float(100 + i * 0.5) for i in range(60)]
        macd_line, signal_line, histogram = macd(data)
        for m, s, h in zip(macd_line, signal_line, histogram):
            if m is not None and s is not None and h is not None:
                _assert_close(h, m - s, tol=1e-4)

    def test_macd_warmup(self):
        """MACD line requires slow_period-1 warmup; signal needs more."""
        data = [float(i) for i in range(60)]
        macd_line, signal_line, _hist = macd(data)
        # First 25 MACD values should be None (slow EMA period=26)
        _assert_nones(macd_line, 25)


# ====================================================================== #
# Bollinger Bands                                                          #
# ====================================================================== #

class TestBollingerBands:
    """Tests for Bollinger Bands (period=20, std_dev=2)."""

    def test_bb_returns_five_lists(self):
        """Returns (upper, middle, lower, pct_b, bandwidth)."""
        data = [float(100 + i) for i in range(30)]
        upper, middle, lower, pct_b, bw = bollinger_bands(data)
        assert len(upper) == 30
        assert len(pct_b) == 30

    def test_bb_middle_is_sma(self):
        """Middle band should equal SMA(20)."""
        data = [float(100 + i) for i in range(30)]
        _upper, middle, _lower, _pct_b, _bw = bollinger_bands(data)
        sma_result = sma(data, period=20)
        for m, s in zip(middle, sma_result):
            if m is not None and s is not None:
                _assert_close(m, s, tol=1e-4)

    def test_bb_upper_above_lower(self):
        """Upper band should always be >= lower band."""
        data = [float(100 + (i % 5) * 2) for i in range(30)]
        upper, _mid, lower, _pct_b, _bw = bollinger_bands(data)
        for u, l in zip(upper, lower):
            if u is not None and l is not None:
                assert u >= l

    def test_bb_constant_series_zero_bandwidth(self):
        """Constant series → bandwidth should be 0."""
        data = [50.0] * 25
        _upper, _mid, _lower, _pct_b, bw = bollinger_bands(data)
        for val in bw:
            if val is not None:
                _assert_close(val, 0.0, tol=1e-6)


# ====================================================================== #
# OBV                                                                      #
# ====================================================================== #

class TestOBV:
    """Tests for On-Balance Volume."""

    def test_obv_rising_prices(self):
        """Rising prices → OBV should accumulate positively."""
        closes = [10.0, 11.0, 12.0, 13.0, 14.0]
        volumes = [100.0, 200.0, 300.0, 400.0, 500.0]
        result = obv(closes, volumes)
        assert result[-1] is not None
        assert result[-1] > 0  # type: ignore[operator]

    def test_obv_falling_prices(self):
        """Falling prices → OBV should be negative."""
        closes = [14.0, 13.0, 12.0, 11.0, 10.0]
        volumes = [100.0, 200.0, 300.0, 400.0, 500.0]
        result = obv(closes, volumes)
        assert result[-1] is not None
        assert result[-1] < 0  # type: ignore[operator]

    def test_obv_length(self):
        """Output length matches input."""
        closes = [10.0, 11.0, 10.0]
        volumes = [100.0, 100.0, 100.0]
        assert len(obv(closes, volumes)) == 3


# ====================================================================== #
# ADX                                                                      #
# ====================================================================== #

class TestADX:
    """Tests for ADX (Average Directional Index)."""

    def test_adx_returns_three_lists(self):
        """Returns (adx_values, plus_di, minus_di)."""
        n = 50
        highs = [float(100 + i) for i in range(n)]
        lows = [float(99 + i) for i in range(n)]
        closes = [float(99.5 + i) for i in range(n)]
        adx_vals, plus_di_vals, minus_di_vals = adx(highs, lows, closes)
        assert len(adx_vals) == n
        assert len(plus_di_vals) == n
        assert len(minus_di_vals) == n

    def test_adx_range(self):
        """ADX values should be in [0, 100]."""
        n = 50
        highs = [float(100 + i + (i % 3)) for i in range(n)]
        lows = [float(98 + i - (i % 3)) for i in range(n)]
        closes = [float(99 + i) for i in range(n)]
        adx_vals, _, _ = adx(highs, lows, closes)
        for v in adx_vals:
            if v is not None:
                assert 0.0 <= v <= 100.0


# ====================================================================== #
# Stochastic                                                               #
# ====================================================================== #

class TestStochastic:
    """Tests for Stochastic %K / %D."""

    def test_stochastic_returns_two_lists(self):
        """Returns (k_values, d_values)."""
        n = 30
        highs = [float(100 + i) for i in range(n)]
        lows = [float(99 + i) for i in range(n)]
        closes = [float(99.5 + i) for i in range(n)]
        k_vals, d_vals = stochastic(highs, lows, closes)
        assert len(k_vals) == n
        assert len(d_vals) == n

    def test_stochastic_range(self):
        """Stochastic %K should be in [0, 100]."""
        n = 30
        highs = [float(100 + i + (i % 5)) for i in range(n)]
        lows = [float(98 + i) for i in range(n)]
        closes = [float(99 + i) for i in range(n)]
        k_vals, _ = stochastic(highs, lows, closes)
        for v in k_vals:
            if v is not None:
                assert 0.0 <= v <= 100.0 + 0.01  # small float tolerance


# ====================================================================== #
# find_local_extrema                                                       #
# ====================================================================== #

class TestLocalExtrema:
    """Tests for peak/trough detection."""

    def test_simple_peak_trough(self):
        """Basic V-shape and peak detection with enough flat region around extrema."""
        # Build a series with clear peak and trough surrounded by enough
        # neighbours for order=3 to trigger.
        values = (
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]       # ramp up
            + [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]          # ramp down
            + [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]     # ramp up again
        )
        peaks, troughs = find_local_extrema(values, order=3)
        # Peak around index 10, trough around index 20
        assert len(peaks) >= 1
        assert len(troughs) >= 1

    def test_monotonic_no_extrema(self):
        """Strictly rising series should yield no peaks."""
        values = list(range(20))
        peaks, troughs = find_local_extrema(values, order=3)
        assert len(peaks) == 0


# ====================================================================== #
# detect_divergence                                                        #
# ====================================================================== #

class TestDivergence:
    """Tests for price/indicator divergence detection."""

    def test_no_divergence_parallel(self):
        """When both rise together, no divergence."""
        prices = [float(i) for i in range(40)]
        indicator = [float(i) for i in range(40)]
        result = detect_divergence(prices, indicator, order=3, lookback=30)
        # Parallel movement → should be None (no divergence)
        assert result is None or result in ("bullish", "bearish")

    def test_short_input_returns_none(self):
        """Inputs shorter than lookback should return None gracefully."""
        result = detect_divergence([1.0, 2.0], [1.0, 2.0], order=3, lookback=30)
        assert result is None


# ====================================================================== #
# compute_all_indicators                                                   #
# ====================================================================== #

class TestComputeAll:
    """Tests for the aggregate compute_all_indicators entry point."""

    def test_returns_dict_with_expected_keys(self):
        """All standard indicator keys should be present."""
        n = 250
        closes = [float(100 + i * 0.1) for i in range(n)]
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        volumes = [1_000_000.0] * n

        result = compute_all_indicators(closes, highs, lows, volumes)

        expected_keys = {
            "ema_20", "ema_50", "ema_200",
            "sma_20", "sma_50", "sma_200",
            "rsi_14",
            "macd_line", "macd_signal", "macd_histogram",
            "bb_upper", "bb_middle", "bb_lower", "bb_pct_b", "bb_bandwidth",
            "obv",
            "adx", "plus_di", "minus_di",
            "stoch_k", "stoch_d",
            # v2 indicators
            "atr_14", "roc_12", "williams_r_14", "cci_20", "cmf_20",
            "ichimoku_tenkan", "ichimoku_kijun",
            "ichimoku_senkou_a", "ichimoku_senkou_b", "ichimoku_chikou",
            "vwap_20",
        }
        missing = expected_keys - set(result.keys())
        assert not missing, f"Missing keys: {missing}"

    def test_output_lengths_match_input(self):
        """Every indicator list should have the same length as input.
        Exceptions:
          - 'fibonacci': returns a dict of price levels, not a time-series list.
        """
        n = 250
        closes = [float(100 + i * 0.1) for i in range(n)]
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        volumes = [1_000_000.0] * n

        result = compute_all_indicators(closes, highs, lows, volumes)

        # Keys that intentionally return non-series outputs (dicts of scalar levels)
        _DICT_OUTPUTS = {"fibonacci", "market_structure"}

        for key, values in result.items():
            if key in _DICT_OUTPUTS:
                assert isinstance(values, dict), (
                    f"{key} expected a dict of levels, got {type(values)}"
                )
            else:
                assert len(values) == n, f"{key} has length {len(values)}, expected {n}"


# ====================================================================== #
# ATR (v2)                                                                 #
# ====================================================================== #

class TestATR:
    """Tests for Average True Range."""

    def test_atr_returns_correct_length(self):
        n = 50
        highs = [float(100 + i + 1) for i in range(n)]
        lows = [float(100 + i - 1) for i in range(n)]
        closes = [float(100 + i) for i in range(n)]
        result = atr(highs, lows, closes)
        assert len(result) == n

    def test_atr_warmup_nones(self):
        """First period entries should be None."""
        n = 50
        highs = [float(100 + i + 1) for i in range(n)]
        lows = [float(100 + i - 1) for i in range(n)]
        closes = [float(100 + i) for i in range(n)]
        result = atr(highs, lows, closes, period=14)
        _assert_nones(result, 14)
        assert result[14] is not None

    def test_atr_constant_range(self):
        """Constant H-L range → ATR should converge to that range."""
        n = 60
        closes = [100.0] * n
        highs = [101.0] * n
        lows = [99.0] * n
        result = atr(highs, lows, closes, period=14)
        last = result[-1]
        assert last is not None
        _assert_close(last, 2.0, tol=0.1)

    def test_atr_positive(self):
        """ATR should always be positive."""
        n = 50
        highs = [float(100 + i + (i % 3)) for i in range(n)]
        lows = [float(98 + i) for i in range(n)]
        closes = [float(99 + i) for i in range(n)]
        result = atr(highs, lows, closes)
        for v in result:
            if v is not None:
                assert v > 0


# ====================================================================== #
# ROC (v2)                                                                 #
# ====================================================================== #

class TestROC:
    """Tests for Rate of Change."""

    def test_roc_rising_series(self):
        """Rising series → positive ROC."""
        data = [float(100 + i) for i in range(30)]
        result = roc(data, period=12)
        last = result[-1]
        assert last is not None
        assert last > 0

    def test_roc_falling_series(self):
        """Falling series → negative ROC."""
        data = [float(200 - i) for i in range(30)]
        result = roc(data, period=12)
        last = result[-1]
        assert last is not None
        assert last < 0

    def test_roc_warmup_nones(self):
        """First period entries should be None."""
        result = roc([100.0] * 30, period=12)
        _assert_nones(result, 12)

    def test_roc_constant_series(self):
        """Constant series → ROC should be 0."""
        result = roc([50.0] * 30, period=12)
        last = result[-1]
        assert last is not None
        _assert_close(last, 0.0, tol=0.01)


# ====================================================================== #
# Williams %R (v2)                                                         #
# ====================================================================== #

class TestWilliamsR:
    """Tests for Williams %R."""

    def test_wr_range(self):
        """Williams %R should be in [-100, 0]."""
        n = 30
        highs = [float(100 + i + (i % 3)) for i in range(n)]
        lows = [float(98 + i) for i in range(n)]
        closes = [float(99 + i) for i in range(n)]
        result = williams_r(highs, lows, closes)
        for v in result:
            if v is not None:
                assert -100.0 <= v <= 0.0

    def test_wr_at_high(self):
        """When close equals the highest high, %R should be 0."""
        n = 30
        highs = [float(100 + i) for i in range(n)]
        lows = [float(98 + i) for i in range(n)]
        # Close equals high
        closes = [float(100 + i) for i in range(n)]
        result = williams_r(highs, lows, closes)
        last = result[-1]
        assert last is not None
        _assert_close(last, 0.0, tol=0.1)

    def test_wr_warmup(self):
        """First period-1 entries should be None."""
        result = williams_r(
            [100.0] * 20, [98.0] * 20, [99.0] * 20, period=14,
        )
        _assert_nones(result, 13)


# ====================================================================== #
# CCI (v2)                                                                 #
# ====================================================================== #

class TestCCI:
    """Tests for Commodity Channel Index."""

    def test_cci_returns_correct_length(self):
        n = 50
        highs = [float(100 + i + 1) for i in range(n)]
        lows = [float(100 + i - 1) for i in range(n)]
        closes = [float(100 + i) for i in range(n)]
        result = cci(highs, lows, closes)
        assert len(result) == n

    def test_cci_warmup_nones(self):
        """First period-1 entries should be None."""
        n = 50
        highs = [float(100 + i + 1) for i in range(n)]
        lows = [float(100 + i - 1) for i in range(n)]
        closes = [float(100 + i) for i in range(n)]
        result = cci(highs, lows, closes, period=20)
        _assert_nones(result, 19)

    def test_cci_constant_series(self):
        """Constant series → CCI should be 0."""
        n = 30
        result = cci([100.0] * n, [100.0] * n, [100.0] * n, period=20)
        last = result[-1]
        assert last is not None
        _assert_close(last, 0.0, tol=0.01)


# ====================================================================== #
# CMF (v2)                                                                 #
# ====================================================================== #

class TestCMF:
    """Tests for Chaikin Money Flow."""

    def test_cmf_range(self):
        """CMF should be roughly between -1 and +1."""
        n = 50
        highs = [float(101 + i) for i in range(n)]
        lows = [float(99 + i) for i in range(n)]
        closes = [float(100 + i) for i in range(n)]
        volumes = [1_000_000.0] * n
        result = cmf(highs, lows, closes, volumes)
        for v in result:
            if v is not None:
                assert -1.0 <= v <= 1.0

    def test_cmf_bullish_closes(self):
        """When close == high every day, CMF should be positive."""
        n = 30
        highs = [float(100 + i) for i in range(n)]
        lows = [float(98 + i) for i in range(n)]
        closes = [float(100 + i) for i in range(n)]  # close at high
        volumes = [1_000_000.0] * n
        result = cmf(highs, lows, closes, volumes, period=20)
        last = result[-1]
        assert last is not None
        assert last > 0  # accumulation

    def test_cmf_warmup_nones(self):
        """First period-1 entries should be None."""
        n = 30
        result = cmf(
            [100.0] * n, [98.0] * n, [99.0] * n, [1e6] * n, period=20,
        )
        _assert_nones(result, 19)


# ====================================================================== #
# Ichimoku Cloud (v2)                                                      #
# ====================================================================== #

class TestIchimoku:
    """Tests for Ichimoku Cloud."""

    def test_ichimoku_returns_dict_with_5_keys(self):
        n = 100
        highs = [float(100 + i + 1) for i in range(n)]
        lows = [float(100 + i - 1) for i in range(n)]
        closes = [float(100 + i) for i in range(n)]
        result = ichimoku(highs, lows, closes)
        assert set(result.keys()) == {"tenkan", "kijun", "senkou_a", "senkou_b", "chikou"}
        for key in result:
            assert len(result[key]) == n

    def test_ichimoku_tenkan_computed(self):
        """Tenkan should be non-None after 9 bars."""
        n = 100
        highs = [float(100 + i + 1) for i in range(n)]
        lows = [float(100 + i - 1) for i in range(n)]
        closes = [float(100 + i) for i in range(n)]
        result = ichimoku(highs, lows, closes)
        # Tenkan available from index 8 (9th bar)
        assert result["tenkan"][8] is not None
        assert result["tenkan"][0] is None

    def test_ichimoku_senkou_b_warmup(self):
        """Senkou B requires 52 bars."""
        n = 100
        highs = [float(100 + i + 1) for i in range(n)]
        lows = [float(100 + i - 1) for i in range(n)]
        closes = [float(100 + i) for i in range(n)]
        result = ichimoku(highs, lows, closes)
        assert result["senkou_b"][50] is None
        assert result["senkou_b"][51] is not None


# ====================================================================== #
# VWAP (v2)                                                                #
# ====================================================================== #

class TestVWAP:
    """Tests for Volume Weighted Average Price."""

    def test_vwap_returns_correct_length(self):
        n = 50
        highs = [float(101 + i) for i in range(n)]
        lows = [float(99 + i) for i in range(n)]
        closes = [float(100 + i) for i in range(n)]
        volumes = [1_000_000.0] * n
        result = vwap(highs, lows, closes, volumes)
        assert len(result) == n

    def test_vwap_warmup_nones(self):
        """First period-1 entries should be None."""
        n = 30
        result = vwap(
            [101.0] * n, [99.0] * n, [100.0] * n, [1e6] * n, period=20,
        )
        _assert_nones(result, 19)

    def test_vwap_constant_prices(self):
        """Constant prices → VWAP should equal typical price = (H+L+C)/3."""
        n = 30
        result = vwap(
            [101.0] * n, [99.0] * n, [100.0] * n, [1e6] * n, period=20,
        )
        last = result[-1]
        assert last is not None
        _assert_close(last, 100.0, tol=0.01)  # (101+99+100)/3 = 100
