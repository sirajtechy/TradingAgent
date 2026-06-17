"""Weekly Supertrend regime filter — cash-only on bear signal."""

from __future__ import annotations

from typing import Optional

import pandas as pd


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def compute_supertrend(
    df: pd.DataFrame,
    period: int = 10,
    multiplier: float = 2.5,
) -> pd.Series:
    """
    Return Supertrend direction series: 1 = bull, -1 = bear.
    """
    if df is None or df.empty:
        return pd.Series(dtype=float)

    hl2 = (df["High"] + df["Low"]) / 2.0
    atr = _atr(df, period)
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    st = pd.Series(index=df.index, dtype=float)
    direction = 1.0
    final_upper = upper.iloc[0]
    final_lower = lower.iloc[0]

    for i in range(len(df)):
        if i == 0:
            st.iloc[i] = direction
            continue
        c = float(df["Close"].iloc[i])
        fu = float(upper.iloc[i])
        fl = float(lower.iloc[i])
        if c > final_upper:
            direction = 1.0
        elif c < final_lower:
            direction = -1.0
        final_upper = min(fu, final_upper) if direction == 1.0 else fu
        final_lower = max(fl, final_lower) if direction == -1.0 else fl
        st.iloc[i] = direction

    return st


def is_bull_regime(
    weekly_df: pd.DataFrame,
    *,
    period: int = 10,
    multiplier: float = 2.5,
) -> bool:
    """True when latest weekly Supertrend is bullish."""
    if weekly_df is None or weekly_df.empty:
        return True
    st = compute_supertrend(weekly_df, period=period, multiplier=multiplier)
    if st.empty:
        return True
    return float(st.iloc[-1]) >= 0
