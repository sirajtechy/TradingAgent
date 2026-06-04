"""
prediction_engine/formatter.py — Formatted prediction output template.

Produces a complete prediction report for a given ticker including:
  - Direction, Entry Date, Exit Date
  - Entry Price, Target Price, Stop Loss
  - Risk/Reward ratio
  - Per-strategy signal status
  - Confluence Score

Acceptance criteria: >60% directional accuracy.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Price targets & stop loss
# ─────────────────────────────────────────────────────────────────────────────

def _compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([(high - low),
                    (high - close.shift()).abs(),
                    (low  - close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]


def compute_targets(
    entry_price: float,
    direction: str,
    atr: float,
    rr_ratio: float = 2.0,
) -> Dict[str, float]:
    """
    Compute target and stop loss using ATR-based levels.

    For BUY:
        stop  = entry - 1.5 * ATR
        target = entry + 1.5 * ATR * RR
    For SELL:
        stop  = entry + 1.5 * ATR
        target = entry - 1.5 * ATR * RR
    """
    atr_mult = 1.5
    risk_pts = atr * atr_mult

    if direction == "BUY":
        stop   = entry_price - risk_pts
        target = entry_price + risk_pts * rr_ratio
    else:  # SELL
        stop   = entry_price + risk_pts
        target = entry_price - risk_pts * rr_ratio

    return {
        "entry_price": round(entry_price, 2),
        "target_price": round(target, 2),
        "stop_loss": round(stop, 2),
        "risk_pts": round(risk_pts, 2),
        "reward_pts": round(risk_pts * rr_ratio, 2),
        "rr_ratio": rr_ratio,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Confluence Score
# ─────────────────────────────────────────────────────────────────────────────

def compute_confluence(
    strategy_signals: List[Dict[str, Any]],
    direction: str,
) -> Dict[str, Any]:
    """
    Confluence Score = weighted agreement % across all strategies.

    Weighting:
      - ML Meta-Learner gets 2x weight
      - All others get 1x weight
    """
    agreement_map = {"BUY": direction == "BUY", "SELL": direction == "SELL", "HOLD": False}

    total_weight = 0.0
    agreeing_weight = 0.0

    for s in strategy_signals:
        w = 2.0 if "ML" in s["strategy"] else 1.0
        total_weight += w * s["strength"]
        if s["signal"] == direction:
            agreeing_weight += w * s["strength"]

    confluence_pct = (agreeing_weight / total_weight * 100.0) if total_weight > 0 else 0.0

    agree_count  = sum(1 for s in strategy_signals if s["signal"] == direction)
    total_active = sum(1 for s in strategy_signals if s["signal"] != "HOLD")

    grade = (
        "STRONG"   if confluence_pct >= 70 else
        "MODERATE" if confluence_pct >= 50 else
        "WEAK"     if confluence_pct >= 30 else
        "NONE"
    )

    return {
        "confluence_score": round(confluence_pct, 1),
        "agreeing_strategies": agree_count,
        "total_active_strategies": total_active,
        "grade": grade,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Full Prediction Output
# ─────────────────────────────────────────────────────────────────────────────

def build_prediction(
    ticker: str,
    df: pd.DataFrame,
    strategy_signals: List[Dict[str, Any]],
    entry_date: Optional[date] = None,
    holding_period_days: int = 30,
) -> Dict[str, Any]:
    """
    Build the full formatted prediction dict from strategy signals + price data.
    """
    # Determine primary direction from ML meta-learner, fall back to vote
    ml_signal = next(
        (s for s in strategy_signals if "ML" in s["strategy"]), None
    )
    if ml_signal and ml_signal["signal"] != "HOLD":
        direction = ml_signal["signal"]
    else:
        buy_count  = sum(1 for s in strategy_signals if s["signal"] == "BUY")
        sell_count = sum(1 for s in strategy_signals if s["signal"] == "SELL")
        if buy_count > sell_count:
            direction = "BUY"
        elif sell_count > buy_count:
            direction = "SELL"
        else:
            direction = "HOLD"

    entry_price = float(df["Close"].iloc[-1])
    atr = _compute_atr(df)
    entry_dt = entry_date or date.today()
    exit_dt  = entry_dt + timedelta(days=holding_period_days)

    targets = compute_targets(entry_price, direction, atr) if direction != "HOLD" else {
        "entry_price": entry_price,
        "target_price": None,
        "stop_loss": None,
        "risk_pts": None,
        "reward_pts": None,
        "rr_ratio": None,
    }
    confluence = compute_confluence(strategy_signals, direction)

    return {
        "ticker":         ticker.upper(),
        "direction":      direction,
        "entry_date":     entry_dt.isoformat(),
        "exit_date":      exit_dt.isoformat(),
        "entry_price":    targets["entry_price"],
        "target_price":   targets["target_price"],
        "stop_loss":      targets["stop_loss"],
        "risk_pts":       targets["risk_pts"],
        "reward_pts":     targets["reward_pts"],
        "risk_reward":    targets["rr_ratio"],
        "atr_14":         round(atr, 2),
        "confluence":     confluence,
        "strategy_signals": strategy_signals,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Display formatter
# ─────────────────────────────────────────────────────────────────────────────

def print_prediction_report(prediction: Dict[str, Any]) -> None:
    """Print a human-readable prediction report."""
    p  = prediction
    c  = p["confluence"]
    ss = p["strategy_signals"]

    dir_arrow = "▲" if p["direction"] == "BUY" else "▼" if p["direction"] == "SELL" else "—"

    print("\n" + "╔" + "═" * 68 + "╗")
    print(f"║  PREDICTION REPORT: {p['ticker']:<48}║")
    print("╠" + "═" * 68 + "╣")
    print(f"║  Direction      : {p['direction']} {dir_arrow:<48}║")
    print(f"║  Entry Date     : {p['entry_date']:<50}║")
    print(f"║  Exit Date      : {p['exit_date']:<50}║")
    print(f"║  Entry Price    : ${p['entry_price']:<49.2f}║")
    if p["target_price"]:
        print(f"║  Target Price   : ${p['target_price']:<49.2f}║")
        print(f"║  Stop Loss      : ${p['stop_loss']:<49.2f}║")
        print(f"║  Risk (pts)     : {p['risk_pts']:<50.2f}║")
        print(f"║  Reward (pts)   : {p['reward_pts']:<50.2f}║")
        print(f"║  Risk / Reward  : 1 : {p['risk_reward']:<46.1f}║")
    print(f"║  ATR (14)       : {p['atr_14']:<50.2f}║")
    print("╠" + "═" * 68 + "╣")
    print(f"║  CONFLUENCE SCORE: {c['confluence_score']}%  [{c['grade']}] "
          f"({c['agreeing_strategies']}/{c['total_active_strategies']} strategies agree)"
          + " " * max(0, 68 - len(f"  CONFLUENCE SCORE: {c['confluence_score']}%  [{c['grade']}] ({c['agreeing_strategies']}/{c['total_active_strategies']} strategies agree)") - 2) + " ║")
    print("╠" + "═" * 68 + "╣")
    print(f"║  {'Strategy':<30} {'Signal':<8} {'Strength':>8}  {'Note':<16} ║")
    print("╠" + "─" * 68 + "╣")
    for s in ss:
        sig_display = s["signal"]
        sig_marker = "✓" if sig_display == p["direction"] else " "
        note_short   = (s["note"] or "")[:15]
        strat_short  = s["strategy"][:28]
        print(f"║ {sig_marker} {strat_short:<30} {sig_display:<8} {s['strength']:>8.3f}  {note_short:<16} ║")
    print("╚" + "═" * 68 + "╝")
