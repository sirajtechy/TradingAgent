"""
indicators.py — Pure-math technical indicator library.

Every function in this module is **deterministic and side-effect free**.
Inputs are plain Python lists of floats; outputs are lists of the same
length (padded with ``None`` where the indicator has not yet warmed up).

Standard parameter choices follow the original creators and are the
industry-accepted defaults (see inline references):

    EMA / SMA ............. period = 20, 50, 200
    RSI ................... period = 14  (J. Welles Wilder, 1978)
    MACD .................. fast=12, slow=26, signal=9  (Gerald Appel)
    Bollinger Bands ....... period=20, std_dev=2  (John Bollinger)
    OBV ................... cumulative  (Joseph Granville, 1963)
    ADX / DI+/DI- ......... period=14  (Wilder, 1978)
    Stochastic %K / %D .... k_period=14, d_period=3, smooth=3  (George Lane)

None of these functions import anything outside the Python standard library.
They can be unit-tested in complete isolation.
"""

from typing import Any, Dict, List, Optional, Tuple


# ====================================================================== #
#  HELPERS                                                                 #
# ====================================================================== #

def _safe_div(numerator: Optional[float],
              denominator: Optional[float]) -> Optional[float]:
    """Divide *numerator* by *denominator*; return None on division by zero."""
    if numerator is None or denominator is None or denominator == 0.0:
        return None
    return numerator / denominator


# ====================================================================== #
#  MOVING AVERAGES                                                         #
# ====================================================================== #

def sma(values: List[float], period: int) -> List[Optional[float]]:
    """
    Simple Moving Average.

    The first ``period - 1`` entries are None (insufficient data).

    Args:
        values: List of closing prices (oldest-first).
        period: Lookback window size.

    Returns:
        List of same length as *values*.
    """
    n = len(values)
    result: List[Optional[float]] = [None] * n
    if period <= 0 or n < period:
        return result

    # Seed with the first window sum
    window_sum = sum(values[:period])
    result[period - 1] = window_sum / period

    for i in range(period, n):
        window_sum += values[i] - values[i - period]
        result[i] = window_sum / period

    return result


def ema(values: List[float], period: int) -> List[Optional[float]]:
    """
    Exponential Moving Average.

    Seed value is the SMA of the first *period* entries.
    Multiplier = 2 / (period + 1).

    Args:
        values: List of closing prices (oldest-first).
        period: Lookback window size.

    Returns:
        List of same length as *values*.  First ``period - 1`` entries
        are None.
    """
    n = len(values)
    result: List[Optional[float]] = [None] * n
    if period <= 0 or n < period:
        return result

    # Seed: SMA of first *period* values
    seed = sum(values[:period]) / period
    result[period - 1] = seed

    multiplier = 2.0 / (period + 1)
    prev = seed
    for i in range(period, n):
        current = (values[i] - prev) * multiplier + prev
        result[i] = current
        prev = current

    return result


# ====================================================================== #
#  RSI  (Wilder, 1978)                                                     #
# ====================================================================== #

def rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
    """
    Relative Strength Index using Wilder's smoothing method.

    - Values range from 0 to 100.
    - Above 70 is traditionally overbought; below 30 oversold.
    - In an uptrend, RSI typically oscillates between 40–80.
    - In a downtrend, RSI typically oscillates between 20–60.

    Args:
        closes: Daily closing prices (oldest-first).
        period: Lookback period (default 14, per Wilder).

    Returns:
        List of same length as *closes*; first *period* entries are None.
    """
    n = len(closes)
    result: List[Optional[float]] = [None] * n
    if period <= 0 or n < period + 1:
        return result

    # Compute price changes
    deltas = [closes[i] - closes[i - 1] for i in range(1, n)]

    # Seed the first average gain / loss with SMA
    gains = [max(d, 0.0) for d in deltas[:period]]
    losses = [max(-d, 0.0) for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # First RSI value
    if avg_loss == 0.0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    # Roll forward using Wilder's smoothing
    for i in range(period, len(deltas)):
        gain = max(deltas[i], 0.0)
        loss = max(-deltas[i], 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0.0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return result


# ====================================================================== #
#  MACD  (Gerald Appel)                                                    #
# ====================================================================== #

def macd(
    closes: List[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    Moving Average Convergence Divergence.

    Returns a 3-tuple:
        (macd_line, signal_line, histogram)

    - MACD line = EMA(fast) − EMA(slow)
    - Signal line = EMA(signal_period) of the MACD line
    - Histogram = MACD line − signal line

    Each list has the same length as *closes*.

    Args:
        closes: Daily closing prices (oldest-first).
        fast:   Fast EMA period (default 12).
        slow:   Slow EMA period (default 26).
        signal_period: Signal line EMA period (default 9).
    """
    n = len(closes)
    none_list: List[Optional[float]] = [None] * n

    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)

    # MACD line
    macd_line: List[Optional[float]] = [None] * n
    for i in range(n):
        if fast_ema[i] is not None and slow_ema[i] is not None:
            macd_line[i] = fast_ema[i] - slow_ema[i]

    # Signal line = EMA of the MACD line (skip Nones)
    # We need to build a dense sub-list, compute EMA, then map back.
    macd_dense: List[float] = []
    macd_indices: List[int] = []
    for i, v in enumerate(macd_line):
        if v is not None:
            macd_dense.append(v)
            macd_indices.append(i)

    signal_dense = ema(macd_dense, signal_period) if macd_dense else []

    signal_line: List[Optional[float]] = [None] * n
    for j, idx in enumerate(macd_indices):
        signal_line[idx] = signal_dense[j] if j < len(signal_dense) else None

    # Histogram
    histogram: List[Optional[float]] = [None] * n
    for i in range(n):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram[i] = macd_line[i] - signal_line[i]

    return macd_line, signal_line, histogram


# ====================================================================== #
#  BOLLINGER BANDS  (John Bollinger)                                       #
# ====================================================================== #

def bollinger_bands(
    closes: List[float],
    period: int = 20,
    num_std: float = 2.0,
) -> Tuple[
    List[Optional[float]],  # upper
    List[Optional[float]],  # middle (SMA)
    List[Optional[float]],  # lower
    List[Optional[float]],  # %B
    List[Optional[float]],  # bandwidth
]:
    """
    Bollinger Bands with %B and bandwidth.

    Returns a 5-tuple:
        (upper, middle, lower, percent_b, bandwidth)

    - %B = (Close − Lower) / (Upper − Lower)  →  0.0 at lower band,
      1.0 at upper band.
    - Bandwidth = (Upper − Lower) / Middle × 100  →  measures squeeze.

    Args:
        closes: Daily closing prices (oldest-first).
        period: SMA lookback window (default 20).
        num_std: Number of standard deviations (default 2.0).
    """
    n = len(closes)
    upper:     List[Optional[float]] = [None] * n
    middle:    List[Optional[float]] = [None] * n
    lower:     List[Optional[float]] = [None] * n
    percent_b: List[Optional[float]] = [None] * n
    bandwidth: List[Optional[float]] = [None] * n

    mid = sma(closes, period)

    for i in range(period - 1, n):
        mid_val = mid[i]
        if mid_val is None:
            continue

        # Standard deviation of the window
        window = closes[i - period + 1 : i + 1]
        mean = mid_val
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance ** 0.5

        u = mean + num_std * std
        l = mean - num_std * std

        upper[i] = u
        middle[i] = mean
        lower[i] = l

        band_width = u - l
        if band_width > 0:
            percent_b[i] = (closes[i] - l) / band_width
        else:
            percent_b[i] = 0.5  # flat bands edge case

        bandwidth[i] = _safe_div(band_width, mean)
        if bandwidth[i] is not None:
            bandwidth[i] *= 100.0  # express as percentage

    return upper, middle, lower, percent_b, bandwidth


# ====================================================================== #
#  OBV  (Joseph Granville, 1963)                                           #
# ====================================================================== #

def obv(closes: List[float], volumes: List[float]) -> List[Optional[float]]:
    """
    On-Balance Volume — a cumulative volume indicator.

    Rules:
        - If today's close > yesterday's close → add today's volume.
        - If today's close < yesterday's close → subtract today's volume.
        - If unchanged → OBV stays the same.

    Args:
        closes:  Daily closing prices (oldest-first).
        volumes: Corresponding daily volumes.

    Returns:
        List of same length.  ``result[0]`` = 0 (starting reference).
    """
    n = len(closes)
    if n == 0:
        return []

    result: List[Optional[float]] = [0.0]
    for i in range(1, n):
        prev_obv = result[i - 1] or 0.0
        if closes[i] > closes[i - 1]:
            result.append(prev_obv + volumes[i])
        elif closes[i] < closes[i - 1]:
            result.append(prev_obv - volumes[i])
        else:
            result.append(prev_obv)

    return result


# ====================================================================== #
#  ADX / DI+ / DI-  (Wilder, 1978)                                        #
# ====================================================================== #

def adx(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    Average Directional Index with +DI and −DI.

    - ADX > 25 (some use 20) indicates a trending market.
    - ADX > 40 is a strong trend.
    - ADX < 20 means the market is range-bound; trend signals are unreliable.

    Returns a 3-tuple: (adx_values, plus_di, minus_di).

    Args:
        highs:  Daily high prices (oldest-first).
        lows:   Daily low prices (oldest-first).
        closes: Daily closing prices (oldest-first).
        period: Smoothing period (default 14, per Wilder).
    """
    n = len(closes)
    adx_vals: List[Optional[float]] = [None] * n
    pdi_vals: List[Optional[float]] = [None] * n
    mdi_vals: List[Optional[float]] = [None] * n

    if n < 2 * period + 1:
        return adx_vals, pdi_vals, mdi_vals

    # Step 1: True Range, +DM, -DM for each bar
    tr_list:  List[float] = []
    pdm_list: List[float] = []
    mdm_list: List[float] = []

    for i in range(1, n):
        high_low = highs[i] - lows[i]
        high_prev_close = abs(highs[i] - closes[i - 1])
        low_prev_close = abs(lows[i] - closes[i - 1])
        tr_list.append(max(high_low, high_prev_close, low_prev_close))

        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        pdm_list.append(up_move if (up_move > down_move and up_move > 0) else 0.0)
        mdm_list.append(down_move if (down_move > up_move and down_move > 0) else 0.0)

    # Step 2: Wilder-smooth the first *period* values (sum, not average)
    atr = sum(tr_list[:period])
    apdm = sum(pdm_list[:period])
    amdm = sum(mdm_list[:period])

    # Step 3: Rolling Wilder smooth + DI computation
    dx_list: List[float] = []

    for i in range(period, len(tr_list)):
        atr = atr - (atr / period) + tr_list[i]
        apdm = apdm - (apdm / period) + pdm_list[i]
        amdm = amdm - (amdm / period) + mdm_list[i]

        pdi = (apdm / atr * 100.0) if atr != 0 else 0.0
        mdi = (amdm / atr * 100.0) if atr != 0 else 0.0

        bar_idx = i + 1  # offset because tr_list starts at bar 1
        pdi_vals[bar_idx] = pdi
        mdi_vals[bar_idx] = mdi

        di_sum = pdi + mdi
        dx = (abs(pdi - mdi) / di_sum * 100.0) if di_sum != 0 else 0.0
        dx_list.append(dx)

    # Step 4: ADX = Wilder-smoothed average of DX over *period* values
    if len(dx_list) < period:
        return adx_vals, pdi_vals, mdi_vals

    adx_val = sum(dx_list[:period]) / period
    # The ADX starts at bar index = 2*period
    first_adx_bar = 2 * period
    if first_adx_bar < n:
        adx_vals[first_adx_bar] = adx_val

    for j in range(period, len(dx_list)):
        adx_val = (adx_val * (period - 1) + dx_list[j]) / period
        bar_idx = period + j + 1
        if bar_idx < n:
            adx_vals[bar_idx] = adx_val

    return adx_vals, pdi_vals, mdi_vals


# ====================================================================== #
#  STOCHASTIC OSCILLATOR  (George Lane, 1950s)                             #
# ====================================================================== #

def stochastic(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    k_period: int = 14,
    d_period: int = 3,
    smooth_k: int = 3,
) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    """
    Stochastic Oscillator — %K (slow) and %D.

    This implements the *slow* stochastic:
        raw_k  = (Close − Lowest Low) / (Highest High − Lowest Low) × 100
        %K     = SMA(raw_k, smooth_k)          ← the "slow" %K
        %D     = SMA(%K, d_period)

    Signals are strongest when a crossover happens above 80 or below 20.

    Args:
        highs:    Daily high prices (oldest-first).
        lows:     Daily low prices (oldest-first).
        closes:   Daily closing prices (oldest-first).
        k_period: Lookback window for raw %K (default 14).
        d_period: Smoothing for %D (default 3).
        smooth_k: Smoothing applied to raw %K to produce slow %K (default 3).

    Returns:
        (k_line, d_line) — each list has the same length as *closes*.
    """
    n = len(closes)
    k_line: List[Optional[float]] = [None] * n
    d_line: List[Optional[float]] = [None] * n

    if n < k_period:
        return k_line, d_line

    # Step 1: raw %K
    raw_k: List[Optional[float]] = [None] * n
    for i in range(k_period - 1, n):
        window_high = max(highs[i - k_period + 1 : i + 1])
        window_low = min(lows[i - k_period + 1 : i + 1])
        denom = window_high - window_low
        if denom > 0:
            raw_k[i] = ((closes[i] - window_low) / denom) * 100.0
        else:
            raw_k[i] = 50.0  # flat range edge case

    # Step 2: slow %K = SMA of raw_k
    raw_k_dense = [v for v in raw_k if v is not None]
    if len(raw_k_dense) >= smooth_k:
        slow_k_dense = sma(raw_k_dense, smooth_k)
        # Map back
        j = 0
        for i in range(n):
            if raw_k[i] is not None:
                k_line[i] = slow_k_dense[j]
                j += 1
    else:
        k_line = raw_k  # not enough data to smooth

    # Step 3: %D = SMA of slow %K
    k_dense = [v for v in k_line if v is not None]
    if len(k_dense) >= d_period:
        d_dense = sma(k_dense, d_period)
        j = 0
        for i in range(n):
            if k_line[i] is not None:
                d_line[i] = d_dense[j]
                j += 1

    return k_line, d_line


# ====================================================================== #
#  DIVERGENCE DETECTOR  (used by RSI, MACD, OBV frameworks)                #
# ====================================================================== #

def find_local_extrema(
    values: List[Optional[float]],
    order: int = 5,
) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """
    Find local maxima and minima without scipy.

    A point at index *i* is a local maximum if it is greater than the
    *order* points on either side.  Analogous for minima.

    Args:
        values: Data series (may contain Nones — these are skipped).
        order:  Number of neighbours on each side to compare.

    Returns:
        (maxima, minima) where each is a list of ``(index, value)`` tuples
        sorted by index.
    """
    maxima: List[Tuple[int, float]] = []
    minima: List[Tuple[int, float]] = []
    n = len(values)

    for i in range(order, n - order):
        val = values[i]
        if val is None:
            continue

        window = values[i - order : i + order + 1]
        clean = [v for v in window if v is not None]
        if not clean:
            continue

        if val == max(clean) and clean.count(val) == 1:
            maxima.append((i, val))
        if val == min(clean) and clean.count(val) == 1:
            minima.append((i, val))

    return maxima, minima


def detect_divergence(
    prices: List[float],
    indicator: List[Optional[float]],
    order: int = 5,
    lookback: int = 60,
) -> Optional[str]:
    """
    Detect bullish or bearish divergence between price and an indicator
    over the most recent *lookback* bars.

    Bullish divergence:
        Price makes a LOWER LOW, but the indicator makes a HIGHER LOW.
        → Bearish momentum is fading; possible reversal up.

    Bearish divergence:
        Price makes a HIGHER HIGH, but the indicator makes a LOWER HIGH.
        → Bullish momentum is fading; possible reversal down.

    Args:
        prices:    Closing prices (oldest-first, full series).
        indicator: Indicator values (same length, may contain Nones).
        order:     Extrema detection window.
        lookback:  How many bars from the end to scan.

    Returns:
        ``"bullish"``, ``"bearish"``, or ``None``.
    """
    n = len(prices)
    start = max(0, n - lookback)

    # Trim to the lookback window
    p_window = prices[start:]
    i_window = indicator[start:]

    _, p_minima = find_local_extrema(p_window, order)
    p_maxima, _ = find_local_extrema(p_window, order)
    _, i_minima = find_local_extrema(i_window, order)
    i_maxima, _ = find_local_extrema(i_window, order)

    # Bullish: last two price lows — lower low; last two indicator lows — higher low
    if len(p_minima) >= 2 and len(i_minima) >= 2:
        p1, p2 = p_minima[-2], p_minima[-1]  # p2 is more recent
        i1, i2 = i_minima[-2], i_minima[-1]
        if p2[1] < p1[1] and i2[1] > i1[1]:
            return "bullish"

    # Bearish: last two price highs — higher high; last two indicator highs — lower high
    if len(p_maxima) >= 2 and len(i_maxima) >= 2:
        p1, p2 = p_maxima[-2], p_maxima[-1]
        i1, i2 = i_maxima[-2], i_maxima[-1]
        if p2[1] > p1[1] and i2[1] < i1[1]:
            return "bearish"

    return None


# ====================================================================== #
#  ATR — Average True Range  (Wilder, 1978)                                #
# ====================================================================== #

def atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> List[Optional[float]]:
    """
    Average True Range — a volatility measure.

    True Range = max(H-L, |H-prevC|, |L-prevC|).
    ATR = Wilder-smoothed average of TR over *period*.

    Args:
        highs:  Daily high prices (oldest-first).
        lows:   Daily low prices (oldest-first).
        closes: Daily closing prices (oldest-first).
        period: Smoothing period (default 14).

    Returns:
        List of same length.  First *period* entries are None.
    """
    n = len(closes)
    result: List[Optional[float]] = [None] * n
    if n < period + 1:
        return result

    # True Range for each bar starting at index 1
    tr_vals: List[float] = []
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr_vals.append(max(hl, hc, lc))

    # Seed: SMA of first *period* TR values
    atr_val = sum(tr_vals[:period]) / period
    result[period] = atr_val

    # Wilder smoothing
    for i in range(period, len(tr_vals)):
        atr_val = (atr_val * (period - 1) + tr_vals[i]) / period
        result[i + 1] = atr_val

    return result


# ====================================================================== #
#  ROC — Rate of Change                                                    #
# ====================================================================== #

def roc(closes: List[float], period: int = 12) -> List[Optional[float]]:
    """
    Rate of Change — percentage change over *period* bars.

    ROC = (Close - Close_n_bars_ago) / Close_n_bars_ago × 100

    Positive ROC indicates upward momentum; negative indicates downward.
    Zero-crossing is a meaningful signal.

    Args:
        closes: Daily closing prices (oldest-first).
        period: Lookback window (default 12).

    Returns:
        List of same length.  First *period* entries are None.
    """
    n = len(closes)
    result: List[Optional[float]] = [None] * n
    if n <= period:
        return result

    for i in range(period, n):
        prev = closes[i - period]
        if prev != 0:
            result[i] = ((closes[i] - prev) / prev) * 100.0
        else:
            result[i] = 0.0

    return result


# ====================================================================== #
#  Williams %R  (Larry Williams)                                           #
# ====================================================================== #

def williams_r(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> List[Optional[float]]:
    """
    Williams %R — momentum oscillator ranging from -100 to 0.

    %R = (Highest High - Close) / (Highest High - Lowest Low) × -100

    Above -20 is overbought; below -80 is oversold.

    Args:
        highs:  Daily high prices (oldest-first).
        lows:   Daily low prices (oldest-first).
        closes: Daily closing prices (oldest-first).
        period: Lookback window (default 14).

    Returns:
        List of same length.  First *period-1* entries are None.
    """
    n = len(closes)
    result: List[Optional[float]] = [None] * n
    if n < period:
        return result

    for i in range(period - 1, n):
        hh = max(highs[i - period + 1 : i + 1])
        ll = min(lows[i - period + 1 : i + 1])
        denom = hh - ll
        if denom > 0:
            result[i] = ((hh - closes[i]) / denom) * -100.0
        else:
            result[i] = -50.0  # flat range edge case

    return result


# ====================================================================== #
#  CCI — Commodity Channel Index  (Donald Lambert, 1980)                   #
# ====================================================================== #

def cci(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 20,
) -> List[Optional[float]]:
    """
    Commodity Channel Index — measures deviation from the statistical mean.

    CCI = (Typical Price - SMA(TP)) / (0.015 × Mean Deviation)

    Above +100 = overbought / strong uptrend.
    Below -100 = oversold / strong downtrend.

    Args:
        highs:  Daily high prices (oldest-first).
        lows:   Daily low prices (oldest-first).
        closes: Daily closing prices (oldest-first).
        period: Lookback window (default 20).

    Returns:
        List of same length.  First *period-1* entries are None.
    """
    n = len(closes)
    result: List[Optional[float]] = [None] * n
    if n < period:
        return result

    # Typical price
    tp = [(highs[i] + lows[i] + closes[i]) / 3.0 for i in range(n)]

    for i in range(period - 1, n):
        window = tp[i - period + 1 : i + 1]
        mean_tp = sum(window) / period
        mean_dev = sum(abs(v - mean_tp) for v in window) / period
        if mean_dev != 0:
            result[i] = (tp[i] - mean_tp) / (0.015 * mean_dev)
        else:
            result[i] = 0.0

    return result


# ====================================================================== #
#  CMF — Chaikin Money Flow  (Marc Chaikin)                                #
# ====================================================================== #

def cmf(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    period: int = 20,
) -> List[Optional[float]]:
    """
    Chaikin Money Flow — volume-weighted accumulation / distribution.

    CMF = Sum(Money Flow Volume, period) / Sum(Volume, period)

    Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
    Money Flow Volume = MFM × Volume

    Positive CMF = buying pressure (accumulation).
    Negative CMF = selling pressure (distribution).

    Args:
        highs:   Daily high prices (oldest-first).
        lows:    Daily low prices (oldest-first).
        closes:  Daily closing prices (oldest-first).
        volumes: Daily volumes.
        period:  Lookback window (default 20).

    Returns:
        List of same length.  First *period-1* entries are None.
        Values range roughly from -1.0 to +1.0.
    """
    n = len(closes)
    result: List[Optional[float]] = [None] * n
    if n < period:
        return result

    # Money Flow Volume for each bar
    mfv: List[float] = []
    for i in range(n):
        hl = highs[i] - lows[i]
        if hl > 0:
            mfm = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl
        else:
            mfm = 0.0
        mfv.append(mfm * volumes[i])

    for i in range(period - 1, n):
        window_mfv = mfv[i - period + 1 : i + 1]
        window_vol = volumes[i - period + 1 : i + 1]
        total_vol = sum(window_vol)
        if total_vol > 0:
            result[i] = sum(window_mfv) / total_vol
        else:
            result[i] = 0.0

    return result


# ====================================================================== #
#  ICHIMOKU CLOUD  (Goichi Hosoda, 1960s)                                  #
# ====================================================================== #

def ichimoku(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
) -> Dict[str, List[Optional[float]]]:
    """
    Ichimoku Cloud — comprehensive trend, support/resistance system.

    Components (all calculated without displacement for backtesting):
        - Tenkan-sen (Conversion Line): midpoint of 9-period H/L
        - Kijun-sen (Base Line): midpoint of 26-period H/L
        - Senkou Span A: average of Tenkan + Kijun
        - Senkou Span B: midpoint of 52-period H/L
        - Chikou Span: current close (compared to price 26 bars ago)

    Bull signal: Price above cloud, Tenkan > Kijun, Chikou > price 26 ago.
    Bear signal: Price below cloud, Tenkan < Kijun, Chikou < price 26 ago.

    Args:
        highs:  Daily high prices (oldest-first).
        lows:   Daily low prices (oldest-first).
        closes: Daily closing prices (oldest-first).
        tenkan_period:  Tenkan-sen period (default 9).
        kijun_period:   Kijun-sen period (default 26).
        senkou_b_period: Senkou Span B period (default 52).

    Returns:
        Dict with keys: tenkan, kijun, senkou_a, senkou_b, chikou.
        Each is a list of the same length as the input.
    """
    n = len(closes)
    tenkan: List[Optional[float]] = [None] * n
    kijun: List[Optional[float]] = [None] * n
    senkou_a: List[Optional[float]] = [None] * n
    senkou_b: List[Optional[float]] = [None] * n
    chikou: List[Optional[float]] = [None] * n

    def _midpoint(series_h: List[float], series_l: List[float],
                  end_idx: int, period: int) -> Optional[float]:
        if end_idx < period - 1:
            return None
        start = end_idx - period + 1
        hh = max(series_h[start : end_idx + 1])
        ll = min(series_l[start : end_idx + 1])
        return (hh + ll) / 2.0

    for i in range(n):
        tenkan[i] = _midpoint(highs, lows, i, tenkan_period)
        kijun[i] = _midpoint(highs, lows, i, kijun_period)
        senkou_b[i] = _midpoint(highs, lows, i, senkou_b_period)

        # Senkou A = average of Tenkan and Kijun (current, not displaced)
        if tenkan[i] is not None and kijun[i] is not None:
            senkou_a[i] = (tenkan[i] + kijun[i]) / 2.0

        # Chikou = close compared to price 26 bars ago
        if i >= kijun_period:
            chikou[i] = closes[i]  # value is the current close

    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou,
    }


# ====================================================================== #
#  VWAP — Volume Weighted Average Price                                    #
# ====================================================================== #

def vwap(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    period: int = 20,
) -> List[Optional[float]]:
    """
    Rolling VWAP — volume-weighted average price over *period* bars.

    VWAP = Σ(Typical Price × Volume) / Σ(Volume) over last *period* bars.

    Price above VWAP = bullish; below = bearish.
    Institutional traders use VWAP as a benchmark.

    Args:
        highs:   Daily high prices (oldest-first).
        lows:    Daily low prices (oldest-first).
        closes:  Daily closing prices (oldest-first).
        volumes: Daily volumes.
        period:  Rolling window (default 20).

    Returns:
        List of same length.  First *period-1* entries are None.
    """
    n = len(closes)
    result: List[Optional[float]] = [None] * n
    if n < period:
        return result

    for i in range(period - 1, n):
        tp_vol_sum = 0.0
        vol_sum = 0.0
        for j in range(i - period + 1, i + 1):
            tp = (highs[j] + lows[j] + closes[j]) / 3.0
            tp_vol_sum += tp * volumes[j]
            vol_sum += volumes[j]

        if vol_sum > 0:
            result[i] = tp_vol_sum / vol_sum
        else:
            result[i] = closes[i]

    return result


# ====================================================================== #
#  v3 INDICATORS: Supertrend, Stochastic RSI, Keltner, Fib, Structure     #
# ====================================================================== #

def supertrend(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 10,
    multiplier: float = 3.0,
) -> Tuple[List[Optional[float]], List[Optional[int]]]:
    """
    Supertrend indicator — dynamic support/resistance with direction.

    Returns:
        (supertrend_line, direction)
        supertrend_line: price level acting as support (uptrend) or
                         resistance (downtrend).
        direction: +1 = uptrend (buy), -1 = downtrend (sell), None = warm-up.
    """
    n = len(closes)
    st_line: List[Optional[float]] = [None] * n
    direction: List[Optional[int]] = [None] * n
    if n < period + 1:
        return st_line, direction

    atr_vals = atr(highs, lows, closes, period)

    upper: List[float] = [0.0] * n
    lower: List[float] = [0.0] * n

    for i in range(period, n):
        a = atr_vals[i]
        if a is None:
            continue
        hl2 = (highs[i] + lows[i]) / 2.0
        basic_upper = hl2 + multiplier * a
        basic_lower = hl2 - multiplier * a

        # Carry forward: upper can only decrease, lower can only increase
        if i == period:
            upper[i] = basic_upper
            lower[i] = basic_lower
            direction[i] = 1 if closes[i] > basic_upper else -1
        else:
            upper[i] = min(basic_upper, upper[i - 1]) if closes[i - 1] <= upper[i - 1] else basic_upper
            lower[i] = max(basic_lower, lower[i - 1]) if closes[i - 1] >= lower[i - 1] else basic_lower

            prev_dir = direction[i - 1] or 1
            if prev_dir == 1:
                direction[i] = -1 if closes[i] < lower[i] else 1
            else:
                direction[i] = 1 if closes[i] > upper[i] else -1

        st_line[i] = lower[i] if direction[i] == 1 else upper[i]

    return st_line, direction


def stochastic_rsi(
    closes: List[float],
    rsi_period: int = 14,
    stoch_period: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    """
    Stochastic RSI — applies the stochastic formula to RSI values.

    More sensitive than regular Stochastic for overbought/oversold detection.

    Returns:
        (stoch_rsi_k, stoch_rsi_d) — both scaled 0–100.
    """
    n = len(closes)
    rsi_vals = rsi(closes, rsi_period)

    raw_stoch: List[Optional[float]] = [None] * n
    warmup = rsi_period + stoch_period - 1

    for i in range(warmup, n):
        window = []
        for j in range(i - stoch_period + 1, i + 1):
            if rsi_vals[j] is not None:
                window.append(rsi_vals[j])
        if len(window) < stoch_period:
            continue
        rsi_min = min(window)
        rsi_max = max(window)
        if rsi_max - rsi_min == 0:
            raw_stoch[i] = 50.0
        else:
            raw_stoch[i] = ((rsi_vals[i] - rsi_min) / (rsi_max - rsi_min)) * 100.0

    # Smooth %K
    stoch_k_vals = sma(
        [v if v is not None else 0.0 for v in raw_stoch], k_smooth
    )
    # Fix None for warmup — clamp to list length to avoid IndexError on short inputs
    for i in range(min(warmup + k_smooth - 1, len(stoch_k_vals))):
        stoch_k_vals[i] = None

    stoch_d_vals = sma(
        [v if v is not None else 0.0 for v in stoch_k_vals], d_smooth
    )
    for i in range(min(warmup + k_smooth + d_smooth - 2, len(stoch_d_vals))):
        stoch_d_vals[i] = None

    return stoch_k_vals, stoch_d_vals


def keltner_channel(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 2.0,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    Keltner Channel — EMA ± multiplier × ATR.

    Bollinger Bands inside Keltner Channel = squeeze (low volatility, pending breakout).

    Returns:
        (kc_upper, kc_middle, kc_lower)
    """
    n = len(closes)
    kc_upper: List[Optional[float]] = [None] * n
    kc_middle = ema(closes, ema_period)
    kc_lower: List[Optional[float]] = [None] * n

    atr_vals = atr(highs, lows, closes, atr_period)

    for i in range(n):
        mid = kc_middle[i]
        a = atr_vals[i]
        if mid is not None and a is not None:
            kc_upper[i] = mid + multiplier * a
            kc_lower[i] = mid - multiplier * a

    return kc_upper, kc_middle, kc_lower


def bb_kc_squeeze(
    bb_upper: List[Optional[float]],
    bb_lower: List[Optional[float]],
    kc_upper: List[Optional[float]],
    kc_lower: List[Optional[float]],
) -> List[Optional[bool]]:
    """
    Bollinger Band / Keltner Channel squeeze detection.

    Squeeze ON = BB is inside KC (low volatility, breakout imminent).
    Returns list of booleans.
    """
    n = len(bb_upper)
    result: List[Optional[bool]] = [None] * n
    for i in range(n):
        if (bb_upper[i] is not None and bb_lower[i] is not None
                and kc_upper[i] is not None and kc_lower[i] is not None):
            result[i] = bb_lower[i] > kc_lower[i] and bb_upper[i] < kc_upper[i]
    return result


def fibonacci_retracement(
    highs: List[float],
    lows: List[float],
    lookback: int = 60,
) -> Dict[str, Optional[float]]:
    """
    Compute Fibonacci retracement levels from the swing high/low over
    the last *lookback* bars.

    Returns dict with keys:
        swing_high, swing_low, fib_236, fib_382, fib_500, fib_618, fib_786,
        current_zone (which fib band price is nearest).
    """
    if len(highs) < lookback or len(lows) < lookback:
        return {
            "swing_high": None, "swing_low": None,
            "fib_236": None, "fib_382": None, "fib_500": None,
            "fib_618": None, "fib_786": None,
        }

    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    swing_high = max(recent_highs)
    swing_low = min(recent_lows)
    diff = swing_high - swing_low

    if diff <= 0:
        return {
            "swing_high": swing_high, "swing_low": swing_low,
            "fib_236": None, "fib_382": None, "fib_500": None,
            "fib_618": None, "fib_786": None,
        }

    return {
        "swing_high": round(swing_high, 4),
        "swing_low":  round(swing_low, 4),
        "fib_236":    round(swing_high - 0.236 * diff, 4),
        "fib_382":    round(swing_high - 0.382 * diff, 4),
        "fib_500":    round(swing_high - 0.500 * diff, 4),
        "fib_618":    round(swing_high - 0.618 * diff, 4),
        "fib_786":    round(swing_high - 0.786 * diff, 4),
    }


def market_structure(
    highs: List[float],
    lows: List[float],
    order: int = 5,
) -> Dict[str, Any]:
    """
    Classify price structure as Higher Highs / Higher Lows (uptrend),
    Lower Highs / Lower Lows (downtrend), or mixed (consolidation).

    Uses local extrema with *order* bar lookback on each side.

    Returns:
        {trend: "uptrend"|"downtrend"|"consolidation",
         higher_highs: int, lower_highs: int,
         higher_lows: int, lower_lows: int,
         swing_highs: [...], swing_lows: [...]}
    """
    n = len(highs)
    if n < order * 2 + 1:
        return {"trend": "unknown", "higher_highs": 0, "lower_highs": 0,
                "higher_lows": 0, "lower_lows": 0,
                "swing_highs": [], "swing_lows": []}

    # find_local_extrema returns (maxima, minima) — each is List[(idx, val)]
    # For swing highs: find maxima in the highs series
    sh_maxima, _ = find_local_extrema(highs, order)
    # For swing lows: find minima in the lows series
    _, sl_minima = find_local_extrema(lows, order)

    # Last 6 swings for classification
    recent_sh = sh_maxima[-6:] if len(sh_maxima) >= 2 else sh_maxima
    recent_sl = sl_minima[-6:] if len(sl_minima) >= 2 else sl_minima

    hh = ll = hl = lh = 0
    for i in range(1, len(recent_sh)):
        if recent_sh[i][1] > recent_sh[i - 1][1]:
            hh += 1
        else:
            lh += 1
    for i in range(1, len(recent_sl)):
        if recent_sl[i][1] > recent_sl[i - 1][1]:
            hl += 1
        else:
            ll += 1

    if hh >= 2 and hl >= 2:
        trend = "uptrend"
    elif lh >= 2 and ll >= 2:
        trend = "downtrend"
    else:
        trend = "consolidation"

    return {
        "trend": trend,
        "higher_highs": hh,
        "lower_highs": lh,
        "higher_lows": hl,
        "lower_lows": ll,
        "swing_highs": [t[1] for t in recent_sh],
        "swing_lows":  [t[1] for t in recent_sl],
    }


# ====================================================================== #
#  CONVENIENCE: compute all indicators at once                             #
# ====================================================================== #

def compute_all_indicators(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
) -> dict:
    """
    Compute every indicator family and return a flat dict.

    This is called by the ``compute_indicators`` node of the LangGraph
    pipeline.  The keys match what ``rules.py`` expects.

    v3 additions: ema_9, ema_21, supertrend, stochastic_rsi, keltner,
    bb_kc_squeeze, fibonacci, market_structure.
    """
    ema_9 = ema(closes, 9)
    ema_21 = ema(closes, 21)
    ema_20 = ema(closes, 20)
    ema_50 = ema(closes, 50)
    ema_200 = ema(closes, 200)
    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    sma_200 = sma(closes, 200)

    rsi_14 = rsi(closes, 14)

    macd_line, macd_signal, macd_hist = macd(closes, 12, 26, 9)

    bb_upper, bb_middle, bb_lower, bb_pct_b, bb_bw = bollinger_bands(
        closes, 20, 2.0
    )

    obv_vals = obv(closes, volumes)

    adx_vals, plus_di, minus_di = adx(highs, lows, closes, 14)

    stoch_k, stoch_d = stochastic(highs, lows, closes, 14, 3, 3)

    # v2 indicators
    atr_14 = atr(highs, lows, closes, 14)
    roc_12 = roc(closes, 12)
    williams_r_14 = williams_r(highs, lows, closes, 14)
    cci_20 = cci(highs, lows, closes, 20)
    cmf_20 = cmf(highs, lows, closes, volumes, 20)
    ichi = ichimoku(highs, lows, closes, 9, 26, 52)
    vwap_20 = vwap(highs, lows, closes, volumes, 20)

    # v3 indicators
    st_line, st_direction = supertrend(highs, lows, closes, 10, 3.0)
    srsi_k, srsi_d = stochastic_rsi(closes, 14, 14, 3, 3)
    kc_upper, kc_middle, kc_lower = keltner_channel(
        highs, lows, closes, 20, 10, 2.0
    )
    squeeze = bb_kc_squeeze(bb_upper, bb_lower, kc_upper, kc_lower)
    fib_levels = fibonacci_retracement(highs, lows, 60)
    mkt_structure = market_structure(highs, lows, 5)

    return {
        "ema_9": ema_9,
        "ema_21": ema_21,
        "ema_20": ema_20,
        "ema_50": ema_50,
        "ema_200": ema_200,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "rsi_14": rsi_14,
        "macd_line": macd_line,
        "macd_signal": macd_signal,
        "macd_histogram": macd_hist,
        "bb_upper": bb_upper,
        "bb_middle": bb_middle,
        "bb_lower": bb_lower,
        "bb_pct_b": bb_pct_b,
        "bb_bandwidth": bb_bw,
        "obv": obv_vals,
        "adx": adx_vals,
        "plus_di": plus_di,
        "minus_di": minus_di,
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
        # v2 indicators
        "atr_14": atr_14,
        "roc_12": roc_12,
        "williams_r_14": williams_r_14,
        "cci_20": cci_20,
        "cmf_20": cmf_20,
        "ichimoku_tenkan": ichi["tenkan"],
        "ichimoku_kijun": ichi["kijun"],
        "ichimoku_senkou_a": ichi["senkou_a"],
        "ichimoku_senkou_b": ichi["senkou_b"],
        "ichimoku_chikou": ichi["chikou"],
        "vwap_20": vwap_20,
        # v3 indicators
        "supertrend_line": st_line,
        "supertrend_direction": st_direction,
        "stoch_rsi_k": srsi_k,
        "stoch_rsi_d": srsi_d,
        "kc_upper": kc_upper,
        "kc_middle": kc_middle,
        "kc_lower": kc_lower,
        "squeeze_on": squeeze,
        "fibonacci": fib_levels,
        "market_structure": mkt_structure,
    }
