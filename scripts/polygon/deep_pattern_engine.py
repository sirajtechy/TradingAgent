"""
deep_pattern_engine.py — Deep pattern recognition beyond standard candlestick/chart patterns.

Goes beyond the 22 candlestick + 10 chart patterns in polygon_kgc_patterns.py.
Adds: volume profile, momentum divergences, volatility regime, mean reversion,
gap analysis, trend strength, exhaustion signals, institutional footprints,
range contraction/expansion, and multi-timeframe confluence scoring.

All patterns return trade-actionable signals with confidence scores.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))

def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0
    atr = _atr(df, period)
    plus_di = 100 * _ema(plus_dm, period) / atr.replace(0, 1e-10)
    minus_di = 100 * _ema(minus_dm, period) / atr.replace(0, 1e-10)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-10)
    return _ema(dx, period)

def _bbands(series: pd.Series, window: int = 20, std: float = 2.0):
    mid = _sma(series, window)
    sd = series.rolling(window).std()
    return mid, mid + std * sd, mid - std * sd

def _stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3):
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, 1e-10)
    d = k.rolling(d_period).mean()
    return k, d


# ═════════════════════════════════════════════════════════════════════════════
# 1. VOLUME PROFILE ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════

def analyze_volume_profile(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Volume-weighted price distribution: POC, value area, volume anomalies."""
    signals = []
    if len(df) < 30:
        return signals

    c, v = df["close"].values, df["volume"].values
    avg_vol = np.mean(v[-20:])

    # Point of Control (POC) — price with most volume in last 60 bars
    lb = min(60, len(df))
    prices = c[-lb:]
    volumes = v[-lb:]
    bins = np.linspace(prices.min(), prices.max(), 30)
    vol_hist = np.zeros(len(bins) - 1)
    for p, vl in zip(prices, volumes):
        idx = np.searchsorted(bins, p) - 1
        idx = max(0, min(idx, len(vol_hist) - 1))
        vol_hist[idx] += vl

    poc_idx = np.argmax(vol_hist)
    poc_price = (bins[poc_idx] + bins[poc_idx + 1]) / 2

    # Value area (70% of volume)
    total_vol = vol_hist.sum()
    sorted_idx = np.argsort(vol_hist)[::-1]
    cum_vol = 0
    va_indices = []
    for idx in sorted_idx:
        cum_vol += vol_hist[idx]
        va_indices.append(idx)
        if cum_vol >= 0.7 * total_vol:
            break
    va_low = bins[min(va_indices)]
    va_high = bins[max(va_indices) + 1]

    last = c[-1]
    if last < va_low:
        signals.append({
            "pattern": "Below Value Area",
            "signal": "bearish",
            "confidence": 0.65,
            "desc": f"Price ${last:.2f} below value area ${va_low:.2f}-${va_high:.2f}. POC=${poc_price:.2f}",
            "category": "volume_profile",
        })
    elif last > va_high:
        signals.append({
            "pattern": "Above Value Area",
            "signal": "bullish",
            "confidence": 0.65,
            "desc": f"Price ${last:.2f} above value area ${va_low:.2f}-${va_high:.2f}. POC=${poc_price:.2f}",
            "category": "volume_profile",
        })

    # Volume climax detection (3x average on reversal candle)
    for i in range(-5, 0):
        if v[i] > 3 * avg_vol:
            change_pct = (c[i] - c[i-1]) / c[i-1] * 100
            if change_pct < -2:
                signals.append({
                    "pattern": "Selling Climax",
                    "signal": "bullish",
                    "confidence": 0.70,
                    "desc": f"Volume climax ({v[i]/avg_vol:.1f}x avg) with {change_pct:.1f}% drop — potential exhaustion",
                    "category": "volume_profile",
                })
            elif change_pct > 2:
                signals.append({
                    "pattern": "Buying Climax",
                    "signal": "bearish",
                    "confidence": 0.60,
                    "desc": f"Volume climax ({v[i]/avg_vol:.1f}x avg) with +{change_pct:.1f}% surge — potential blowoff",
                    "category": "volume_profile",
                })

    # Volume dry-up (base building)
    recent_vol = np.mean(v[-5:])
    if recent_vol < 0.5 * avg_vol and c[-1] > c[-10]:
        signals.append({
            "pattern": "Low Volume Advance",
            "signal": "neutral",
            "confidence": 0.55,
            "desc": f"Volume drying up ({recent_vol/avg_vol:.1%} of avg) during advance — watch for breakout or fail",
            "category": "volume_profile",
        })

    return signals


# ═════════════════════════════════════════════════════════════════════════════
# 2. MOMENTUM DIVERGENCES
# ═════════════════════════════════════════════════════════════════════════════

def detect_divergences(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """RSI and MACD divergences — price vs momentum disagreement."""
    signals = []
    if len(df) < 50:
        return signals

    c = df["close"]
    rsi = _rsi(c, 14).values
    macd_line = (_ema(c, 12) - _ema(c, 26)).values

    # Scan last 30 bars for swing highs/lows
    lb = 30
    n = len(df)

    # Find local highs and lows in close price
    for lookback in [lb]:
        start = n - lookback
        prices = c.values[start:]
        rsi_vals = rsi[start:]
        macd_vals = macd_line[start:]

        # Find swing highs (local maxima)
        swing_highs = []
        swing_lows = []
        for i in range(2, len(prices) - 2):
            if prices[i] > prices[i-1] and prices[i] > prices[i-2] and prices[i] > prices[i+1] and prices[i] > prices[i+2]:
                swing_highs.append(i)
            if prices[i] < prices[i-1] and prices[i] < prices[i-2] and prices[i] < prices[i+1] and prices[i] < prices[i+2]:
                swing_lows.append(i)

        # Bearish divergence: higher high in price, lower high in RSI
        if len(swing_highs) >= 2:
            a, b = swing_highs[-2], swing_highs[-1]
            if prices[b] > prices[a] and rsi_vals[b] < rsi_vals[a]:
                signals.append({
                    "pattern": "Bearish RSI Divergence",
                    "signal": "bearish",
                    "confidence": 0.72,
                    "desc": f"Price made higher high but RSI made lower high ({rsi_vals[b]:.0f} vs {rsi_vals[a]:.0f})",
                    "category": "divergence",
                })
            if prices[b] > prices[a] and macd_vals[b] < macd_vals[a]:
                signals.append({
                    "pattern": "Bearish MACD Divergence",
                    "signal": "bearish",
                    "confidence": 0.70,
                    "desc": f"Price made higher high but MACD made lower high — momentum fading",
                    "category": "divergence",
                })

        # Bullish divergence: lower low in price, higher low in RSI
        if len(swing_lows) >= 2:
            a, b = swing_lows[-2], swing_lows[-1]
            if prices[b] < prices[a] and rsi_vals[b] > rsi_vals[a]:
                signals.append({
                    "pattern": "Bullish RSI Divergence",
                    "signal": "bullish",
                    "confidence": 0.72,
                    "desc": f"Price made lower low but RSI made higher low ({rsi_vals[b]:.0f} vs {rsi_vals[a]:.0f})",
                    "category": "divergence",
                })
            if prices[b] < prices[a] and macd_vals[b] > macd_vals[a]:
                signals.append({
                    "pattern": "Bullish MACD Divergence",
                    "signal": "bullish",
                    "confidence": 0.70,
                    "desc": f"Price made lower low but MACD made higher low — selling pressure fading",
                    "category": "divergence",
                })

    return signals


# ═════════════════════════════════════════════════════════════════════════════
# 3. VOLATILITY REGIME DETECTION
# ═════════════════════════════════════════════════════════════════════════════

def analyze_volatility_regime(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect volatility contractions/expansions using ATR and Bollinger Band width."""
    signals = []
    if len(df) < 50:
        return signals

    c = df["close"]
    atr = _atr(df, 14).values
    _, upper, lower = _bbands(c, 20, 2.0)
    bb_width = ((upper - lower) / c * 100).values

    # Bollinger squeeze (lowest 20-period BB width)
    current_bbw = bb_width[-1]
    min_bbw_20 = np.nanmin(bb_width[-20:])
    avg_bbw = np.nanmean(bb_width[-60:]) if len(bb_width) >= 60 else np.nanmean(bb_width)

    if current_bbw <= min_bbw_20 * 1.05 and current_bbw < avg_bbw * 0.6:
        signals.append({
            "pattern": "Bollinger Squeeze",
            "signal": "neutral",
            "confidence": 0.75,
            "desc": f"BB width at {current_bbw:.2f}% — lowest in 20 bars (avg: {avg_bbw:.2f}%). Breakout imminent.",
            "category": "volatility",
        })

    # ATR expansion (volatility spike)
    current_atr = atr[-1]
    avg_atr = np.mean(atr[-20:])
    if current_atr > 1.5 * avg_atr:
        signals.append({
            "pattern": "Volatility Expansion",
            "signal": "neutral",
            "confidence": 0.60,
            "desc": f"ATR ${current_atr:.2f} is {current_atr/avg_atr:.1f}x 20-bar avg — increased volatility",
            "category": "volatility",
        })

    # ATR contraction (pre-breakout)
    if current_atr < 0.6 * avg_atr:
        signals.append({
            "pattern": "Volatility Contraction",
            "signal": "neutral",
            "confidence": 0.70,
            "desc": f"ATR ${current_atr:.2f} is {current_atr/avg_atr:.1%} of avg — range contraction, breakout setup",
            "category": "volatility",
        })

    return signals


# ═════════════════════════════════════════════════════════════════════════════
# 4. GAP ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════

def detect_gaps(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Identify unfilled gaps and gap-and-go setups."""
    signals = []
    if len(df) < 20:
        return signals

    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    dates = df["date"].values

    # Scan last 20 bars for gaps
    for i in range(-20, 0):
        if i == -len(df):
            break

        gap_up = o[i] > h[i-1]  # open above prior high
        gap_down = o[i] < l[i-1]  # open below prior low

        if gap_up:
            gap_size_pct = (o[i] - h[i-1]) / h[i-1] * 100
            if gap_size_pct >= 1.0:
                # Check if gap is still unfilled
                filled = any(l[j] <= h[i-1] for j in range(i+1 if i+1 < 0 else len(df), 0))
                status = "filled" if filled else "unfilled"
                if not filled and i >= -5:
                    signals.append({
                        "pattern": f"Gap Up ({status})",
                        "signal": "bullish",
                        "confidence": 0.65 if not filled else 0.50,
                        "desc": f"{dates[i]}: +{gap_size_pct:.1f}% gap up from ${h[i-1]:.2f} to ${o[i]:.2f} — {status}",
                        "category": "gap",
                    })

        if gap_down:
            gap_size_pct = (l[i-1] - o[i]) / l[i-1] * 100
            if gap_size_pct >= 1.0:
                filled = any(h[j] >= l[i-1] for j in range(i+1 if i+1 < 0 else len(df), 0))
                status = "filled" if filled else "unfilled"
                if not filled and i >= -5:
                    signals.append({
                        "pattern": f"Gap Down ({status})",
                        "signal": "bearish",
                        "confidence": 0.65 if not filled else 0.50,
                        "desc": f"{dates[i]}: -{gap_size_pct:.1f}% gap down from ${l[i-1]:.2f} to ${o[i]:.2f} — {status}",
                        "category": "gap",
                    })

    return signals


# ═════════════════════════════════════════════════════════════════════════════
# 5. MEAN REVERSION SIGNALS
# ═════════════════════════════════════════════════════════════════════════════

def detect_mean_reversion(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Overextension from moving averages — rubber-band snapback setups."""
    signals = []
    if len(df) < 50:
        return signals

    c = df["close"]
    sma20 = _sma(c, 20).values
    sma50 = _sma(c, 50).values
    last = c.values[-1]

    # Distance from SMA20
    if not np.isnan(sma20[-1]):
        dist_20 = (last - sma20[-1]) / sma20[-1] * 100
        if dist_20 > 8:
            signals.append({
                "pattern": "Overextended Above SMA20",
                "signal": "bearish",
                "confidence": 0.65,
                "desc": f"Price {dist_20:+.1f}% above SMA20 (${sma20[-1]:.2f}) — mean reversion pullback likely",
                "category": "mean_reversion",
            })
        elif dist_20 < -8:
            signals.append({
                "pattern": "Overextended Below SMA20",
                "signal": "bullish",
                "confidence": 0.65,
                "desc": f"Price {dist_20:+.1f}% below SMA20 (${sma20[-1]:.2f}) — mean reversion bounce likely",
                "category": "mean_reversion",
            })

    # Distance from SMA50
    if not np.isnan(sma50[-1]):
        dist_50 = (last - sma50[-1]) / sma50[-1] * 100
        if dist_50 > 15:
            signals.append({
                "pattern": "Overextended Above SMA50",
                "signal": "bearish",
                "confidence": 0.70,
                "desc": f"Price {dist_50:+.1f}% above SMA50 (${sma50[-1]:.2f}) — extended, pullback risk high",
                "category": "mean_reversion",
            })
        elif dist_50 < -15:
            signals.append({
                "pattern": "Overextended Below SMA50",
                "signal": "bullish",
                "confidence": 0.70,
                "desc": f"Price {dist_50:+.1f}% below SMA50 (${sma50[-1]:.2f}) — oversold, bounce candidate",
                "category": "mean_reversion",
            })

    return signals


# ═════════════════════════════════════════════════════════════════════════════
# 6. TREND STRENGTH + EXHAUSTION
# ═════════════════════════════════════════════════════════════════════════════

def analyze_trend_exhaustion(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """ADX trend strength, consecutive candle streaks, momentum deceleration."""
    signals = []
    if len(df) < 30:
        return signals

    c = df["close"].values
    adx = _adx(df, 14).values
    rsi = _rsi(df["close"], 14).values

    # ADX trend strength
    current_adx = adx[-1]
    if not np.isnan(current_adx):
        if current_adx > 40:
            signals.append({
                "pattern": "Strong Trend (ADX>40)",
                "signal": "neutral",
                "confidence": 0.60,
                "desc": f"ADX={current_adx:.0f} — very strong trend, potential exhaustion if overbought",
                "category": "trend",
            })
        elif current_adx < 15:
            signals.append({
                "pattern": "No Trend (ADX<15)",
                "signal": "neutral",
                "confidence": 0.55,
                "desc": f"ADX={current_adx:.0f} — trendless market, range-bound trading expected",
                "category": "trend",
            })

    # Consecutive candle streaks
    streak = 0
    direction = "up" if c[-1] > c[-2] else "down"
    for i in range(-1, -min(15, len(df)), -1):
        if direction == "up" and c[i] > c[i-1]:
            streak += 1
        elif direction == "down" and c[i] < c[i-1]:
            streak += 1
        else:
            break

    if streak >= 5:
        sig = "bearish" if direction == "up" else "bullish"
        signals.append({
            "pattern": f"{streak}-Bar {'Up' if direction=='up' else 'Down'} Streak",
            "signal": sig,
            "confidence": 0.60 + min(streak - 5, 3) * 0.05,
            "desc": f"{streak} consecutive {'up' if direction=='up' else 'down'} bars — exhaustion likely",
            "category": "trend",
        })

    # RSI extreme zones
    if rsi[-1] > 80:
        signals.append({
            "pattern": "RSI Extreme Overbought",
            "signal": "bearish",
            "confidence": 0.68,
            "desc": f"RSI={rsi[-1]:.0f} — severely overbought, reversal risk elevated",
            "category": "trend",
        })
    elif rsi[-1] < 20:
        signals.append({
            "pattern": "RSI Extreme Oversold",
            "signal": "bullish",
            "confidence": 0.68,
            "desc": f"RSI={rsi[-1]:.0f} — severely oversold, bounce candidate",
            "category": "trend",
        })

    # Stochastic extremes
    k, d = _stochastic(df)
    k_val, d_val = k.values[-1], d.values[-1]
    if not np.isnan(k_val):
        if k_val > 90 and d_val > 80:
            signals.append({
                "pattern": "Stochastic Overbought",
                "signal": "bearish",
                "confidence": 0.60,
                "desc": f"Stoch K={k_val:.0f}, D={d_val:.0f} — overbought territory",
                "category": "trend",
            })
        elif k_val < 10 and d_val < 20:
            signals.append({
                "pattern": "Stochastic Oversold",
                "signal": "bullish",
                "confidence": 0.60,
                "desc": f"Stoch K={k_val:.0f}, D={d_val:.0f} — oversold territory",
                "category": "trend",
            })

    return signals


# ═════════════════════════════════════════════════════════════════════════════
# 7. INSTITUTIONAL FOOTPRINT (VOLUME-PRICE ANALYSIS)
# ═════════════════════════════════════════════════════════════════════════════

def detect_institutional_activity(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect likely institutional accumulation or distribution."""
    signals = []
    if len(df) < 30:
        return signals

    c, v, o = df["close"].values, df["volume"].values, df["open"].values
    h, l = df["high"].values, df["low"].values
    avg_vol = np.mean(v[-20:])

    # Accumulation: narrow range, high volume, close near high (on down days)
    acc_count = 0
    dist_count = 0
    for i in range(-10, 0):
        rng = h[i] - l[i]
        if rng == 0:
            continue
        close_pos = (c[i] - l[i]) / rng  # 0=close at low, 1=close at high
        vol_ratio = v[i] / avg_vol if avg_vol > 0 else 1

        if close_pos > 0.7 and vol_ratio > 1.3 and c[i] < c[i-1]:
            acc_count += 1  # closing high on higher volume despite down day
        elif close_pos < 0.3 and vol_ratio > 1.3 and c[i] > c[i-1]:
            dist_count += 1  # closing low on higher volume despite up day

    if acc_count >= 3:
        signals.append({
            "pattern": "Institutional Accumulation",
            "signal": "bullish",
            "confidence": 0.72,
            "desc": f"{acc_count} accumulation bars in last 10 — smart money buying into weakness",
            "category": "institutional",
        })

    if dist_count >= 3:
        signals.append({
            "pattern": "Institutional Distribution",
            "signal": "bearish",
            "confidence": 0.72,
            "desc": f"{dist_count} distribution bars in last 10 — smart money selling into strength",
            "category": "institutional",
        })

    return signals


# ═════════════════════════════════════════════════════════════════════════════
# 8. RANGE CONTRACTION / EXPANSION (NR7, INSIDE BARS)
# ═════════════════════════════════════════════════════════════════════════════

def detect_range_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """NR7 (narrowest range of 7), inside bars, outside bars."""
    signals = []
    if len(df) < 10:
        return signals

    h, l = df["high"].values, df["low"].values
    ranges = h - l

    # NR7 — narrowest range of 7 bars
    if len(ranges) >= 7:
        last_7 = ranges[-7:]
        if ranges[-1] == min(last_7) and ranges[-1] > 0:
            signals.append({
                "pattern": "NR7 (Narrowest Range 7)",
                "signal": "neutral",
                "confidence": 0.70,
                "desc": "Today's range is narrowest of last 7 bars — expansion/breakout expected",
                "category": "range",
            })

    # Inside bar
    if len(df) >= 2:
        if h[-1] < h[-2] and l[-1] > l[-2]:
            signals.append({
                "pattern": "Inside Bar",
                "signal": "neutral",
                "confidence": 0.65,
                "desc": f"Bar contained within prior bar (${l[-1]:.2f}-${h[-1]:.2f} inside ${l[-2]:.2f}-${h[-2]:.2f})",
                "category": "range",
            })

    # Outside bar (engulfs prior range)
    if len(df) >= 2:
        if h[-1] > h[-2] and l[-1] < l[-2]:
            change = (df["close"].values[-1] - df["open"].values[-1])
            sig = "bullish" if change > 0 else "bearish"
            signals.append({
                "pattern": "Outside Bar",
                "signal": sig,
                "confidence": 0.62,
                "desc": f"Range engulfs prior bar — {'bullish' if change > 0 else 'bearish'} expansion",
                "category": "range",
            })

    return signals


# ═════════════════════════════════════════════════════════════════════════════
# 9. MOVING AVERAGE CROSSOVERS & ALIGNMENT
# ═════════════════════════════════════════════════════════════════════════════

def analyze_ma_structure(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """MA crossovers, ribbon alignment, death/golden cross proximity."""
    signals = []
    if len(df) < 200:
        return signals

    c = df["close"]
    ema9 = _ema(c, 9).values
    sma20 = _sma(c, 20).values
    sma50 = _sma(c, 50).values
    sma200 = _sma(c, 200).values

    # Full bullish alignment: price > EMA9 > SMA20 > SMA50 > SMA200
    if (c.values[-1] > ema9[-1] > sma20[-1] > sma50[-1] > sma200[-1]):
        signals.append({
            "pattern": "Full Bullish MA Alignment",
            "signal": "bullish",
            "confidence": 0.78,
            "desc": "Price > EMA9 > SMA20 > SMA50 > SMA200 — strong uptrend confirmed",
            "category": "ma_structure",
        })
    elif (c.values[-1] < ema9[-1] < sma20[-1] < sma50[-1] < sma200[-1]):
        signals.append({
            "pattern": "Full Bearish MA Alignment",
            "signal": "bearish",
            "confidence": 0.78,
            "desc": "Price < EMA9 < SMA20 < SMA50 < SMA200 — strong downtrend confirmed",
            "category": "ma_structure",
        })

    # Golden/Death cross detection (SMA50 vs SMA200)
    if not np.isnan(sma50[-1]) and not np.isnan(sma200[-1]):
        if sma50[-2] < sma200[-2] and sma50[-1] >= sma200[-1]:
            signals.append({
                "pattern": "Golden Cross",
                "signal": "bullish",
                "confidence": 0.72,
                "desc": f"SMA50 crossed above SMA200 — major bullish signal",
                "category": "ma_structure",
            })
        elif sma50[-2] > sma200[-2] and sma50[-1] <= sma200[-1]:
            signals.append({
                "pattern": "Death Cross",
                "signal": "bearish",
                "confidence": 0.72,
                "desc": f"SMA50 crossed below SMA200 — major bearish signal",
                "category": "ma_structure",
            })

        # Proximity to cross (within 1%)
        gap_pct = abs(sma50[-1] - sma200[-1]) / sma200[-1] * 100
        if gap_pct < 1.0 and not (sma50[-2] < sma200[-2] and sma50[-1] >= sma200[-1]) and not (sma50[-2] > sma200[-2] and sma50[-1] <= sma200[-1]):
            approaching = "golden" if sma50[-1] < sma200[-1] and sma50[-1] > sma50[-5] else "death"
            signals.append({
                "pattern": f"Approaching {'Golden' if approaching == 'golden' else 'Death'} Cross",
                "signal": "bullish" if approaching == "golden" else "bearish",
                "confidence": 0.60,
                "desc": f"SMA50/SMA200 gap only {gap_pct:.2f}% — {'golden' if approaching=='golden' else 'death'} cross approaching",
                "category": "ma_structure",
            })

    # EMA9/SMA20 crossover (short-term)
    if not np.isnan(ema9[-1]) and not np.isnan(sma20[-1]):
        if ema9[-2] < sma20[-2] and ema9[-1] >= sma20[-1]:
            signals.append({
                "pattern": "EMA9/SMA20 Bullish Cross",
                "signal": "bullish",
                "confidence": 0.62,
                "desc": "Short-term EMA9 crossed above SMA20 — momentum turning up",
                "category": "ma_structure",
            })
        elif ema9[-2] > sma20[-2] and ema9[-1] <= sma20[-1]:
            signals.append({
                "pattern": "EMA9/SMA20 Bearish Cross",
                "signal": "bearish",
                "confidence": 0.62,
                "desc": "Short-term EMA9 crossed below SMA20 — momentum turning down",
                "category": "ma_structure",
            })

    return signals


# ═════════════════════════════════════════════════════════════════════════════
# 10. SUPPORT/RESISTANCE PROXIMITY
# ═════════════════════════════════════════════════════════════════════════════

def analyze_sr_proximity(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect key S/R levels and check proximity to current price."""
    signals = []
    if len(df) < 60:
        return signals

    c, h, l = df["close"].values, df["high"].values, df["low"].values
    last = c[-1]

    # 52-week high/low
    lb = min(252, len(df))
    high_52w = np.max(h[-lb:])
    low_52w = np.min(l[-lb:])

    dist_from_high = (high_52w - last) / high_52w * 100
    dist_from_low = (last - low_52w) / low_52w * 100

    if dist_from_high < 3:
        signals.append({
            "pattern": "Near 52-Week High",
            "signal": "bullish",
            "confidence": 0.65,
            "desc": f"Price ${last:.2f} is {dist_from_high:.1f}% from 52w high ${high_52w:.2f} — breakout or resistance",
            "category": "sr_level",
        })
    elif dist_from_low < 5:
        signals.append({
            "pattern": "Near 52-Week Low",
            "signal": "bearish",
            "confidence": 0.60,
            "desc": f"Price ${last:.2f} is {dist_from_low:.1f}% from 52w low ${low_52w:.2f} — support or breakdown",
            "category": "sr_level",
        })

    # SMA proximity
    if len(df) >= 200:
        sma200 = _sma(df["close"], 200).values[-1]
        if not np.isnan(sma200):
            dist = abs(last - sma200) / sma200 * 100
            if dist < 2:
                sig = "bullish" if last > sma200 else "bearish"
                signals.append({
                    "pattern": "Testing SMA200",
                    "signal": sig,
                    "confidence": 0.70,
                    "desc": f"Price ${last:.2f} is {dist:.1f}% from SMA200 ${sma200:.2f} — major level test",
                    "category": "sr_level",
                })

    return signals


# ═════════════════════════════════════════════════════════════════════════════
# MASTER ENGINE — runs all detectors and aggregates
# ═════════════════════════════════════════════════════════════════════════════

def run_deep_analysis(df: pd.DataFrame, timeframe: str = "daily") -> Dict[str, Any]:
    """
    Run ALL deep pattern detectors on a DataFrame.
    Returns aggregated signals with confidence scores and bias.
    """
    all_signals = []

    detectors = [
        analyze_volume_profile,
        detect_divergences,
        analyze_volatility_regime,
        detect_gaps,
        detect_mean_reversion,
        analyze_trend_exhaustion,
        detect_institutional_activity,
        detect_range_patterns,
        analyze_ma_structure,
        analyze_sr_proximity,
    ]

    for detector in detectors:
        try:
            signals = detector(df)
            for s in signals:
                s["timeframe"] = timeframe
            all_signals.extend(signals)
        except Exception as e:
            pass  # skip failed detector, don't crash

    # Compute aggregated bias
    bull = [s for s in all_signals if s["signal"] == "bullish"]
    bear = [s for s in all_signals if s["signal"] == "bearish"]
    neut = [s for s in all_signals if s["signal"] == "neutral"]

    # Confidence-weighted scoring
    bull_score = sum(s["confidence"] for s in bull)
    bear_score = sum(s["confidence"] for s in bear)
    total_score = bull_score + bear_score

    if total_score > 0:
        bias_pct = bull_score / total_score * 100
    else:
        bias_pct = 50.0

    if bias_pct >= 65:
        bias = "BULLISH"
    elif bias_pct <= 35:
        bias = "BEARISH"
    elif bias_pct >= 55:
        bias = "LEAN_BULLISH"
    elif bias_pct <= 45:
        bias = "LEAN_BEARISH"
    else:
        bias = "NEUTRAL"

    return {
        "timeframe": timeframe,
        "total_signals": len(all_signals),
        "bullish_count": len(bull),
        "bearish_count": len(bear),
        "neutral_count": len(neut),
        "bull_confidence": round(bull_score, 2),
        "bear_confidence": round(bear_score, 2),
        "bias_pct": round(bias_pct, 1),
        "bias": bias,
        "signals": all_signals,
        "categories": list(set(s.get("category", "other") for s in all_signals)),
    }
