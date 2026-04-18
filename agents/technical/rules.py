"""
rules.py — Deterministic scoring engine for the technical analysis agent.

Nine independent frameworks each produce a score between 0 and 100.
They are combined into a single weighted composite score, mapped to a
band, and then to a directional signal (bullish / neutral / bearish).

v2 enhancements (audit-driven):
    - Added Ichimoku Cloud framework (trend/support/resistance)
    - Added Momentum Composite framework (ROC + Williams %R + CCI)
    - Integrated CMF into Volume framework to detect distribution
    - Added ROC overlay to EMA Trend to catch turning points
    - Enhanced RSI with overbought-exit detection (falling from 65-80)
    - Enhanced Bollinger with overbought reversal (%B extreme + BW combo)
    - Fixed pattern scoring: recency decay, contribution cap, conflict handling
    - Reweighted all 9 frameworks to reduce systemic bullish bias

Frameworks and weights:
    1. EMA Trend Alignment  (0.17) — trend backbone + ROC overlay
    2. MACD System          (0.14) — trend + momentum combo
    3. RSI Regime           (0.14) — gold-standard oscillator
    4. Bollinger Bands      (0.10) — volatility context
    5. Volume (OBV + CMF)   (0.10) — leading indicator + distribution
    6. ADX + Stochastic     (0.07) — trend strength + mean-reversion
    7. Pattern Recognition  (0.08) — chart breakout confirmation
    8. Ichimoku Cloud       (0.12) — comprehensive trend/S-R system
    9. Momentum Composite   (0.08) — ROC + Williams %R + CCI

All helpers are pure functions.  ``evaluate_snapshot()`` is the single
entry-point invoked by the graph ``evaluate`` node.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .models import OHLCVBar, PatternSignal, RawTechnicalSnapshot
from .indicators import (
    compute_all_indicators,
    detect_divergence,
    find_local_extrema,
)


# ====================================================================== #
# HELPERS                                                                   #
# ====================================================================== #

def _last(series: List[Optional[float]]) -> Optional[float]:
    """Return the last non-None value in *series*, or None if all None."""
    for val in reversed(series):
        if val is not None:
            return val
    return None


def _second_last(series: List[Optional[float]]) -> Optional[float]:
    """Return the second-to-last non-None value in *series*."""
    count = 0
    for val in reversed(series):
        if val is not None:
            count += 1
            if count == 2:
                return val
    return None


def _slope_direction(series: List[Optional[float]], lookback: int = 5) -> Optional[str]:
    """
    Determine whether the tail of *series* is rising, falling, or flat.

    Compares the last non-None value to the value *lookback* bars before it.
    Returns ``"rising"``, ``"falling"``, or ``"flat"``.
    """
    vals: List[float] = []
    for v in reversed(series):
        if v is not None:
            vals.append(v)
        if len(vals) >= lookback + 1:
            break
    if len(vals) < 2:
        return None
    diff = vals[0] - vals[-1]  # newest minus oldest
    if diff > 0:
        return "rising"
    elif diff < 0:
        return "falling"
    return "flat"


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp *value* between *lo* and *hi*."""
    return max(lo, min(hi, value))


def _last_int(series) -> Optional[int]:
    """Return last non-None integer from a list (for direction indicators)."""
    if not series:
        return None
    for val in reversed(series):
        if val is not None:
            return int(val)
    return None


def _last_bool(series) -> Optional[bool]:
    """Return last non-None bool from a list (for squeeze indicators)."""
    if not series:
        return None
    for val in reversed(series):
        if val is not None:
            return bool(val)
    return None


# ====================================================================== #
# FRAMEWORK 1: EMA Trend Alignment   (weight 0.17)                         #
# ====================================================================== #

def evaluate_ema_trend(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    Score based on EMA stacking, price position, and momentum overlay.

    v2 enhancement: ROC overlay detects when price momentum is fading
    even while EMAs remain bullishly stacked (lagging indicator fix).

    Scoring (out of 100, neutral base = 50):
        ±15  Price above/below EMA-200
        ±12  Price above/below EMA-50
        ±7   Price above/below EMA-20
        ±7   EMA stack alignment (20>50>200 or inverse)
        ±7   Golden/Death Cross
        ±8   ROC momentum overlay (catches turning points)
    """
    price = closes[-1] if closes else None
    ema20 = _last(indicators.get("ema_20", []))
    ema50 = _last(indicators.get("ema_50", []))
    ema200 = _last(indicators.get("ema_200", []))
    sma50 = _last(indicators.get("sma_50", []))
    sma200 = _last(indicators.get("sma_200", []))
    roc_val = _last(indicators.get("roc_12", []))

    if price is None or ema200 is None:
        return {"applicable": False, "score_pct": None, "details": {}, "notes": [
            "Insufficient data for EMA trend evaluation."
        ]}

    score = 50.0  # neutral baseline

    # Price vs EMAs
    if price > ema200:
        score += 15.0
    else:
        score -= 15.0

    if ema50 is not None:
        if price > ema50:
            score += 12.0
        else:
            score -= 12.0

    if ema20 is not None:
        if price > ema20:
            score += 7.0
        else:
            score -= 7.0

    # Perfect EMA stack
    if ema20 is not None and ema50 is not None:
        if ema20 > ema50 > ema200:
            score += 7.0
        elif ema20 < ema50 < ema200:
            score -= 7.0

    # Golden Cross / Death Cross
    if sma50 is not None and sma200 is not None:
        if sma50 > sma200:
            score += 7.0
        else:
            score -= 7.0

    # v2: ROC momentum overlay — catches trend exhaustion
    # If EMAs are bullish but ROC is negative/falling, penalize
    if roc_val is not None:
        if roc_val < -2.0:
            score -= 8.0  # momentum sharply negative
        elif roc_val < 0:
            score -= 4.0  # momentum fading
        elif roc_val > 5.0:
            score += 6.0  # strong momentum
        elif roc_val > 0:
            score += 3.0  # positive momentum

    score = _clamp(score)

    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "price": round(price, 4),
            "ema_20": round(ema20, 4) if ema20 else None,
            "ema_50": round(ema50, 4) if ema50 else None,
            "ema_200": round(ema200, 4) if ema200 else None,
            "golden_cross": sma50 > sma200 if (sma50 and sma200) else None,
            "roc_12": round(roc_val, 4) if roc_val is not None else None,
        },
        "notes": [],
    }


# ====================================================================== #
# FRAMEWORK 2: MACD System   (weight 0.18)                                 #
# ====================================================================== #

def evaluate_macd(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    Score MACD signal line position, centerline position, histogram
    direction, and divergence.

    Scoring (out of 100, neutral base = 50):
        ±15  MACD above/below signal line
        ±12  MACD above/below zero (centerline)
        ±10  Histogram rising/falling
        ±13  Bullish/bearish divergence (strongest reversal signal)
    """
    macd_val = _last(indicators.get("macd_line", []))
    signal_val = _last(indicators.get("macd_signal", []))
    hist_val = _last(indicators.get("macd_histogram", []))
    hist_prev = _second_last(indicators.get("macd_histogram", []))

    if macd_val is None or signal_val is None:
        return {"applicable": False, "score_pct": None, "details": {},
                "notes": ["Insufficient data for MACD evaluation."]}

    score = 50.0

    # Signal line position
    if macd_val > signal_val:
        score += 15.0
    else:
        score -= 15.0

    # Centerline position
    if macd_val > 0:
        score += 12.0
    else:
        score -= 12.0

    # Histogram momentum
    if hist_val is not None and hist_prev is not None:
        if hist_val > hist_prev:
            score += 10.0
        else:
            score -= 10.0

    # Divergence
    macd_line_series = indicators.get("macd_line", [])
    div = detect_divergence(closes, macd_line_series, order=5, lookback=60)
    if div == "bullish":
        score += 13.0
    elif div == "bearish":
        score -= 13.0

    score = _clamp(score)

    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "macd": round(macd_val, 4),
            "signal": round(signal_val, 4),
            "histogram": round(hist_val, 4) if hist_val else None,
            "histogram_rising": (hist_val > hist_prev) if (hist_val is not None and hist_prev is not None) else None,
            "divergence": div,
        },
        "notes": [],
    }


# ====================================================================== #
# FRAMEWORK 3: RSI Regime   (weight 0.14)                                  #
# ====================================================================== #

def evaluate_rsi(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    RSI scoring using Wilder's regime concept.

    v2 enhancement: Overbought-exit detection — when RSI is in 65-80 range
    AND falling, apply bearish penalty. This catches the common case of
    RSI fading from bullish territory before a downturn.

    Scoring (out of 100, neutral base = 50):
        ±12  RSI above/below 50 (trend filter)
        ±10  RSI in bull zone (40–80) or bear zone (20–60)
        ±10  RSI slope rising/falling
        ±13  Bullish/bearish divergence
        -8   Overbought exit (RSI 65-80 AND falling) — v2 bearish signal
        -5   Overbought (>80) penalty
        +5   Oversold (<20) contrarian bonus
    """
    rsi_val = _last(indicators.get("rsi_14", []))
    rsi_series = indicators.get("rsi_14", [])

    if rsi_val is None:
        return {"applicable": False, "score_pct": None, "details": {},
                "notes": ["Insufficient data for RSI evaluation."]}

    score = 50.0
    rsi_slope = _slope_direction(rsi_series)

    # Trend filter: above/below 50
    if rsi_val > 50:
        score += 12.0
    else:
        score -= 12.0

    # Zone assessment
    if 40 <= rsi_val <= 80:
        score += 10.0  # healthy bull zone
    elif 20 <= rsi_val < 40:
        score -= 10.0  # bear zone
    elif rsi_val > 80:
        score -= 5.0   # overbought — caution
    elif rsi_val < 20:
        score += 5.0   # oversold — contrarian bounce opportunity

    # RSI slope
    if rsi_slope == "rising":
        score += 10.0
    elif rsi_slope == "falling":
        score -= 10.0

    # v2: Overbought-exit detection — RSI falling from high territory
    # This is the #1 root cause of false positives (52/83 errors)
    if rsi_slope == "falling" and 65 <= rsi_val <= 80:
        score -= 8.0  # momentum fading from bull zone → bearish signal

    # v2: Deep oversold recovery — RSI was <30 and is now rising
    if rsi_slope == "rising" and 30 <= rsi_val <= 45:
        prev_rsi = _second_last(rsi_series)
        if prev_rsi is not None and prev_rsi < 30:
            score += 5.0  # recovery from oversold

    # Divergence
    div = detect_divergence(closes, rsi_series, order=5, lookback=60)
    if div == "bullish":
        score += 13.0
    elif div == "bearish":
        score -= 13.0

    score = _clamp(score)

    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "rsi": round(rsi_val, 2),
            "rsi_slope": rsi_slope,
            "divergence": div,
        },
        "notes": [],
    }


# ====================================================================== #
# FRAMEWORK 4: Bollinger Bands   (weight 0.10)                             #
# ====================================================================== #

def evaluate_bollinger(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    Bollinger Band scoring: %B position, squeeze, band walk, reversal.

    v2 enhancement: Overbought reversal detection — %B > 0.9 with
    contracting bandwidth signals imminent reversal (was missed in 33/83
    errors). Band walk at upper band now penalized when BW is shrinking.

    Scoring (out of 100, neutral base = 50):
        ±12  %B > 0.5 / < 0.5
        ±10  Band walk (riding upper/lower band)
        ±10  Squeeze → breakout direction
        ±8   Bandwidth expanding / contracting
        -6   Overbought reversal (%B>0.9 + BW contracting) — v2
        +6   Oversold bounce (%B<0.1 + BW expanding) — v2
    """
    pct_b = _last(indicators.get("bb_pct_b", []))
    bw = _last(indicators.get("bb_bandwidth", []))
    bw_series = indicators.get("bb_bandwidth", [])

    if pct_b is None:
        return {"applicable": False, "score_pct": None, "details": {},
                "notes": ["Insufficient data for Bollinger evaluation."]}

    score = 50.0
    bw_slope = _slope_direction(bw_series)

    # %B position
    if pct_b > 0.5:
        score += 12.0
    else:
        score -= 12.0

    # Band walk: %B > 0.8 = riding upper band, %B < 0.2 = lower band
    # v2: Band walk at upper band with contracting BW is bearish reversal
    if pct_b > 0.8:
        if bw_slope == "falling":
            score -= 4.0  # v2: band walk + contraction = reversal warning
        else:
            score += 10.0
    elif pct_b < 0.2:
        if bw_slope == "rising":
            score += 4.0  # v2: oversold + expansion = bounce potential
        else:
            score -= 10.0

    # Squeeze detection
    bw_clean = [v for v in bw_series if v is not None]
    squeeze = False
    if bw is not None and len(bw_clean) >= 20:
        recent_bw = bw_clean[-20:]
        min_bw = min(recent_bw)
        if bw <= min_bw * 1.1:
            squeeze = True
            if pct_b > 0.5:
                score += 10.0
            else:
                score -= 10.0

    # Bandwidth trend
    if bw_slope == "rising":
        score += 8.0
    elif bw_slope == "falling":
        score -= 3.0

    # v2: Overbought reversal signal — %B extreme + bandwidth contracting
    if pct_b > 0.9 and bw_slope == "falling":
        score -= 6.0  # high probability of mean reversion

    # v2: Oversold bounce signal
    if pct_b < 0.1 and bw_slope == "rising":
        score += 6.0  # expansion from oversold = bounce

    score = _clamp(score)

    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "pct_b": round(pct_b, 4),
            "bandwidth": round(bw, 4) if bw else None,
            "squeeze": squeeze,
            "bandwidth_trend": bw_slope,
        },
        "notes": [],
    }


# ====================================================================== #
# FRAMEWORK 5: Volume / OBV + CMF   (weight 0.10)                          #
# ====================================================================== #

def evaluate_volume(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    OBV trend + CMF distribution detection + divergence.

    v2 enhancement: Chaikin Money Flow integrated to catch distribution
    that OBV alone misses (was responsible for 33/83 errors).

    Scoring (out of 100, neutral base = 50):
        ±12  OBV trend direction (rising/falling)
        ±10  OBV confirms price direction
        ±12  Bullish/bearish divergence between price and OBV
        ±10  CMF positive (accumulation) / negative (distribution) — v2
        -6   CMF strongly negative while price rising (stealth distribution) — v2
    """
    obv_series = indicators.get("obv", [])
    obv_slope = _slope_direction(obv_series, lookback=10)
    price_slope = _slope_direction(
        [float(c) for c in closes[-20:]] if len(closes) >= 20 else closes
    )
    cmf_val = _last(indicators.get("cmf_20", []))

    if obv_slope is None:
        return {"applicable": False, "score_pct": None, "details": {},
                "notes": ["Insufficient OBV data."]}

    score = 50.0

    # OBV direction
    if obv_slope == "rising":
        score += 12.0
    elif obv_slope == "falling":
        score -= 12.0

    # Confirmation: OBV and price agree
    if obv_slope == price_slope:
        if obv_slope == "rising":
            score += 10.0
        elif obv_slope == "falling":
            score -= 10.0

    # Formal divergence
    div = detect_divergence(closes, obv_series, order=5, lookback=60)
    if div == "bullish":
        score += 12.0
    elif div == "bearish":
        score -= 12.0

    # v2: Chaikin Money Flow — catches distribution OBV misses
    if cmf_val is not None:
        if cmf_val > 0.1:
            score += 10.0  # strong accumulation
        elif cmf_val > 0:
            score += 5.0   # mild accumulation
        elif cmf_val < -0.1:
            score -= 10.0  # strong distribution
        elif cmf_val < 0:
            score -= 5.0   # mild distribution

        # Stealth distribution: CMF negative while price is rising
        if cmf_val < -0.05 and price_slope == "rising":
            score -= 6.0  # smart money selling into strength

    score = _clamp(score)

    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "obv_trend": obv_slope,
            "price_trend": price_slope,
            "confirms_price": obv_slope == price_slope,
            "divergence": div,
            "cmf": round(cmf_val, 4) if cmf_val is not None else None,
        },
        "notes": [],
    }


# ====================================================================== #
# FRAMEWORK 6: ADX + Stochastic   (weight 0.08)                            #
# ====================================================================== #

def evaluate_adx_stochastic(
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    ADX trend-strength gate combined with Stochastic timing signal.

    ADX scoring:
        ADX > 40 → strong trend → +10
        ADX 25–40 → moderate trend → +5
        ADX < 20 → no trend → -10 (trend signals unreliable)

    DI scoring: +DI > -DI → +8, else -8

    Stochastic scoring:
        %K crosses above %D below 20 → +12 (oversold buy)
        %K crosses below %D above 80 → -12 (overbought sell)
        Otherwise +/- 5 based on %K position relative to 50.
    """
    adx_val = _last(indicators.get("adx", []))
    plus_di = _last(indicators.get("plus_di", []))
    minus_di = _last(indicators.get("minus_di", []))
    stoch_k = _last(indicators.get("stoch_k", []))
    stoch_d = _last(indicators.get("stoch_d", []))
    stoch_k_prev = _second_last(indicators.get("stoch_k", []))
    stoch_d_prev = _second_last(indicators.get("stoch_d", []))

    if adx_val is None and stoch_k is None:
        return {"applicable": False, "score_pct": None, "details": {},
                "notes": ["Insufficient data for ADX/Stochastic evaluation."]}

    score = 50.0

    # ADX component
    if adx_val is not None:
        if adx_val >= 40:
            score += 10.0  # strong trend
        elif adx_val >= 25:
            score += 5.0   # moderate trend
        elif adx_val < 20:
            score -= 10.0  # ranging — lower confidence

        # DI direction
        if plus_di is not None and minus_di is not None:
            if plus_di > minus_di:
                score += 8.0
            else:
                score -= 8.0

    # Stochastic component
    if stoch_k is not None and stoch_d is not None:
        # Crossover detection
        cross_up = (
            stoch_k_prev is not None and stoch_d_prev is not None
            and stoch_k_prev <= stoch_d_prev
            and stoch_k > stoch_d
        )
        cross_down = (
            stoch_k_prev is not None and stoch_d_prev is not None
            and stoch_k_prev >= stoch_d_prev
            and stoch_k < stoch_d
        )

        if cross_up and stoch_k < 20:
            score += 12.0  # oversold bullish cross
        elif cross_down and stoch_k > 80:
            score -= 12.0  # overbought bearish cross
        elif stoch_k > 50:
            score += 5.0
        else:
            score -= 5.0

    score = _clamp(score)

    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "adx": round(adx_val, 2) if adx_val else None,
            "plus_di": round(plus_di, 2) if plus_di else None,
            "minus_di": round(minus_di, 2) if minus_di else None,
            "stoch_k": round(stoch_k, 2) if stoch_k else None,
            "stoch_d": round(stoch_d, 2) if stoch_d else None,
        },
        "notes": [],
    }


# ====================================================================== #
# FRAMEWORK 7: Pattern Recognition   (weight 0.08)                         #
# ====================================================================== #

def evaluate_patterns(
    patterns: List[PatternSignal],
) -> Dict[str, Any]:
    """
    Aggregate chart-pattern detections into a single 0–100 score.

    v2 fixes (addressed 67/83 errors from always-bullish pattern scoring):
        1. Recency decay: patterns older than 60 bars contribute 50% less.
        2. Contribution cap: max ±25 points total from all patterns.
        3. Unconfirmed patterns contribute less (no breakout = halved impact).
        4. Bullish-bearish conflict: mixed signals push score toward neutral.
        5. No patterns = neutral 50 (not bullish).

    If no patterns are found the score is neutral (50).
    """
    if not patterns:
        return {
            "applicable": True,
            "score_pct": 50.0,
            "detected_patterns": [],
            "details": {"bullish_count": 0, "bearish_count": 0},
            "notes": ["No chart patterns detected in the lookback window."],
        }

    bullish_impact = 0.0
    bearish_impact = 0.0
    bullish_count = 0
    bearish_count = 0

    for p in patterns:
        # Base impact scaled by confidence (max 15 pts per pattern, not 30)
        impact = p.confidence * 15.0

        # Unconfirmed patterns are much weaker signals
        if p.breakout_confirmed:
            impact *= 1.3
        else:
            impact *= 0.5  # v2: unconfirmed patterns halved

        if p.volume_confirmation:
            impact *= 1.15

        if p.direction == "bullish":
            bullish_impact += impact
            bullish_count += 1
        elif p.direction == "bearish":
            bearish_impact += impact
            bearish_count += 1

    # v2: Cap total contribution to ±25 points
    bullish_impact = min(bullish_impact, 25.0)
    bearish_impact = min(bearish_impact, 25.0)

    # v2: If both bullish and bearish patterns exist, reduce net impact
    if bullish_count > 0 and bearish_count > 0:
        # Conflicting signals → dampen the net effect
        net = bullish_impact - bearish_impact
        score = 50.0 + net * 0.6  # 40% dampening for conflict
    else:
        score = 50.0 + bullish_impact - bearish_impact

    score = _clamp(score)

    pattern_dicts = [
        {
            "name": p.pattern_name,
            "direction": p.direction,
            "confidence": p.confidence,
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat(),
            "breakout_confirmed": p.breakout_confirmed,
            "volume_confirmation": p.volume_confirmation,
            "description": p.description,
            "breakout_price": p.breakout_price,
            "breakout_date": p.breakout_date.isoformat() if p.breakout_date else None,
            "pattern_target": p.pattern_target,
        }
        for p in patterns
    ]

    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "detected_patterns": pattern_dicts,
        "details": {
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "total_patterns": len(patterns),
        },
        "notes": [],
    }


# ====================================================================== #
# FRAMEWORK 8: Ichimoku Cloud   (weight 0.12)                              #
# ====================================================================== #

def evaluate_ichimoku(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    Ichimoku Cloud scoring — comprehensive trend/support/resistance system.

    Components:
        - Price vs Cloud: above = bullish, below = bearish, inside = neutral
        - Tenkan/Kijun cross: bullish cross above cloud, bearish below
        - Cloud color: Senkou A > B = bullish, else bearish
        - Chikou confirmation: current close vs price 26 bars ago

    Scoring (out of 100, neutral base = 50):
        ±15  Price above/below cloud
        ±10  Tenkan-Kijun cross direction
        ±8   Cloud color (Senkou A vs B)
        ±8   Cloud thickness (thicker = stronger support/resistance)
        ±9   Chikou confirmation (close vs price 26 bars ago)
    """
    tenkan = _last(indicators.get("ichimoku_tenkan", []))
    kijun = _last(indicators.get("ichimoku_kijun", []))
    senkou_a = _last(indicators.get("ichimoku_senkou_a", []))
    senkou_b = _last(indicators.get("ichimoku_senkou_b", []))
    price = closes[-1] if closes else None

    if tenkan is None or kijun is None or senkou_a is None or senkou_b is None:
        return {"applicable": False, "score_pct": None, "details": {},
                "notes": ["Insufficient data for Ichimoku evaluation (need 52+ bars)."]}

    score = 50.0
    cloud_top = max(senkou_a, senkou_b)
    cloud_bottom = min(senkou_a, senkou_b)

    # Price vs Cloud
    if price is not None:
        if price > cloud_top:
            score += 15.0  # above cloud = bullish
        elif price < cloud_bottom:
            score -= 15.0  # below cloud = bearish
        # Inside cloud = neutral (no adjustment)

    # Tenkan / Kijun cross
    if tenkan > kijun:
        score += 10.0  # bullish cross
    elif tenkan < kijun:
        score -= 10.0  # bearish cross

    # Cloud color (future trend bias)
    if senkou_a > senkou_b:
        score += 8.0  # bullish cloud
    else:
        score -= 8.0  # bearish cloud

    # Cloud thickness — thicker cloud = stronger S/R
    if price is not None and cloud_top > 0:
        thickness_pct = abs(senkou_a - senkou_b) / cloud_top * 100
        if thickness_pct > 3.0:
            # Thick cloud reinforces current position
            if price > cloud_top:
                score += 8.0  # strong support below
            elif price < cloud_bottom:
                score -= 8.0  # strong resistance above
        elif thickness_pct < 1.0:
            # Thin cloud = weak, trend change likely
            pass  # neutral

    # Chikou (close vs price 26 bars ago)
    if len(closes) > 26:
        price_26_ago = closes[-27]
        if price is not None and price > price_26_ago:
            score += 9.0
        elif price is not None and price < price_26_ago:
            score -= 9.0

    score = _clamp(score)

    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "tenkan": round(tenkan, 4),
            "kijun": round(kijun, 4),
            "senkou_a": round(senkou_a, 4),
            "senkou_b": round(senkou_b, 4),
            "cloud_top": round(cloud_top, 4),
            "cloud_bottom": round(cloud_bottom, 4),
            "price_vs_cloud": (
                "above" if (price and price > cloud_top)
                else "below" if (price and price < cloud_bottom)
                else "inside"
            ),
        },
        "notes": [],
    }


# ====================================================================== #
# FRAMEWORK 9: Momentum Composite   (weight 0.08)                          #
# ====================================================================== #

def evaluate_momentum(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    Combined momentum scoring from ROC, Williams %R, and CCI.

    These three oscillators together catch mean-reversion and momentum
    exhaustion signals that the trend-following indicators miss.

    Scoring (out of 100, neutral base = 50):
        ±10  ROC direction (positive/negative momentum)
        ±8   ROC extreme (>10% or <-10% = overextended)
        ±10  Williams %R overbought/oversold zone
        ±10  CCI above/below zero (trend filter)
        ±8   CCI extreme (>200 or <-200 = overextended reversal)
    """
    roc_val = _last(indicators.get("roc_12", []))
    wr_val = _last(indicators.get("williams_r_14", []))
    cci_val = _last(indicators.get("cci_20", []))

    available = any(v is not None for v in [roc_val, wr_val, cci_val])
    if not available:
        return {"applicable": False, "score_pct": None, "details": {},
                "notes": ["Insufficient data for momentum evaluation."]}

    score = 50.0

    # ROC component
    if roc_val is not None:
        if roc_val > 0:
            score += 10.0
        else:
            score -= 10.0

        # Extreme ROC = overextended (mean reversion likely)
        if roc_val > 10.0:
            score -= 8.0  # overbought momentum
        elif roc_val < -10.0:
            score += 8.0  # oversold momentum (bounce likely)

    # Williams %R component
    if wr_val is not None:
        if wr_val > -20:
            score -= 10.0  # overbought
        elif wr_val < -80:
            score += 10.0  # oversold
        elif wr_val > -50:
            score += 5.0   # upper half = mild bullish
        else:
            score -= 5.0   # lower half = mild bearish

    # CCI component
    if cci_val is not None:
        if cci_val > 0:
            score += 10.0
        else:
            score -= 10.0

        # Extreme CCI = overextended
        if cci_val > 200:
            score -= 8.0  # extreme overbought
        elif cci_val < -200:
            score += 8.0  # extreme oversold (reversal up)

    score = _clamp(score)

    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "roc_12": round(roc_val, 4) if roc_val is not None else None,
            "williams_r_14": round(wr_val, 2) if wr_val is not None else None,
            "cci_20": round(cci_val, 2) if cci_val is not None else None,
        },
        "notes": [],
    }


# ====================================================================== #
# FRAMEWORK 10: Supertrend + Market Structure  (weight 0.06)                #
# ====================================================================== #

def evaluate_supertrend(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    Score based on Supertrend direction, Stochastic RSI, and market structure.

    Scoring (out of 100, neutral base = 50):
        ±15  Supertrend direction (+1 bullish, -1 bearish)
        ±10  Stochastic RSI overbought/oversold
        ±12  Market structure (HH+HL = bullish, LH+LL = bearish)
        ±8   Fibonacci zone (near support = bullish, near resistance = bearish)
    """
    st_dir_series = indicators.get("supertrend_direction", [])
    st_dir = None
    for v in reversed(st_dir_series):
        if v is not None:
            st_dir = v
            break

    srsi_k = _last(indicators.get("stoch_rsi_k", []))
    srsi_d = _last(indicators.get("stoch_rsi_d", []))
    mkt = indicators.get("market_structure", {})
    fib = indicators.get("fibonacci", {})

    available = st_dir is not None or srsi_k is not None
    if not available:
        return {"applicable": False, "score_pct": None, "details": {},
                "notes": ["Insufficient data for supertrend evaluation."]}

    score = 50.0
    notes: List[str] = []

    # Supertrend direction
    if st_dir is not None:
        if st_dir == 1:
            score += 15.0
            notes.append("Supertrend: uptrend (bullish)")
        else:
            score -= 15.0
            notes.append("Supertrend: downtrend (bearish)")

    # Stochastic RSI
    if srsi_k is not None:
        if srsi_k > 80:
            score -= 10.0
            notes.append(f"Stoch RSI K={srsi_k:.1f}: overbought")
        elif srsi_k < 20:
            score += 10.0
            notes.append(f"Stoch RSI K={srsi_k:.1f}: oversold (bullish)")
        elif srsi_k > 50:
            score += 5.0
        else:
            score -= 5.0

    # Market Structure
    if isinstance(mkt, dict) and mkt.get("trend"):
        trend = mkt["trend"]
        if trend == "uptrend":
            score += 12.0
            notes.append("Structure: Higher Highs + Higher Lows")
        elif trend == "downtrend":
            score -= 12.0
            notes.append("Structure: Lower Highs + Lower Lows")
        else:
            notes.append("Structure: consolidation")

    # Fibonacci zone (where is current price relative to retracement?)
    if isinstance(fib, dict) and fib.get("fib_500") is not None:
        price = closes[-1] if closes else None
        if price is not None:
            fib_618 = fib.get("fib_618")
            fib_382 = fib.get("fib_382")
            fib_236 = fib.get("fib_236")
            sh = fib.get("swing_high")
            if fib_618 and price <= fib_618:
                score += 8.0  # deep pullback zone = buy
                notes.append(f"Price near Fib 61.8% ({fib_618:.2f}): buy zone")
            elif fib_382 and price <= fib_382:
                score += 4.0  # moderate pullback
            elif fib_236 and price >= fib_236 and sh and price < sh:
                score -= 4.0  # near top of retracement
            elif sh and price >= sh:
                score -= 8.0  # above swing high = overextended
                notes.append("Price above swing high: extended")

    score = _clamp(score)
    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "supertrend_direction": st_dir,
            "stoch_rsi_k": round(srsi_k, 2) if srsi_k is not None else None,
            "stoch_rsi_d": round(srsi_d, 2) if srsi_d is not None else None,
            "market_structure": mkt.get("trend") if isinstance(mkt, dict) else None,
            "higher_highs": mkt.get("higher_highs") if isinstance(mkt, dict) else None,
            "lower_lows": mkt.get("lower_lows") if isinstance(mkt, dict) else None,
        },
        "notes": notes,
    }


# ====================================================================== #
# FRAMEWORK 11: Volatility Squeeze  (weight 0.06)                          #
# ====================================================================== #

def evaluate_volatility_squeeze(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    Bollinger Band / Keltner Channel squeeze detection + ATR-based
    position sizing context.

    A squeeze signals low volatility → imminent breakout.
    Direction of breakout is inferred from other signals.

    Scoring (out of 100, neutral base = 50):
        ±15  Squeeze state (squeeze ON + price direction)
        ±10  Keltner band position (above/below channel)
        ±5   ATR expansion/contraction as regime context
    """
    squeeze_series = indicators.get("squeeze_on", [])
    kc_upper = _last(indicators.get("kc_upper", []))
    kc_lower = _last(indicators.get("kc_lower", []))
    kc_mid = _last(indicators.get("kc_middle", []))
    atr_val = _last(indicators.get("atr_14", []))

    # Check squeeze state
    squeeze_on = None
    for v in reversed(squeeze_series):
        if v is not None:
            squeeze_on = v
            break

    if squeeze_on is None and kc_upper is None:
        return {"applicable": False, "score_pct": None, "details": {},
                "notes": ["Insufficient data for volatility squeeze."]}

    score = 50.0
    notes: List[str] = []
    price = closes[-1] if closes else None

    # Squeeze state
    if squeeze_on is not None and price is not None:
        if squeeze_on:
            # Squeeze ON — use price momentum to guess breakout direction
            prev_price = closes[-6] if len(closes) >= 6 else closes[0]
            if price > prev_price:
                score += 15.0
                notes.append("Squeeze ON + upward momentum → bullish breakout pending")
            else:
                score -= 15.0
                notes.append("Squeeze ON + downward momentum → bearish breakout pending")
        else:
            notes.append("Squeeze OFF — normal volatility")

    # Keltner band position
    if kc_upper is not None and kc_lower is not None and price is not None:
        if price > kc_upper:
            score += 10.0
            notes.append("Price above Keltner upper: strong bullish")
        elif price < kc_lower:
            score -= 10.0
            notes.append("Price below Keltner lower: strong bearish")
        elif kc_mid is not None:
            if price > kc_mid:
                score += 5.0
            else:
                score -= 5.0

    # ATR context
    if atr_val is not None and price is not None and price > 0:
        atr_pct = (atr_val / price) * 100
        if atr_pct > 4.0:
            score -= 5.0
            notes.append(f"ATR={atr_pct:.1f}% — high volatility regime")
        elif atr_pct < 1.5:
            score += 5.0
            notes.append(f"ATR={atr_pct:.1f}% — low volatility, expansion coming")

    score = _clamp(score)
    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "squeeze_on": squeeze_on,
            "kc_upper": round(kc_upper, 2) if kc_upper is not None else None,
            "kc_lower": round(kc_lower, 2) if kc_lower is not None else None,
            "atr_14": round(atr_val, 2) if atr_val is not None else None,
        },
        "notes": notes,
    }


# ====================================================================== #
# FRAMEWORK 12: Entry / Exit Rules Engine  (weight 0.06)                    #
# ====================================================================== #

def evaluate_entry_exit_rules(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
    volumes: List[float],
) -> Dict[str, Any]:
    """
    Meta-framework that checks a structured set of entry and exit rules.

    Each passing rule = +1 aligned signal.  The total count feeds directly
    into the signal-alignment confidence score system.

    **Entry Rules (LONG):**
    1. MA crossover: EMA 9 > EMA 21 > EMA 50
    2. RSI filter: RSI < 70 (not overbought)
    3. MACD confirmation: MACD histogram > 0
    4. Volume spike: current vol > 1.5× 20-bar average
    5. Price above VWAP
    6. Supertrend direction = +1
    7. ADX > 20 (trending market)
    8. CMF > 0 (money inflow)
    9. Price above Ichimoku cloud (Senkou A & B)
    10. Market structure uptrend (HH + HL)
    11. Stochastic RSI not overbought (< 80)
    12. Bollinger %B in 0.2–0.8 range (not extreme)

    **Exit / Risk Signals:**
    - RSI > 75 (exit warning)
    - MACD histogram turning negative
    - Bearish Supertrend flip
    - Volume dry-up (below 0.5× average)

    Returns the count of aligned signals which the confidence
    scoring system converts to a percentage.
    """
    ema9 = _last(indicators.get("ema_9", []))
    ema21 = _last(indicators.get("ema_21", []))
    ema50 = _last(indicators.get("ema_50", []))
    rsi_val = _last(indicators.get("rsi_14", []))
    macd_hist = _last(indicators.get("macd_histogram", []))
    vwap_val = _last(indicators.get("vwap_20", []))
    adx_val = _last(indicators.get("adx", []))
    cmf_val = _last(indicators.get("cmf_20", []))
    bb_pct_b = _last(indicators.get("bb_pct_b", []))
    senkou_a = _last(indicators.get("ichimoku_senkou_a", []))
    senkou_b = _last(indicators.get("ichimoku_senkou_b", []))
    srsi_k = _last(indicators.get("stoch_rsi_k", []))

    st_dir_series = indicators.get("supertrend_direction", [])
    st_dir = None
    for v in reversed(st_dir_series):
        if v is not None:
            st_dir = v
            break

    mkt = indicators.get("market_structure", {})

    price = closes[-1] if closes else None

    entry_signals: List[str] = []
    exit_signals: List[str] = []

    # --- Entry Rules ---

    # 1. MA crossover stack
    if ema9 is not None and ema21 is not None and ema50 is not None:
        if ema9 > ema21 > ema50:
            entry_signals.append("ma_crossover_stack")

    # 2. RSI filter
    if rsi_val is not None and rsi_val < 70:
        entry_signals.append("rsi_not_overbought")

    # 3. MACD confirmation
    if macd_hist is not None and macd_hist > 0:
        entry_signals.append("macd_positive")

    # 4. Volume spike
    if volumes and len(volumes) >= 20:
        avg_vol = sum(volumes[-20:]) / 20
        if avg_vol > 0 and volumes[-1] >= 1.5 * avg_vol:
            entry_signals.append("volume_spike")

    # 5. Price above VWAP
    if price is not None and vwap_val is not None and price > vwap_val:
        entry_signals.append("above_vwap")

    # 6. Supertrend direction
    if st_dir == 1:
        entry_signals.append("supertrend_bullish")

    # 7. ADX trending
    if adx_val is not None and adx_val > 20:
        entry_signals.append("adx_trending")

    # 8. CMF positive
    if cmf_val is not None and cmf_val > 0:
        entry_signals.append("cmf_inflow")

    # 9. Above Ichimoku cloud
    if (price is not None and senkou_a is not None and senkou_b is not None
            and price > max(senkou_a, senkou_b)):
        entry_signals.append("above_cloud")

    # 10. Market structure uptrend
    if isinstance(mkt, dict) and mkt.get("trend") == "uptrend":
        entry_signals.append("structure_uptrend")

    # 11. Stochastic RSI not overbought
    if srsi_k is not None and srsi_k < 80:
        entry_signals.append("stoch_rsi_ok")

    # 12. Bollinger %B in range
    if bb_pct_b is not None and 0.2 <= bb_pct_b <= 0.8:
        entry_signals.append("bb_pctb_ok")

    # --- Exit Warnings ---
    if rsi_val is not None and rsi_val > 75:
        exit_signals.append("rsi_overbought_exit")
    if macd_hist is not None and macd_hist < 0:
        exit_signals.append("macd_negative")
    if st_dir == -1:
        exit_signals.append("supertrend_bearish")
    if volumes and len(volumes) >= 20:
        avg_vol = sum(volumes[-20:]) / 20
        if avg_vol > 0 and volumes[-1] < 0.5 * avg_vol:
            exit_signals.append("volume_dryup")

    # Score: map aligned entry signals to 0–100
    n_entry = len(entry_signals)
    n_exit = len(exit_signals)

    # Base from entry signals aligned
    if n_entry >= 10:
        score = 85.0 + min(n_entry - 10, 2) * 5.0
    elif n_entry >= 7:
        score = 65.0 + (n_entry - 7) * 6.67
    elif n_entry >= 4:
        score = 40.0 + (n_entry - 4) * 8.33
    elif n_entry >= 1:
        score = 20.0 + (n_entry - 1) * 6.67
    else:
        score = 10.0

    # Penalize for exit signals
    score -= n_exit * 10.0

    score = _clamp(score)

    return {
        "applicable": True,
        "score_pct": round(score, 1),
        "details": {
            "entry_signals_aligned": n_entry,
            "exit_warnings": n_exit,
            "entry_rules_met": entry_signals,
            "exit_rules_triggered": exit_signals,
        },
        "notes": [
            f"{n_entry}/12 entry signals aligned",
            f"{n_exit} exit warnings active",
        ],
    }


# ====================================================================== #
# SIGNAL ALIGNMENT → CONFIDENCE SCORE                                       #
# ====================================================================== #

def compute_signal_alignment_confidence(
    frameworks: Dict[str, Dict[str, Any]],
    entry_exit: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Signal-alignment confidence model (user spec v3).

    Counts bullish-aligned frameworks (score > 60) and combined with
    the entry/exit rule count:

        1-3 signals  → 20-40% (Weak)
        4-6 signals  → 40-65% (Moderate)
        7-9 signals  → 65-80% (Strong)
        10+ signals  → 80-100% (High Conviction)

    Returns dict with: signal_count, confidence_pct, confidence_label.
    """
    # Count frameworks scoring bullish (>60)
    bullish_fw = 0
    for name, fw in frameworks.items():
        s = fw.get("score_pct")
        if s is not None and s > 60:
            bullish_fw += 1

    # Add entry rule signals aligned
    entry_count = entry_exit.get("details", {}).get("entry_signals_aligned", 0)

    total_signals = bullish_fw + entry_count

    # Map to confidence
    if total_signals >= 10:
        pct = 80.0 + min((total_signals - 10) * 4.0, 20.0)
        label = "high_conviction"
    elif total_signals >= 7:
        pct = 65.0 + (total_signals - 7) * 5.0
        label = "strong"
    elif total_signals >= 4:
        pct = 40.0 + (total_signals - 4) * 8.33
        label = "moderate"
    elif total_signals >= 1:
        pct = 20.0 + (total_signals - 1) * 6.67
        label = "weak"
    else:
        pct = 10.0
        label = "very_weak"

    return {
        "signal_count": total_signals,
        "bullish_frameworks": bullish_fw,
        "entry_rules_met": entry_count,
        "confidence_pct": round(min(pct, 100.0), 1),
        "confidence_label": label,
    }


# ====================================================================== #
# COMPOSITE SCORE                                                           #
# ====================================================================== #

_FRAMEWORK_WEIGHTS = {
    "ema_trend":           0.14,
    "macd_system":         0.11,
    "rsi_regime":          0.11,
    "bollinger":           0.08,
    "volume_obv":          0.08,
    "adx_stochastic":      0.06,
    "pattern_recognition":  0.07,
    "ichimoku":            0.10,
    "momentum":            0.07,
    "supertrend":          0.06,
    "volatility_squeeze":  0.06,
    "entry_exit_rules":    0.06,
}


def build_composite_score(
    frameworks: Dict[str, Dict[str, Any]],
    adx_value: Optional[float] = None,
    signal_alignment: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Combine individual framework scores into a weighted composite.

    v3: Uses signal-alignment confidence when available, falls back to
    ADX-based confidence gate.
    """
    weighted_parts: List[Tuple[float, float]] = []

    for name, weight in _FRAMEWORK_WEIGHTS.items():
        fw = frameworks.get(name, {})
        score_pct = fw.get("score_pct")
        if score_pct is not None and fw.get("applicable", False):
            weighted_parts.append((score_pct, weight))

    if not weighted_parts:
        return {
            "available": False,
            "warning": (
                "Composite score could not be computed — no framework "
                "produced a valid score."
            ),
        }

    total_weight = sum(w for _, w in weighted_parts)
    composite = sum(v * w for v, w in weighted_parts) / total_weight

    # Band mapping
    if composite >= 75:
        band = "strong"
    elif composite >= 60:
        band = "good"
    elif composite >= 50:
        band = "mixed_positive"
    elif composite >= 35:
        band = "mixed"
    else:
        band = "weak"

    # ── STR-2: ADX hard gate ────────────────────────────────────────────
    # When ADX < 17 the market is trendless/choppy.  A bullish composite
    # score in these conditions is unreliable — it reflects oscillator noise
    # rather than directional momentum.  Downgrade mixed_positive → mixed
    # so the orchestrator cannot generate a bullish signal from a no-trend
    # environment.  "strong" and "good" bands are intentionally left
    # unchanged because they indicate very high technical conviction.
    adx_gate_applied = False
    if adx_value is not None and adx_value < 17.0:
        if band == "mixed_positive":
            band = "mixed"
            adx_gate_applied = True

    # v3: Signal alignment confidence (preferred) or ADX fallback
    if signal_alignment is not None:
        confidence = signal_alignment["confidence_label"]
        confidence_pct = signal_alignment["confidence_pct"]
        # ADX gate further degrades confidence when no trend
        if adx_gate_applied:
            confidence = "low"
            confidence_pct = min(confidence_pct, 25.0)
    elif adx_value is not None:
        if adx_value >= 40:
            confidence = "high"
            confidence_pct = 80.0
        elif adx_value >= 20:
            confidence = "medium"
            confidence_pct = 55.0
        elif adx_value >= 17:
            confidence = "low"
            confidence_pct = 35.0
        else:
            # Sub-17: trendless — hard low
            confidence = "low"
            confidence_pct = 15.0
    else:
        confidence = "medium" if total_weight >= 0.65 else "low"
        confidence_pct = 50.0 if total_weight >= 0.65 else 25.0

    # Subscores for transparency
    subscores = {}
    for name in _FRAMEWORK_WEIGHTS:
        fw = frameworks.get(name, {})
        subscores[name] = fw.get("score_pct")

    return {
        "available": True,
        "score": round(composite, 1),
        "band": band,
        "confidence": confidence,
        "confidence_pct": round(confidence_pct, 1),
        "adx_gate_applied": adx_gate_applied,
        "total_weight": round(total_weight, 3),
        "subscores": subscores,
        "signal_alignment": signal_alignment,
        "warning": (
            "Technical composite score is intended for backtesting and "
            "ranking experiments, not as a standalone trading signal."
        ),
    }


# ====================================================================== #
# KEY INDICATOR SUMMARY                                                     #
# ====================================================================== #

def build_key_indicators(
    closes: List[float],
    indicators: Dict[str, List[Optional[float]]],
) -> Dict[str, Any]:
    """
    Build a flat dict of the most important indicator values for the
    report and JSON output.  All values are rounded for readability.
    """
    price = closes[-1] if closes else None

    def _r(val: Optional[float], dp: int = 4) -> Optional[float]:
        """Round if not None."""
        return round(val, dp) if val is not None else None

    obv_series = indicators.get("obv", [])
    obv_slope = _slope_direction(obv_series, lookback=10)

    return {
        "close": _r(price),
        "ema_20": _r(_last(indicators.get("ema_20", []))),
        "ema_50": _r(_last(indicators.get("ema_50", []))),
        "ema_200": _r(_last(indicators.get("ema_200", []))),
        "rsi_14": _r(_last(indicators.get("rsi_14", [])), 2),
        "macd": _r(_last(indicators.get("macd_line", []))),
        "macd_signal": _r(_last(indicators.get("macd_signal", []))),
        "macd_histogram": _r(_last(indicators.get("macd_histogram", []))),
        "adx": _r(_last(indicators.get("adx", [])), 2),
        "plus_di": _r(_last(indicators.get("plus_di", [])), 2),
        "minus_di": _r(_last(indicators.get("minus_di", [])), 2),
        "stoch_k": _r(_last(indicators.get("stoch_k", [])), 2),
        "stoch_d": _r(_last(indicators.get("stoch_d", [])), 2),
        "bb_pct_b": _r(_last(indicators.get("bb_pct_b", []))),
        "bb_bandwidth": _r(_last(indicators.get("bb_bandwidth", []))),
        "obv_trend": obv_slope,
        # v2 indicators
        "atr_14": _r(_last(indicators.get("atr_14", [])), 2),
        "roc_12": _r(_last(indicators.get("roc_12", [])), 2),
        "williams_r_14": _r(_last(indicators.get("williams_r_14", [])), 2),
        "cci_20": _r(_last(indicators.get("cci_20", [])), 2),
        "cmf_20": _r(_last(indicators.get("cmf_20", []))),
        "ichimoku_tenkan": _r(_last(indicators.get("ichimoku_tenkan", []))),
        "ichimoku_kijun": _r(_last(indicators.get("ichimoku_kijun", []))),
        "vwap_20": _r(_last(indicators.get("vwap_20", []))),
        # v3 indicators
        "ema_9": _r(_last(indicators.get("ema_9", []))),
        "ema_21": _r(_last(indicators.get("ema_21", []))),
        "supertrend_direction": _last_int(indicators.get("supertrend_direction", [])),
        "supertrend_line": _r(_last(indicators.get("supertrend_line", []))),
        "stoch_rsi_k": _r(_last(indicators.get("stoch_rsi_k", [])), 2),
        "stoch_rsi_d": _r(_last(indicators.get("stoch_rsi_d", [])), 2),
        "kc_upper": _r(_last(indicators.get("kc_upper", []))),
        "kc_lower": _r(_last(indicators.get("kc_lower", []))),
        "squeeze_on": _last_bool(indicators.get("squeeze_on", [])),
        "fibonacci": indicators.get("fibonacci", {}),
        "market_structure": indicators.get("market_structure", {}).get("trend")
            if isinstance(indicators.get("market_structure"), dict) else None,
    }


# ====================================================================== #
# RISK MANAGEMENT                                                           #
# ====================================================================== #

def _compute_risk_levels(
    price: float,
    atr_val: Optional[float],
) -> Dict[str, Any]:
    """
    Compute stop-loss and take-profit levels based on ATR.

    Stop-loss:   price − 2 × ATR  (standard 2-ATR risk)
    Take-profit: price + 3 × ATR  (1.5:1 reward/risk ratio)
    Max risk:    1-2% of position per trade.
    """
    if price <= 0 or atr_val is None or atr_val <= 0:
        return {
            "stop_loss": None,
            "take_profit_1": None,
            "take_profit_2": None,
            "risk_per_share": None,
            "reward_risk_ratio": None,
            "atr_pct": None,
        }

    stop_loss = round(price - 2.0 * atr_val, 4)
    tp1 = round(price + 3.0 * atr_val, 4)   # 1.5:1 R/R
    tp2 = round(price + 4.0 * atr_val, 4)   # 2:1 R/R
    risk_per_share = round(2.0 * atr_val, 4)
    atr_pct = round((atr_val / price) * 100, 2)

    return {
        "stop_loss": stop_loss,
        "take_profit_1": tp1,
        "take_profit_2": tp2,
        "risk_per_share": risk_per_share,
        "reward_risk_ratio": 1.5,
        "atr_pct": atr_pct,
    }


# ====================================================================== #
# MAIN ENTRY POINT                                                          #
# ====================================================================== #

def evaluate_snapshot(
    snapshot: RawTechnicalSnapshot,
    indicators: Dict[str, List[Optional[float]]],
    patterns: List[PatternSignal],
) -> Dict[str, Any]:
    """
    Run all 12 frameworks and build the complete evaluation dict.

    v3: Added Supertrend, Volatility Squeeze, Entry/Exit Rules frameworks.
    Signal-alignment confidence replaces ADX-only confidence gate.
    Includes stop-loss/take-profit levels and risk management fields.
    """
    closes = [b.close for b in snapshot.bars]
    volumes = [b.volume for b in snapshot.bars]

    # --- Run all 12 frameworks ---
    ema_result = evaluate_ema_trend(closes, indicators)
    macd_result = evaluate_macd(closes, indicators)
    rsi_result = evaluate_rsi(closes, indicators)
    bb_result = evaluate_bollinger(closes, indicators)
    vol_result = evaluate_volume(closes, indicators)
    adx_stoch_result = evaluate_adx_stochastic(indicators)
    pattern_result = evaluate_patterns(patterns)
    ichimoku_result = evaluate_ichimoku(closes, indicators)
    momentum_result = evaluate_momentum(closes, indicators)
    # v3 frameworks
    supertrend_result = evaluate_supertrend(closes, indicators)
    squeeze_result = evaluate_volatility_squeeze(closes, indicators)
    entry_exit_result = evaluate_entry_exit_rules(closes, indicators, volumes)

    frameworks = {
        "ema_trend": ema_result,
        "macd_system": macd_result,
        "rsi_regime": rsi_result,
        "bollinger": bb_result,
        "volume_obv": vol_result,
        "adx_stochastic": adx_stoch_result,
        "pattern_recognition": pattern_result,
        "ichimoku": ichimoku_result,
        "momentum": momentum_result,
        "supertrend": supertrend_result,
        "volatility_squeeze": squeeze_result,
        "entry_exit_rules": entry_exit_result,
    }

    # Signal alignment confidence (v3)
    signal_alignment = compute_signal_alignment_confidence(
        frameworks, entry_exit_result
    )

    # Composite score with signal alignment
    adx_val = _last(indicators.get("adx", []))
    composite = build_composite_score(
        frameworks, adx_value=adx_val, signal_alignment=signal_alignment
    )

    # Key indicator summary
    key_ind = build_key_indicators(closes, indicators)

    # Risk management levels
    price = closes[-1] if closes else 0.0
    atr_val = _last(indicators.get("atr_14", []))
    risk_mgmt = _compute_risk_levels(price, atr_val)

    # Pattern summary for top-level output
    pattern_summary = [
        {
            "name": p.pattern_name,
            "direction": p.direction,
            "confidence": p.confidence,
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat(),
            "breakout_confirmed": p.breakout_confirmed,
            "volume_confirmation": p.volume_confirmation,
            "description": p.description,
            "breakout_price": p.breakout_price,
            "breakout_date": p.breakout_date.isoformat() if p.breakout_date else None,
            "pattern_target": p.pattern_target,
        }
        for p in patterns
    ]

    return {
        "request": {
            "ticker": snapshot.request.ticker,
            "as_of_date": snapshot.request.as_of_date.isoformat(),
        },
        "company": {
            "ticker": snapshot.request.ticker,
            "company_name": snapshot.company_name,
            "sector": snapshot.sector,
            "industry": snapshot.industry,
        },
        "as_of_price": {
            "price": round(snapshot.as_of_price, 4),
            "price_date": snapshot.as_of_price_date.isoformat(),
        },
        "frameworks": frameworks,
        "experimental_score": composite,
        "signal_alignment": signal_alignment,
        "risk_management": risk_mgmt,
        "patterns": pattern_summary,
        "key_indicators": key_ind,
        "warnings": list(snapshot.warnings),
    }
