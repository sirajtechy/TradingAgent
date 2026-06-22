"""
recovery_regime.py — Post-correction recovery detector (Phase 2).

Phoenix's standard hard gates (price > SMA200 AND >= +50% from 52w low) are a
trend-continuation filter: they correctly avoid value traps and broken-trend
whipsaws ~90% of the time, but they categorically reject the early days of a
broad-market recovery. The 2025-04-23 IT backtest is the canonical failure:
~95% of names were below SMA200 and only 11 trading days off the tariff crash
low, so Phoenix issued 193/206 AVOID even though 184 of those went on to hit
+5% within 15 days (median alpha vs QQQ: +3.3pp).

This module detects "post-correction recovery" regimes so a separate, narrower
gate can fire on names that are credibly reclaiming structure (Bill O'Neil
follow-through-day spirit; Stan Weinstein Stage 1 → 2 transition).

The detector is intentionally conservative: it only fires when the market has
ALREADY taken a meaningful drawdown AND has ALREADY started turning. It does
NOT predict reversals — it confirms one in progress.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.phoenix.models import PhoenixSnapshot

from .features import ema_at, slope_rising, snapshot_bars

_DEFAULT_DD_WINDOW = 30
_DEFAULT_DD_THRESHOLD_PCT = 8.0
# FTD window of 15 sessions: O'Neil's original framing is "day 4-15 of the
# rally attempt". 7 sessions misses the canonical case (2025-04-09 SPY +10.5%
# tariff-pause FTD, 11 sessions before 2025-04-23).
_DEFAULT_FTD_WINDOW = 15
_DEFAULT_FTD_GAIN_PCT = 1.5
# Volume baseline is the 30-day average ending BEFORE the recent drawdown.
# Using a 10-day average contaminated by panic-day volume drops the ratio
# below 1.0× even on legitimate institutional re-entry days.
_DEFAULT_FTD_VOL_MULT = 1.10
_DEFAULT_FTD_VOL_BASELINE_DAYS = 30


def detect_recovery_regime(
    index_snapshot: Optional[PhoenixSnapshot],
    *,
    drawdown_window: int = _DEFAULT_DD_WINDOW,
    drawdown_threshold_pct: float = _DEFAULT_DD_THRESHOLD_PCT,
    ftd_window: int = _DEFAULT_FTD_WINDOW,
    ftd_gain_pct: float = _DEFAULT_FTD_GAIN_PCT,
    ftd_vol_mult: float = _DEFAULT_FTD_VOL_MULT,
) -> Dict[str, Any]:
    """
    Return regime state for the broad market index.

    A "post-correction recovery" requires THREE things to be true together:
      1. The index drew down >= ``drawdown_threshold_pct`` (default 8%) at
         some point in the last ``drawdown_window`` (default 30) trading days.
      2. Price is currently above its 10-period EMA with positive slope.
      3. At least one "follow-through day" in the last ``ftd_window`` (default
         7) trading days: close up >= ``ftd_gain_pct`` on volume >=
         ``ftd_vol_mult`` × 10-day avg. (Bill O'Neil's FTD signal.)

    Returns a dict with ``is_recovery`` boolean and diagnostic metrics so the
    caller can see why it did or didn't fire.
    """
    bars = snapshot_bars(index_snapshot)
    if len(bars) < max(30, drawdown_window + 5):
        return {
            "is_recovery": False,
            "reason": "insufficient_index_history",
            "drawdown_window_pct": None,
            "above_ema10": None,
            "ema10_rising": None,
            "follow_through_day": False,
            "diagnostic": "Need at least 30 bars of index history.",
        }

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]
    current_price = closes[-1]

    # 1. Correction occurred: max DD in last 30 days >= threshold
    window_bars = bars[-drawdown_window:]
    window_high = max(b.high for b in window_bars)
    dd_pct = (window_high - current_price) / window_high * 100.0 if window_high > 0 else 0.0
    max_dd_in_window = _max_drawdown_in_window(window_bars)
    drew_down = max_dd_in_window >= drawdown_threshold_pct

    # 2. Follow-through day in last ftd_window sessions (Bill O'Neil signal)
    ftd, ftd_detail = _detect_follow_through_day(
        bars,
        window=ftd_window,
        gain_pct=ftd_gain_pct,
        vol_mult=ftd_vol_mult,
    )

    # 3. FTD still valid: price hasn't closed below the FTD-day low since,
    # AND no new 20-day intraday low has been printed since the FTD. This
    # captures O'Neil's rule that an undercut of the FTD-day low cancels it.
    ftd_still_valid = True
    ftd_index: Optional[int] = None
    if ftd and ftd_detail:
        for i in range(len(bars) - 1, -1, -1):
            bd = bars[i].bar_date
            iso = bd.isoformat() if hasattr(bd, "isoformat") else str(bd)
            if iso == ftd_detail["bar_date"]:
                ftd_index = i
                break
    if ftd_index is not None:
        ftd_low = bars[ftd_index].low
        # Closes after FTD must not have broken below FTD-day low
        for j in range(ftd_index + 1, len(bars)):
            if bars[j].close < ftd_low:
                ftd_still_valid = False
                break

    # 4. No new 20-day low in the last 5 sessions — confirms downtrend break
    no_new_low = True
    if len(lows) >= 25:
        for i in range(-5, 0):
            if lows[i] < min(lows[i - 20:i]):
                no_new_low = False
                break

    # Reference: include EMA10 in diagnostics but don't gate on its slope
    ema10 = ema_at(bars, 10)
    above_ema10 = ema10 is not None and current_price > ema10

    is_recovery = bool(drew_down and ftd and ftd_still_valid and no_new_low)

    notes: List[str] = []
    if not drew_down:
        notes.append(
            f"No recent correction: max DD in last {drawdown_window}d is "
            f"{max_dd_in_window:.1f}% (need >= {drawdown_threshold_pct:.1f}%)."
        )
    if not ftd:
        notes.append(
            f"No follow-through day in last {ftd_window}d "
            f"(need close >= +{ftd_gain_pct:.1f}% on volume >= "
            f"{ftd_vol_mult:.2f}x 30d-pre-window baseline)."
        )
    if ftd and not ftd_still_valid:
        notes.append("FTD invalidated — price closed below FTD-day low.")
    if not no_new_low:
        notes.append("Index made a new 20-day low in the last 5 sessions — downtrend not broken.")

    return {
        "is_recovery": is_recovery,
        "reason": "ok" if is_recovery else "criteria_unmet",
        "max_drawdown_pct_in_window": round(max_dd_in_window, 2),
        "current_dd_from_window_high_pct": round(dd_pct, 2),
        "no_new_20d_low_in_last_5d": no_new_low,
        "above_ema10": above_ema10,
        "ema10": round(ema10, 2) if ema10 is not None else None,
        "follow_through_day": ftd,
        "follow_through_still_valid": ftd_still_valid,
        "follow_through_detail": ftd_detail,
        "diagnostic": " ".join(notes) if notes else "All recovery criteria satisfied.",
    }


def _max_drawdown_in_window(window_bars) -> float:
    """Largest peak-to-trough decline within the window (intraday high → close)."""
    peak = window_bars[0].high
    worst = 0.0
    for b in window_bars:
        if b.high > peak:
            peak = b.high
        if peak > 0:
            dd = (peak - b.low) / peak * 100.0
            if dd > worst:
                worst = dd
    return worst


def _detect_follow_through_day(
    bars,
    *,
    window: int,
    gain_pct: float,
    vol_mult: float,
    baseline_days: int = _DEFAULT_FTD_VOL_BASELINE_DAYS,
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Bill O'Neil follow-through day: after a correction, look for a single
    high-volume up-day signaling institutional re-entry. We only check the
    most-recent ``window`` bars.

    Volume baseline uses the ``baseline_days``-bar trailing average measured
    BEFORE the lookback window so panic-day volume doesn't deflate the ratio.
    """
    if len(bars) < window + baseline_days + 2:
        return False, None
    baseline_end = len(bars) - window - 1
    baseline_start = max(0, baseline_end - baseline_days)
    baseline_window = bars[baseline_start:baseline_end]
    if not baseline_window:
        return False, None
    baseline_avg_vol = sum(x.volume for x in baseline_window) / len(baseline_window)
    if baseline_avg_vol <= 0:
        return False, None

    for i in range(len(bars) - 1, len(bars) - 1 - window, -1):
        b = bars[i]
        prev = bars[i - 1]
        if prev.close <= 0:
            continue
        gain = (b.close - prev.close) / prev.close * 100.0
        vol_ratio = b.volume / baseline_avg_vol
        if gain >= gain_pct and vol_ratio >= vol_mult:
            return True, {
                "bar_date": b.bar_date.isoformat() if hasattr(b.bar_date, "isoformat") else str(b.bar_date),
                "gain_pct": round(gain, 2),
                "volume_vs_baseline": round(vol_ratio, 2),
                "baseline_days": baseline_days,
            }
    return False, None
