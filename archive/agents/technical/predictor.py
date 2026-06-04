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

# Staleness: how many trading days old a breakout can be before we check consumed%
_STALE_DAYS_THRESHOLD = 10
# Staleness: ABSOLUTE maximum — any breakout older than this is ALWAYS rejected,
# regardless of how much of the measured move remains.  45 trading days ≈ 9 weeks.
_STALE_DAYS_ABSOLUTE_MAX = 45
# Staleness: if this fraction of the measured move is already consumed → skip
_STALE_MOVE_CONSUMED = 0.60

# Transaction friction (round-trip: commission + slippage)
_FRICTION_PCT = 0.20


# ---------------------------------------------------------------------------
# Helpers: trading-day calendar
# ---------------------------------------------------------------------------

# US market holidays (fixed-date and nearest-weekday observed rules).
# Extended through 2030 — add years as needed.
_US_MARKET_HOLIDAYS: set = set()

def _build_us_holidays() -> set:
    """Build a set of US market holiday dates from 2020 through 2030."""
    holidays: set = set()
    for year in range(2020, 2031):
        # New Year's Day (Jan 1, observed nearest weekday)
        holidays.add(_observed(date(year, 1, 1)))
        # MLK Day (3rd Monday of January)
        holidays.add(_nth_weekday(year, 1, 0, 3))
        # Presidents' Day (3rd Monday of February)
        holidays.add(_nth_weekday(year, 2, 0, 3))
        # Good Friday — computed from Easter
        holidays.add(_good_friday(year))
        # Memorial Day (last Monday of May)
        holidays.add(_last_weekday(year, 5, 0))
        # Juneteenth (Jun 19, observed nearest weekday)
        holidays.add(_observed(date(year, 6, 19)))
        # Independence Day (Jul 4, observed nearest weekday)
        holidays.add(_observed(date(year, 7, 4)))
        # Labor Day (1st Monday of September)
        holidays.add(_nth_weekday(year, 9, 0, 1))
        # Thanksgiving (4th Thursday of November)
        holidays.add(_nth_weekday(year, 11, 3, 4))
        # Christmas (Dec 25, observed nearest weekday)
        holidays.add(_observed(date(year, 12, 25)))
    return holidays


def _observed(d: date) -> date:
    """Return the observed market holiday date for a fixed calendar date."""
    # Saturday → Friday; Sunday → Monday
    if d.weekday() == 5:   # Saturday
        return d - timedelta(days=1)
    if d.weekday() == 6:   # Sunday
        return d + timedelta(days=1)
    return d


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Return the n-th occurrence (1-based) of *weekday* (Mon=0) in month."""
    first = date(year, month, 1)
    delta = (weekday - first.weekday()) % 7
    first_match = first + timedelta(days=delta)
    return first_match + timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Return the last occurrence of *weekday* (Mon=0) in month."""
    # Go to first day of next month, then step back
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    delta = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=delta)


def _good_friday(year: int) -> date:
    """Compute Good Friday (2 days before Easter Sunday) using the anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)
    return easter - timedelta(days=2)


# Initialise once at import time
_US_MARKET_HOLIDAYS = _build_us_holidays()


def _next_trading_day(d: date) -> date:
    """Advance to the next weekday (Mon–Fri) that is not a US market holiday."""
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5 or nxt in _US_MARKET_HOLIDAYS:
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
# Entry conviction classifier
# ---------------------------------------------------------------------------

def _entry_conviction(
    current_price: float,
    breakout_price: float,
    days_since_breakout: int,
) -> Tuple[str, float]:
    """
    Classify the entry regime based on how extended price is from the
    breakout level as of the cutoff date.

    Returns (conviction_label, price_extension_pct).

    Regimes
    ───────
    IMMEDIATE       Extension < 3%  AND  stale ≤ 3 days
                    Price hasn't run — enter Jan 2 on open.

    RETEST_ENTRY    Extension 3–8%  OR  stale 4–10 days
                    Moderate extension — wait for a pullback into the
                    retest zone (breakout ± 0.5×ATR) before entering.

    WAIT_FOR_RETEST Extension > 8%  OR  stale > 10 days
                    Price has already moved significantly — only enter
                    if/when price fully retests the breakout level.
    """
    if breakout_price <= 0:
        return "IMMEDIATE", 0.0

    extension_pct = (current_price - breakout_price) / breakout_price * 100.0

    if extension_pct < 3.0 and days_since_breakout <= 3:
        return "IMMEDIATE", extension_pct
    elif extension_pct > 8.0 or days_since_breakout > 10:
        return "WAIT_FOR_RETEST", extension_pct
    else:
        return "RETEST_ENTRY", extension_pct


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
        # Raw indicators included so SKIP rows can still show projected
        # entry/target/stop without a second API call.
        key_indicators      = key_ind,
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

    # ── Price as-of the analysis cutoff ──────────────────────────────────
    # bars may include forward bars (after cutoff) for walk-forward simulation.
    # Gates 3a and 3b must use the price AT the cutoff, not today's price.
    cutoff_bar_idx = len(bars) - 1
    for _i in range(len(bars) - 1, -1, -1):
        if bars[_i].bar_date <= cutoff_date:
            cutoff_bar_idx = _i
            break
    current_price = bars[cutoff_bar_idx].close if bars else breakout_price

    # ── Gate 3a: failed breakout — price has reversed below breakout level ─
    if current_price < breakout_price:
        return {**_base, "trade": None,
                "no_trade_reason": (
                    f"Failed breakout — price at cutoff {current_price:.2f} is below "
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

    # Hard cap: breakouts older than _STALE_DAYS_ABSOLUTE_MAX are always rejected.
    # This prevents ancient signals (months-old breakouts) from being surfaced as
    # fresh entry opportunities regardless of how much measured move remains.
    if days_since_breakout > _STALE_DAYS_ABSOLUTE_MAX:
        return {**_base, "trade": None,
                "no_trade_reason": (
                    f"Pattern breakout is too old ({days_since_breakout} trading days ago, "
                    f"max allowed: {_STALE_DAYS_ABSOLUTE_MAX} days)"
                )}

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

    # ── Entry: first trading day AFTER the analysis cutoff ────────────────
    # The signal is generated as-of `cutoff_date`. The earliest possible
    # entry is always the next trading day after cutoff — never before.
    # Bars are strictly bounded by cutoff_date (no post-cutoff data fetched).
    # entry_price is estimated from the last available bar (Dec 31 close)
    # since forward bars are intentionally not fetched.
    entry_earliest = _next_trading_day(cutoff_date)
    entry_date     = entry_earliest
    entry_bar_idx  = len(bars) - 1
    entry_price    = round(bars[-1].close, 2)  # Dec 31 close — estimate for Jan 2 open

    # ── ATR from indicators ───────────────────────────────────────────────
    atr = key_ind.get("atr_14")
    atr = float(atr) if atr is not None else entry_price * 0.02  # fallback 2%
    adx = key_ind.get("adx")
    rsi = key_ind.get("rsi_14")

    # ── Entry conviction: classify entry regime ───────────────────────────
    # Based on how extended price already is from the breakout level as of
    # cutoff_date. Determines whether a trader should:
    #   IMMEDIATE      — act on Jan 2 open (price hasn't run yet)
    #   RETEST_ENTRY   — moderate extension, wait for a pullback to retest zone
    #   WAIT_FOR_RETEST — significant extension, only enter on full retest
    conviction, price_extension_pct = _entry_conviction(
        current_price       = entry_price,
        breakout_price      = breakout_price,
        days_since_breakout = days_since_breakout,
    )

    # For retest regimes: recommended entry is at the retest zone midpoint
    retest_zone_low  = round(breakout_price - 0.5 * atr, 2)
    retest_zone_high = round(breakout_price + 0.5 * atr, 2)
    if conviction in ("RETEST_ENTRY", "WAIT_FOR_RETEST"):
        entry_price = round(breakout_price + 0.5 * atr, 2)  # zone midpoint

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
        "entry_price_note": "Estimated from Dec 31 close" if conviction == "IMMEDIATE" else "Retest zone midpoint (breakout + 0.5×ATR)",
        "entry_source":     f"pattern:{best.get('name', 'unknown')}",
        "entry_earliest":   entry_earliest.isoformat(),
        "entry_conviction": conviction,
        "price_extension_pct": round(price_extension_pct, 2),
        "retest_zone_low":  retest_zone_low,
        "retest_zone_high": retest_zone_high,
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
        "true_breakout_date":   true_breakout_date.isoformat(),
        "days_since_breakout":  days_since_breakout,
        "pattern_name":         best.get("name", ""),
        "pattern_start":        best.get("start_date"),
        "pattern_end":          best.get("end_date"),
        "pattern_breakout_price": breakout_price,
        "friction_pct":         _FRICTION_PCT,
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
