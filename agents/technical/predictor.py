"""
predictor.py — Trade prediction engine for the Technical Agent.

Takes the output of ``analyze_ticker()`` (CWAF-fused via orchestrator) and
produces a concrete trade prediction grounded in pattern geometry and real
bar data.

Entry logic (pattern-driven):
    1. Find the best confirmed bullish pattern (highest confidence,
       breakout_confirmed=True).
    2. Scan backward through bars to find the FIRST bar after the pattern's
       end_date where close crossed above the breakout_price — this is the
       TRUE breakout bar (not always the cutoff).
    3. entry_date  = true_breakout_date + 1 trading day.
    4. entry_price = open of the entry bar (looked up from bars array).
    5. Staleness check: if breakout happened >10 trading days ago AND
       >60% of the measured move is already consumed → NO TRADE (stale).
    6. If no confirmed bullish breakout exists → NO TRADE.

Exit logic (walk-forward simulation):
    Walk each bar from entry through cutoff (all bars we own):
        - bar.low  <= stop_price  → exit at stop_price  (HIT_STOP)
        - bar.high >= target_price → exit at target_price (HIT_TARGET)
    If neither is hit by the last available bar → exit at last close (EXPIRED).

R:R (3:2):
    stop   = entry - 2 × ATR
    target = pattern_target (measured move) if available, else entry + 3 × ATR

LONG-only.  Bearish / neutral orchestrator signals → NO TRADE always.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .models import OHLCVBar

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# ATR multipliers (3:2 risk-reward)
ATR_TARGET_MULT = 3.0   # entry + 3×ATR
ATR_STOP_MULT   = 2.0   # entry - 2×ATR

# Min / Max prediction horizon (trading days - matches MAX_TARGET_DAYS gate)
MIN_TARGET_DAYS = 2
MAX_TARGET_DAYS = 30

# Staleness: how many trading days old a breakout can be before we skip it
_STALE_DAYS_THRESHOLD = 10
# Staleness: if this fraction of the measured move is already consumed → skip
_STALE_MOVE_CONSUMED = 0.60

# Transaction friction (round-trip: commission + slippage)
_FRICTION_PCT = 0.20


# ---------------------------------------------------------------------------
# Helpers: trading-day calendar
# ---------------------------------------------------------------------------

def _next_trading_day(d: date) -> date:
    """Advance to the next weekday (Mon–Fri). Skips weekends only."""
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5:   # 5=Sat, 6=Sun
        nxt += timedelta(days=1)
    return nxt


def _count_trading_days_between(start: date, end: date) -> int:
    """Count weekdays strictly between start and end (exclusive on both ends)."""
    if end <= start:
        return 0
    count = 0
    cur = start + timedelta(days=1)
    while cur < end:
        if cur.weekday() < 5:
            count += 1
        cur += timedelta(days=1)
    return count


def _estimate_days_to_target(
    entry_price: float,
    target_price: float,
    atr: float,
    adx: Optional[float],
    max_trading_days: int,
) -> tuple:
    """
    ATR-velocity estimate of how many trading days to reach target.

    Method (Wilder ATR + ADX strength modifier):
      raw_days = (target - entry) / ATR_daily
      ADX >= 30  → strong trend → price moves ~25% faster  (× 0.75)
      ADX 20-29  → normal trend → no adjustment             (× 1.00)
      ADX < 20   → weak/choppy → price moves ~40% slower   (× 1.40)
    Window: ±30% around midpoint, clamped to [2, max_trading_days].

    Returns (low, mid, high) in trading days.
    """
    if atr <= 0 or target_price <= entry_price:
        mid = max_trading_days // 2
        return max(2, round(mid * 0.7)), mid, max_trading_days

    raw_days = (target_price - entry_price) / atr

    if adx is not None and adx >= 30:
        adj = 0.75   # strong trend — faster
    elif adx is not None and adx >= 20:
        adj = 1.00   # normal
    else:
        adj = 1.40   # choppy/weak — slower

    mid  = max(3, round(raw_days * adj))
    low  = max(2, round(mid * 0.70))
    high = min(max_trading_days, round(mid * 1.40))
    return low, mid, high


# ---------------------------------------------------------------------------
# Helpers: bar lookup
# ---------------------------------------------------------------------------

def _bar_index_on_or_after(bars: List[OHLCVBar], target_date: date) -> Optional[int]:
    """
    Binary-search style: return the index of the first bar whose
    bar_date >= target_date. Returns None if no such bar exists.
    Assumes bars are sorted oldest-first.
    """
    for i, bar in enumerate(bars):
        if bar.bar_date >= target_date:
            return i
    return None


def _find_true_breakout_bar_idx(
    bars: List[OHLCVBar],
    breakout_price: float,
    after_date: date,
) -> Optional[int]:
    """
    Find the index of the FIRST bar after *after_date* where
    bar.close > breakout_price. This is the true breakout bar.

    The pattern detector confirms breakout using the LAST bar, but the
    actual cross may have happened earlier. Finding the real bar lets us
    derive a realistic entry date and price.

    Returns None if no such bar is found (shouldn't happen when
    breakout_confirmed=True, but guarded for safety).
    """
    for i, bar in enumerate(bars):
        if bar.bar_date <= after_date:
            continue
        if bar.close > breakout_price:
            return i
    return None


# ---------------------------------------------------------------------------
# Walk-forward exit simulation
# ---------------------------------------------------------------------------

def _simulate_trade(
    bars: List[OHLCVBar],
    entry_bar_idx: int,
    entry_date: date,
    entry_price: float,
    stop_price: float,
    target_price: float,
    max_bars: int,
) -> Tuple[date, float, str, int]:
    """
    Simulate an exit by walking forward bar-by-bar from the day AFTER entry.

    For each bar:
        - If low  <= stop_price  → exit at stop_price  (HIT_STOP)
        - If high >= target_price → exit at target_price (HIT_TARGET)
    If neither is hit within *max_bars* trading days or we run out of bars,
    exit at the last available close (EXPIRED).

    When no future bars are available (entry is at or beyond the last bar),
    returns exit_outcome="OPEN" — trade is a live setup, not yet simulated.
    exit_date is guaranteed to be >= entry_date.

    Args:
        bars:           Full bar list (oldest-first).
        entry_bar_idx:  Index of the proxy entry bar (for stop/target math).
        entry_date:     The actual entry date (may be in the future).
        entry_price:    The price we entered at.
        stop_price:     Stop-loss price level.
        target_price:   Take-profit price level.
        max_bars:       Maximum number of bars to hold (= target_days).

    Returns:
        (exit_date, exit_price, exit_outcome, bars_simulated)
        exit_outcome: "HIT_TARGET" | "HIT_STOP" | "EXPIRED" | "OPEN"
    """
    start_sim_idx = entry_bar_idx + 1  # first bar after proxy entry bar
    end_sim_idx   = min(start_sim_idx + max_bars, len(bars))  # exclusive upper bound

    bars_checked = 0
    for i in range(start_sim_idx, end_sim_idx):
        bar = bars[i]
        bars_checked += 1

        hit_stop   = bar.low  <= stop_price
        hit_target = bar.high >= target_price

        # Priority: if both triggered same bar, assume worst case hit stop first
        # (conservative — real fill depends on intraday order; we're daily bars)
        if hit_stop:
            return bar.bar_date, round(stop_price, 2), "HIT_STOP", bars_checked
        if hit_target:
            return bar.bar_date, round(target_price, 2), "HIT_TARGET", bars_checked

    # No bars after the proxy entry bar — entry is in the future (live setup)
    if bars_checked == 0:
        return entry_date, round(entry_price, 2), "OPEN", 0

    # Expired within window — exit at close of last bar in window
    last_bar_in_window = bars[min(end_sim_idx - 1, len(bars) - 1)]
    exit_date = last_bar_in_window.bar_date
    # Guard: exit must not be before entry (can happen if bars out of order)
    if exit_date < entry_date:
        exit_date = entry_date
    return (
        exit_date,
        round(last_bar_in_window.close, 2),
        "EXPIRED",
        bars_checked,
    )


# ---------------------------------------------------------------------------
# Pattern selection and entry derivation
# ---------------------------------------------------------------------------

def _select_best_pattern(patterns: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    From the list of detected patterns (dicts from tech_evaluation),
    return the best confirmed bullish breakout pattern (highest confidence).
    Returns None if no eligible pattern exists.
    """
    candidates = [
        p for p in patterns
        if p.get("direction") == "bullish"
        and p.get("breakout_confirmed") is True
        and p.get("breakout_price") is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.get("confidence", 0.0))


def _parse_date(val: Any) -> Optional[date]:
    """Safely parse an ISO date string or return a date object as-is."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        from datetime import datetime
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Main prediction function
# ---------------------------------------------------------------------------

def build_trade_prediction(
    orchestrator_result: Dict[str, Any],
    tech_evaluation: Dict[str, Any],
    cutoff_date: date,
    target_days: int,
    bars: List[OHLCVBar],
) -> Dict[str, Any]:
    """
    Build a pattern-grounded LONG trade prediction.

    Entry:  First confirmed breakout bar after pattern formation end.
    Exit:   Walk-forward bar-by-bar simulation using real OHLCV bars.
    Target: Pattern measured move (if available) or entry + 3×ATR.
    Stop:   entry - 2×ATR.

    NO TRADE when:
        - Orchestrator signal is not "bullish".
        - No confirmed bullish breakout pattern is found.
        - Breakout is stale (>10 days old + >60% of move consumed).

    Args:
        orchestrator_result: CWAF-fused dict from orchestrator.service.
        tech_evaluation:     Raw technical eval dict (rules engine output).
        cutoff_date:         Analysis date. All bars are on/before this date.
        target_days:         Max simulation window in trading days (2–30).
        bars:                OHLCVBar list, sorted oldest-first, up to cutoff.

    Returns:
        Prediction dict. ``trade`` key is None when no trade is recommended.
    """
    target_days = max(MIN_TARGET_DAYS, min(MAX_TARGET_DAYS, target_days))

    # ── Orchestrator data (CWAF) ──────────────────────────────────────────
    orch_signal     = orchestrator_result.get("final_signal", "neutral")
    orch_score      = float(orchestrator_result.get("orchestrator_score", 50.0))
    orch_confidence = float(orchestrator_result.get("final_confidence", 0.5))
    conflict        = orchestrator_result.get("conflict_detected", False)
    conflict_res    = orchestrator_result.get("conflict_resolution")
    weights         = orchestrator_result.get("weights_applied", {})

    tech_out  = orchestrator_result.get("tech_output") or {}
    fund_out  = orchestrator_result.get("fund_output") or {}
    tech_score = float(tech_out.get("score", 50.0)) if isinstance(tech_out, dict) else 50.0
    fund_score = float(fund_out.get("score", 50.0)) if isinstance(fund_out, dict) else 50.0

    # ── Pattern and indicator data ─────────────────────────────────────── #
    patterns_raw     = tech_evaluation.get("patterns", []) or []
    key_ind          = tech_evaluation.get("key_indicators", {}) or {}
    signal_alignment = tech_evaluation.get("signal_alignment", {}) or {}
    patterns_formed  = _format_patterns(patterns_raw)

    # Common base for all returns
    _base = dict(
        cutoff_date         = cutoff_date.isoformat(),
        target_days_requested = target_days,
        sentiment           = orch_signal,
        confidence_score    = round(orch_score, 1),
        confidence_pct      = round(orch_confidence * 100, 1),
        tech_score          = round(tech_score, 1),
        fund_score          = round(fund_score, 1),
        fusion_weights      = weights,
        conflict_detected   = conflict,
        conflict_resolution = conflict_res,
        patterns            = patterns_formed,
        signal_alignment    = signal_alignment,
        orchestrator_score  = round(orch_score, 1),
        orchestrator_confidence = round(orch_confidence, 3),
    )

    # ── Gate 1: orchestrator must be bullish ──────────────────────────────
    if orch_signal != "bullish":
        return {**_base, "trade": None,
                "no_trade_reason": f"Orchestrator signal is {orch_signal} — LONG trade not applicable"}

    # ── Gate 2: confirmed bullish breakout pattern required ───────────────
    best = _select_best_pattern(patterns_raw)
    if best is None:
        return {**_base, "trade": None,
                "no_trade_reason": "No confirmed bullish pattern breakout — no structural entry basis"}

    breakout_price   = float(best["breakout_price"])
    pattern_end_date = _parse_date(best.get("end_date"))
    pattern_target   = best.get("pattern_target")
    pattern_target   = float(pattern_target) if pattern_target is not None else None

    # ── Gate 3a: failed breakout — price has reversed below breakout level ─
    current_price = bars[-1].close if bars else breakout_price
    if current_price < breakout_price:
        return {**_base, "trade": None,
                "no_trade_reason": (
                    f"Failed breakout — current price {current_price:.2f} is below "
                    f"breakout level {breakout_price:.2f}; pattern has reversed"
                )}

    # ── Find the true breakout bar in bars array ──────────────────────────
    true_breakout_idx: Optional[int] = None
    if pattern_end_date is not None:
        true_breakout_idx = _find_true_breakout_bar_idx(
            bars, breakout_price, after_date=pattern_end_date
        )
    # Fallback: scan from the very beginning if end_date is unavailable
    if true_breakout_idx is None:
        for i, b in enumerate(bars):
            if b.close > breakout_price:
                true_breakout_idx = i
                break

    if true_breakout_idx is None:
        return {**_base, "trade": None,
                "no_trade_reason": "Breakout confirmed but breakout bar not found in available data"}

    true_breakout_date = bars[true_breakout_idx].bar_date

    # ── Gate 3b: staleness check ──────────────────────────────────────────
    days_since_breakout = _count_trading_days_between(true_breakout_date, cutoff_date)

    if days_since_breakout > _STALE_DAYS_THRESHOLD:
        if pattern_target is not None and pattern_target > breakout_price:
            full_move = pattern_target - breakout_price
            consumed  = (current_price - breakout_price) / full_move
            if consumed >= _STALE_MOVE_CONSUMED:
                return {**_base, "trade": None,
                        "no_trade_reason": (
                            f"Pattern breakout is stale ({days_since_breakout} trading days ago) "
                            f"and {consumed * 100:.0f}% of measured move already consumed"
                        )}
        else:
            # No pattern target to verify setup quality → reject if stale
            return {**_base, "trade": None,
                    "no_trade_reason": (
                        f"Pattern breakout is stale ({days_since_breakout} trading days ago) "
                        f"and no measured-move target to verify remaining upside"
                    )}

    # ── Entry: next trading day after the breakout bar ────────────────────
    entry_date = _next_trading_day(true_breakout_date)

    # Find entry bar in bars array (first bar on or after entry_date)
    entry_bar_idx = _bar_index_on_or_after(bars, entry_date)
    if entry_bar_idx is None:
        # Entry date is beyond available bars (breakout on last bar)
        entry_bar_idx = len(bars) - 1
        entry_price   = round(bars[-1].close, 2)
        entry_date    = _next_trading_day(bars[-1].bar_date)
    else:
        entry_price = round(bars[entry_bar_idx].open, 2)
        entry_date  = bars[entry_bar_idx].bar_date

    # ── Gate 4: live prediction anchor ───────────────────────────────────
    # If the computed entry is before the cutoff, we would have had to enter
    # in the past. Re-anchor to the next tradeable day after cutoff.
    if entry_date < cutoff_date:
        entry_date    = _next_trading_day(cutoff_date)
        new_bar_idx   = _bar_index_on_or_after(bars, entry_date)
        if new_bar_idx is not None:
            entry_bar_idx = new_bar_idx
            entry_price   = round(bars[entry_bar_idx].open, 2)
            entry_date    = bars[entry_bar_idx].bar_date
        else:
            # Entry is in the future — no bar yet (normal for live predictions)
            entry_bar_idx = len(bars) - 1
            entry_price   = round(bars[-1].close, 2)  # last close as best estimate

    # ── ATR from indicators ───────────────────────────────────────────────
    atr = key_ind.get("atr_14")
    atr = float(atr) if atr is not None else entry_price * 0.02  # fallback 2%
    adx = key_ind.get("adx")
    rsi = key_ind.get("rsi_14")

    # ── Stop and target ───────────────────────────────────────────────────
    stop_price   = round(entry_price - ATR_STOP_MULT * atr, 2)
    # Pattern measured move takes priority over generic ATR target
    if pattern_target is not None and pattern_target > entry_price:
        target_price = round(pattern_target, 2)
    else:
        target_price = round(entry_price + ATR_TARGET_MULT * atr, 2)

    # ── Walk-forward simulation ───────────────────────────────────────────
    exit_date, exit_price, exit_outcome, bars_simulated = _simulate_trade(
        bars          = bars,
        entry_bar_idx = entry_bar_idx,
        entry_date    = entry_date,
        entry_price   = entry_price,
        stop_price    = stop_price,
        target_price  = target_price,
        max_bars      = target_days,
    )

    # OPEN = live setup with no future bars; holding_days is not yet known
    holding_days = (
        _count_trading_days_between(entry_date, exit_date) + 1
        if exit_outcome != "OPEN"
        else 0
    )

    # ── ATR-velocity estimate of days to target ──────────────────────────
    est_low, est_mid, est_high = _estimate_days_to_target(
        entry_price, target_price, atr, adx, target_days
    )
    # Trading days → calendar days: 5 trading ≈ 7 calendar (×1.4)
    est_target_date = entry_date + timedelta(days=round(est_mid * 1.4))

    # ── P&L ──────────────────────────────────────────────────────────────
    gross_profit_pct = round((exit_price - entry_price) / entry_price * 100.0, 2)
    net_profit_pct   = round(gross_profit_pct - _FRICTION_PCT, 2)
    risk_pct         = round((entry_price - stop_price) / entry_price * 100.0, 2)
    reward_pct       = round((target_price - entry_price) / entry_price * 100.0, 2)
    rr_ratio         = round(reward_pct / risk_pct, 2) if risk_pct > 0 else None

    # ── Build trade sub-object ────────────────────────────────────────────
    trade = {
        "entry_date":       entry_date.isoformat(),
        "entry_price":      entry_price,
        "entry_source":     f"pattern:{best.get('name', 'unknown')}",
        "exit_date":        exit_date.isoformat(),
        "exit_price":       exit_price,
        "exit_outcome":     exit_outcome,
        "holding_days":     holding_days,
        "bars_simulated":   bars_simulated,
        "stop_loss":        stop_price,
        "target_price":     target_price,
        "gross_profit_pct": gross_profit_pct,
        "net_profit_pct":   net_profit_pct,
        "risk_pct":         risk_pct,
        "reward_risk_ratio": rr_ratio,
        "atr_at_entry":     round(atr, 2),
        "adx_at_entry":     adx,
        "rsi_at_entry":     rsi,
        "true_breakout_date": true_breakout_date.isoformat(),
        "days_since_breakout": days_since_breakout,
        "friction_pct":     _FRICTION_PCT,
        "estimated_days_to_target": est_mid,
        "estimated_target_window":  f"{est_low}–{est_high} trading days",
        "estimated_target_date":    est_target_date.isoformat(),
    }

    return {**_base, "trade": trade, "no_trade_reason": None}


# ---------------------------------------------------------------------------
# Helpers: format patterns for output
# ---------------------------------------------------------------------------

def _format_patterns(patterns_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format pattern dicts for clean output — include all new structural fields."""
    return [
        {
            "name":                 p.get("name") or p.get("pattern_name", ""),
            "direction":            p.get("direction", ""),
            "confidence":           p.get("confidence", 0.0),
            "formation_start":      p.get("start_date"),
            "formation_end":        p.get("end_date"),
            "breakout_confirmed":   p.get("breakout_confirmed", False),
            "volume_confirmation":  p.get("volume_confirmation", False),
            "breakout_price":       p.get("breakout_price"),
            "breakout_date":        p.get("breakout_date"),
            "pattern_target":       p.get("pattern_target"),
            "description":          p.get("description", ""),
        }
        for p in patterns_raw
    ]
