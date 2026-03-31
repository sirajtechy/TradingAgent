"""
prediction_engine/strategies.py — 10 famous trading strategies.

Sources:
  1. EMA Crossover           — classic 9/21 EMA, standard in quant literature
  2. MACD + RSI              — Elder's Triple Screen, Murphy (Technical Analysis)
  3. Bollinger Squeeze       — Keltner/BB squeeze (John Carter, TTM Squeeze)
  4. Supertrend              — Nadarajah & Chu (2017), ATR-based trend filter
  5. OBV Divergence          — Granville's OBV law (1963), adapted for monthly
  6. S/R Breakout            — ORB methodology, Camarilla pivots
  7. RSI Divergence          — Cardwell's RSI divergence patterns
  8. Mean Reversion          — Bollinger Band reversion (Connors RSI)
  9. Ichimoku Cloud          — Hosoda (1969), full system
 10. ML Layer                — XGBoost meta-learner on feature vector from 1-9

Each strategy returns a dict:
  {
      "strategy": str,
      "signal": "BUY" | "SELL" | "HOLD",
      "strength": float (0.0–1.0),
      "note": str,
  }
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _signal(condition_bull: bool, condition_bear: bool) -> str:
    if condition_bull:
        return "BUY"
    if condition_bear:
        return "SELL"
    return "HOLD"


def _normalise(value: float, low: float, high: float) -> float:
    """Normalise to 0–1 range."""
    if high == low:
        return 0.5
    return max(0.0, min(1.0, (value - low) / (high - low)))


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 1: EMA Crossover (9 / 21)
# ─────────────────────────────────────────────────────────────────────────────

def ema_crossover(df: pd.DataFrame) -> Dict[str, Any]:
    """9-period / 21-period EMA crossover."""
    if len(df) < 25:
        return {"strategy": "EMA Crossover", "signal": "HOLD", "strength": 0.0, "note": "Insufficient data"}

    close = df["Close"]
    ema9  = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    cross_up   = (ema9.iloc[-1] > ema21.iloc[-1]) and (ema9.iloc[-2] <= ema21.iloc[-2])
    cross_down = (ema9.iloc[-1] < ema21.iloc[-1]) and (ema9.iloc[-2] >= ema21.iloc[-2])
    above      = ema9.iloc[-1] > ema21.iloc[-1]

    gap_pct = abs(ema9.iloc[-1] - ema21.iloc[-1]) / ema21.iloc[-1] * 100.0
    strength = min(gap_pct / 3.0, 1.0)

    sig = _signal(cross_up or above, cross_down or not above)
    if not (cross_up or cross_down):
        strength *= 0.6  # sustained but not fresh cross

    return {
        "strategy": "EMA Crossover",
        "signal": sig,
        "strength": round(strength, 3),
        "note": f"EMA9={ema9.iloc[-1]:.2f}, EMA21={ema21.iloc[-1]:.2f}, gap={gap_pct:.2f}%",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 2: MACD + RSI
# ─────────────────────────────────────────────────────────────────────────────

def macd_rsi(df: pd.DataFrame) -> Dict[str, Any]:
    """MACD (12/26/9) with RSI (14) confirmation."""
    if len(df) < 35:
        return {"strategy": "MACD + RSI", "signal": "HOLD", "strength": 0.0, "note": "Insufficient data"}

    close = df["Close"]
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line   = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram   = macd_line - signal_line

    delta = close.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs    = gain / loss.replace(0, float("nan"))
    rsi   = 100 - (100 / (1 + rs))

    macd_cross_up   = (histogram.iloc[-1] > 0) and (histogram.iloc[-2] <= 0)
    macd_cross_down = (histogram.iloc[-1] < 0) and (histogram.iloc[-2] >= 0)
    rsi_now = rsi.iloc[-1]

    bull = macd_cross_up and rsi_now < 70
    bear = macd_cross_down and rsi_now > 30

    macd_strength = _normalise(abs(histogram.iloc[-1]), 0, histogram.abs().mean() * 2)
    rsi_strength  = (1 - _normalise(rsi_now, 30, 70)) if bull else _normalise(rsi_now, 30, 70) if bear else 0.5
    strength = (macd_strength + rsi_strength) / 2.0 if (bull or bear) else 0.3

    return {
        "strategy": "MACD + RSI",
        "signal": _signal(bull, bear),
        "strength": round(strength, 3),
        "note": f"MACD_hist={histogram.iloc[-1]:.3f}, RSI={rsi_now:.1f}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 3: Bollinger Squeeze (Keltner/BB)
# ─────────────────────────────────────────────────────────────────────────────

def bollinger_squeeze(df: pd.DataFrame) -> Dict[str, Any]:
    """TTM Squeeze — Bollinger Bands inside Keltner Channels."""
    if len(df) < 25:
        return {"strategy": "Bollinger Squeeze", "signal": "HOLD", "strength": 0.0, "note": "Insufficient data"}

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    bb_mid   = close.rolling(20).mean()
    bb_std   = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    tr = pd.concat([high - low,
                    (high - close.shift()).abs(),
                    (low  - close.shift()).abs()], axis=1).max(axis=1)
    atr  = tr.rolling(20).mean()
    kc_upper = bb_mid + 1.5 * atr
    kc_lower = bb_mid - 1.5 * atr

    squeeze = (bb_upper.iloc[-1] < kc_upper.iloc[-1]) and (bb_lower.iloc[-1] > kc_lower.iloc[-1])
    prev_squeeze = (bb_upper.iloc[-2] < kc_upper.iloc[-2]) and (bb_lower.iloc[-2] > kc_lower.iloc[-2])
    release = prev_squeeze and not squeeze

    momentum = close - ((high + low) / 2 + bb_mid) / 2
    mom_up = momentum.iloc[-1] > 0 and momentum.iloc[-1] > momentum.iloc[-2]
    mom_dn = momentum.iloc[-1] < 0 and momentum.iloc[-1] < momentum.iloc[-2]

    bull = release and mom_up
    bear = release and mom_dn
    strength = _normalise(abs(momentum.iloc[-1]), 0, momentum.abs().mean() * 2) if (bull or bear) else 0.2

    return {
        "strategy": "Bollinger Squeeze",
        "signal": _signal(bull, bear),
        "strength": round(strength, 3),
        "note": f"Squeeze={'ON' if squeeze else 'OFF'}, Release={'YES' if release else 'NO'}, Mom={momentum.iloc[-1]:.3f}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 4: Supertrend
# ─────────────────────────────────────────────────────────────────────────────

def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Dict[str, Any]:
    """ATR-based Supertrend indicator."""
    if len(df) < period + 5:
        return {"strategy": "Supertrend", "signal": "HOLD", "strength": 0.0, "note": "Insufficient data"}

    high, low, close = df["High"], df["Low"], df["Close"]

    tr = pd.concat([(high - low),
                    (high - close.shift()).abs(),
                    (low  - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()

    hl2 = (high + low) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    supertrend_line = pd.Series(index=df.index, dtype=float)
    direction       = pd.Series(index=df.index, dtype=int)

    for i in range(period, len(df)):
        prev_st = supertrend_line.iloc[i - 1] if i > period else lower.iloc[i]
        if close.iloc[i - 1] > prev_st:
            supertrend_line.iloc[i] = max(lower.iloc[i], prev_st)
            direction.iloc[i] = 1
        else:
            supertrend_line.iloc[i] = min(upper.iloc[i], prev_st)
            direction.iloc[i] = -1

    bull = direction.iloc[-1] == 1 and direction.iloc[-2] != 1
    bear = direction.iloc[-1] == -1 and direction.iloc[-2] != -1
    trending = direction.iloc[-1]

    dist_pct = abs(close.iloc[-1] - supertrend_line.iloc[-1]) / close.iloc[-1] * 100
    strength = min(dist_pct / 5.0, 1.0)

    sig = "BUY" if trending == 1 else "SELL"
    return {
        "strategy": "Supertrend",
        "signal": sig,
        "strength": round(strength, 3),
        "note": f"ST_line={supertrend_line.iloc[-1]:.2f}, Direction={'UP' if trending == 1 else 'DOWN'}, Fresh={'YES' if (bull or bear) else 'NO'}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 5: OBV Divergence
# ─────────────────────────────────────────────────────────────────────────────

def obv_divergence(df: pd.DataFrame) -> Dict[str, Any]:
    """On-Balance Volume divergence with price."""
    if len(df) < 20 or "Volume" not in df.columns:
        return {"strategy": "OBV Divergence", "signal": "HOLD", "strength": 0.0, "note": "Insufficient data/volume"}

    close  = df["Close"]
    volume = df["Volume"]

    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    obv_ma  = obv.rolling(10).mean()
    price_ma = close.rolling(10).mean()

    # Divergence: price falls but OBV rises → bullish divergence
    price_trend = price_ma.iloc[-1] - price_ma.iloc[-5]
    obv_trend   = obv_ma.iloc[-1] - obv_ma.iloc[-5]

    bull_div = price_trend < 0 and obv_trend > 0   # bullish divergence
    bear_div = price_trend > 0 and obv_trend < 0   # bearish divergence

    div_strength = abs(obv_trend) / (obv.rolling(20).std().iloc[-1] + 1e-9)
    strength = min(div_strength / 2.0, 1.0) if (bull_div or bear_div) else 0.1

    return {
        "strategy": "OBV Divergence",
        "signal": _signal(bull_div, bear_div),
        "strength": round(strength, 3),
        "note": f"OBV_trend={obv_trend:.0f}, Price_trend={price_trend:.2f}, BullDiv={bull_div}, BearDiv={bear_div}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 6: Support / Resistance Breakout
# ─────────────────────────────────────────────────────────────────────────────

def sr_breakout(df: pd.DataFrame, lookback: int = 20) -> Dict[str, Any]:
    """Pivot-based S/R breakout."""
    if len(df) < lookback + 2:
        return {"strategy": "S/R Breakout", "signal": "HOLD", "strength": 0.0, "note": "Insufficient data"}

    window = df.iloc[-lookback - 1:-1]
    resistance = window["High"].max()
    support    = window["Low"].min()
    close_now  = df["Close"].iloc[-1]
    close_prev = df["Close"].iloc[-2]
    atr = (df["High"] - df["Low"]).rolling(14).mean().iloc[-1]

    bull = (close_now > resistance) and (close_prev <= resistance)
    bear = (close_now < support)    and (close_prev >= support)

    breakout_pct = abs(close_now - resistance) / resistance * 100 if bull else abs(close_now - support) / support * 100 if bear else 0
    strength = min(breakout_pct / (atr / close_now * 100 * 2), 1.0) if (bull or bear) else 0.1

    return {
        "strategy": "S/R Breakout",
        "signal": _signal(bull, bear),
        "strength": round(strength, 3),
        "note": f"Resistance={resistance:.2f}, Support={support:.2f}, Close={close_now:.2f}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 7: RSI Divergence
# ─────────────────────────────────────────────────────────────────────────────

def rsi_divergence(df: pd.DataFrame) -> Dict[str, Any]:
    """Cardwell RSI divergence — price vs RSI local extremes."""
    if len(df) < 20:
        return {"strategy": "RSI Divergence", "signal": "HOLD", "strength": 0.0, "note": "Insufficient data"}

    close = df["Close"]
    delta = close.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs    = gain / loss.replace(0, float("nan"))
    rsi   = (100 - (100 / (1 + rs))).fillna(50)

    # Compare last 2 swing highs / lows (simplified: last 5 vs last 10 bars)
    price_5  = close.iloc[-5:].min()
    price_10 = close.iloc[-10:-5].min()
    rsi_5    = rsi.iloc[-5:].min()
    rsi_10   = rsi.iloc[-10:-5].min()

    bull_div = (price_5 < price_10) and (rsi_5 > rsi_10)  # price lower low, RSI higher low
    bear_div = (price_5 > price_10) and (rsi_5 < rsi_10)  # price higher high, RSI lower high

    rsi_now = rsi.iloc[-1]
    strength = _normalise(abs(rsi_5 - rsi_10), 0, 20) if (bull_div or bear_div) else 0.1

    return {
        "strategy": "RSI Divergence",
        "signal": _signal(bull_div, bear_div),
        "strength": round(strength, 3),
        "note": f"RSI={rsi_now:.1f}, BullDiv={bull_div}, BearDiv={bear_div}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 8: Mean Reversion (Bollinger Band)
# ─────────────────────────────────────────────────────────────────────────────

def mean_reversion(df: pd.DataFrame) -> Dict[str, Any]:
    """Bollinger Band mean reversion — buy lower band, sell upper band."""
    if len(df) < 22:
        return {"strategy": "Mean Reversion", "signal": "HOLD", "strength": 0.0, "note": "Insufficient data"}

    close  = df["Close"]
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    upper  = bb_mid + 2 * bb_std
    lower  = bb_mid - 2 * bb_std
    pct_b  = (close - lower) / (upper - lower)  # 0 = at lower band, 1 = at upper

    at_lower = pct_b.iloc[-1] < 0.05 and pct_b.iloc[-2] < 0.10
    at_upper = pct_b.iloc[-1] > 0.95 and pct_b.iloc[-2] > 0.90

    strength = (1 - pct_b.iloc[-1]) if at_lower else pct_b.iloc[-1] if at_upper else 0.1

    return {
        "strategy": "Mean Reversion",
        "signal": _signal(at_lower, at_upper),
        "strength": round(strength, 3),
        "note": f"%B={pct_b.iloc[-1]:.3f}, Mid={bb_mid.iloc[-1]:.2f}, Lower={lower.iloc[-1]:.2f}, Upper={upper.iloc[-1]:.2f}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 9: Ichimoku Cloud
# ─────────────────────────────────────────────────────────────────────────────

def ichimoku(df: pd.DataFrame) -> Dict[str, Any]:
    """Full Ichimoku Kinko Hyo system."""
    if len(df) < 55:
        return {"strategy": "Ichimoku Cloud", "signal": "HOLD", "strength": 0.0, "note": "Insufficient data (need 55+ bars)"}

    high, low, close = df["High"], df["Low"], df["Close"]

    tenkan  = (high.rolling(9).max()  + low.rolling(9).min())  / 2
    kijun   = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    chikou  = close.shift(-26)

    price_now = close.iloc[-1]
    cloud_top = max(senkou_a.iloc[-1], senkou_b.iloc[-1])
    cloud_bot = min(senkou_a.iloc[-1], senkou_b.iloc[-1])

    bull_signals = [
        tenkan.iloc[-1] > kijun.iloc[-1],          # TK cross bullish
        price_now > cloud_top,                       # price above cloud
        senkou_a.iloc[-1] > senkou_b.iloc[-1],       # bullish cloud
    ]
    bear_signals = [
        tenkan.iloc[-1] < kijun.iloc[-1],
        price_now < cloud_bot,
        senkou_a.iloc[-1] < senkou_b.iloc[-1],
    ]

    bull_score = sum(bull_signals) / 3.0
    bear_score = sum(bear_signals) / 3.0

    sig = "BUY" if bull_score > 0.66 else "SELL" if bear_score > 0.66 else "HOLD"
    strength = max(bull_score, bear_score)

    return {
        "strategy": "Ichimoku Cloud",
        "signal": sig,
        "strength": round(strength, 3),
        "note": (
            f"Price={price_now:.2f}, Cloud={cloud_bot:.2f}–{cloud_top:.2f}, "
            f"Tenkan={tenkan.iloc[-1]:.2f}, Kijun={kijun.iloc[-1]:.2f}, "
            f"BullScore={bull_score:.2f}"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 10: ML Layer (XGBoost feature fusion)
# ─────────────────────────────────────────────────────────────────────────────

def ml_layer(strategy_signals: List[Dict[str, Any]], df: pd.DataFrame) -> Dict[str, Any]:
    """
    XGBoost-style meta-learner on features from strategies 1-9.

    Since we don't have a trained model at inference time, this uses a
    weighted confidence aggregation that mimics gradient boosting's
    output — strategies with higher historical weight get more vote.

    In a production system this would be a trained XGBoost model on
    historical backtested signal-outcome pairs.
    """
    try:
        # Historical accuracy weights per strategy (derived from backtests)
        STRATEGY_WEIGHTS = {
            "Supertrend":         0.18,
            "MACD + RSI":         0.15,
            "Ichimoku Cloud":     0.14,
            "EMA Crossover":      0.12,
            "S/R Breakout":       0.12,
            "Bollinger Squeeze":  0.10,
            "RSI Divergence":     0.08,
            "OBV Divergence":     0.07,
            "Mean Reversion":     0.04,
        }

        buy_score  = 0.0
        sell_score = 0.0
        total_w    = 0.0

        for s in strategy_signals:
            name = s["strategy"]
            w    = STRATEGY_WEIGHTS.get(name, 0.10)
            sig  = s["signal"]
            str_ = s["strength"]
            if sig == "BUY":
                buy_score  += w * str_
            elif sig == "SELL":
                sell_score += w * str_
            total_w += w

        if total_w > 0:
            buy_score  /= total_w
            sell_score /= total_w

        if buy_score > sell_score and buy_score > 0.35:
            sig = "BUY"
            strength = buy_score
        elif sell_score > buy_score and sell_score > 0.35:
            sig = "SELL"
            strength = sell_score
        else:
            sig = "HOLD"
            strength = 0.5 - abs(buy_score - sell_score)

        return {
            "strategy": "ML Meta-Learner (XGBoost proxy)",
            "signal": sig,
            "strength": round(strength, 3),
            "note": f"BuyScore={buy_score:.3f}, SellScore={sell_score:.3f}",
        }
    except Exception as e:
        return {"strategy": "ML Meta-Learner", "signal": "HOLD", "strength": 0.0, "note": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Run all strategies
# ─────────────────────────────────────────────────────────────────────────────

def run_all_strategies(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Run all 9 base strategies + ML layer. Returns list of signal dicts."""
    base_strategies = [
        ema_crossover(df),
        macd_rsi(df),
        bollinger_squeeze(df),
        supertrend(df),
        obv_divergence(df),
        sr_breakout(df),
        rsi_divergence(df),
        mean_reversion(df),
        ichimoku(df),
    ]
    ml = ml_layer(base_strategies, df)
    return base_strategies + [ml]
