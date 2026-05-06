"""
risk.py — Risk management and position sizing for the Phoenix Agent.

Phoenix Trader risk rules:
  Stop Loss:      LOC — Low Of the breakout Candle (hard stop)
                  Stop price = LOC × (1 − stop_buffer_pct)
  Targets:        Target 1 = entry + 1.0× base height (measured move)
                  Target 2 = entry + 1.5× base height
  Position size:  (account_size × 1% capital risk) / risk_per_share
  Trailing stop:  If price > MA10 → trail on MA10
                  If MA10 broken → shift trail to MA20

'Base height' = the vertical distance of the pattern base, used as the
measured move for targets.  For VCP/Flat Base it is (base_high − base_low).
For Shakeout/Pullback it is the distance from support to the prior pivot high.

Public API
──────────
  compute_risk(entry, pattern, snapshot, settings, account_size) → RiskLevels
"""

from __future__ import annotations

from typing import Optional

from .config import PhoenixSettings
from .models import EntrySetup, PatternMatch, PhoenixSnapshot, RiskLevels


def compute_risk(
    entry: EntrySetup,
    pattern: PatternMatch,
    snapshot: PhoenixSnapshot,
    settings: PhoenixSettings | None = None,
    account_size: float = 100_000,
) -> RiskLevels:
    """
    Compute stop, targets, R/R, and position size for a Phoenix setup.

    Parameters
    ----------
    entry:        EntrySetup from evaluate_entry().
    pattern:      PatternMatch from detect_all_patterns().
    snapshot:     PhoenixSnapshot (bars, SMA values, current price).
    settings:     PhoenixSettings; uses defaults if None.
    account_size: Total account size in dollars for position sizing.

    Returns
    -------
    RiskLevels with all computed values.
    """
    if settings is None:
        settings = PhoenixSettings()

    bars         = snapshot.bars
    smas         = snapshot.smas
    entry_price  = entry.entry_price
    entry_type   = entry.entry_type

    # ── LOC Stop — Low Of breakout Candle ────────────────────────────────
    # The LOC is the low of the most recent bar (the breakout/trigger bar).
    # For pending entries (pivot_breakout) we use the current bar's low as a
    # forward-looking reference — the actual stop is set on the day of entry.
    loc_low = bars[-1].low if bars else entry_price * 0.95

    # Stop price: LOC minus a small buffer
    stop_price = round(loc_low * (1 - settings.stop_buffer_pct), 4)

    # Risk per share
    risk_per_share = entry_price - stop_price
    if risk_per_share <= 0:
        # Degenerate case: stop above entry (can happen with fractional prices)
        risk_per_share = entry_price * 0.02  # default 2% stop
        stop_price = round(entry_price - risk_per_share, 4)

    stop_pct = round(risk_per_share / entry_price, 6) if entry_price > 0 else 0.0

    # ── Base height (measured move) ───────────────────────────────────────
    base_height = _compute_base_height(pattern, snapshot, entry_price)

    # ── Targets ───────────────────────────────────────────────────────────
    target_1 = round(entry_price + base_height * settings.target_multiplier_1, 4)
    target_2 = round(entry_price + base_height * settings.target_multiplier_2, 4)

    # ── R/R ratio ─────────────────────────────────────────────────────────
    upside      = target_1 - entry_price
    downside    = entry_price - stop_price
    reward_risk = round(upside / downside, 3) if downside > 0 else 0.0

    # ── Position sizing ───────────────────────────────────────────────────
    capital_at_risk   = account_size * settings.capital_risk_pct
    position_size_shares: Optional[float] = None
    if risk_per_share > 0 and account_size > 0:
        position_size_shares = round(capital_at_risk / risk_per_share, 2)

    # ── Trailing stop MA selection ────────────────────────────────────────
    # Logic: if price is comfortably above MA10, trail on MA10.
    # If MA10 has been broken (price < MA10) or MA10 is None, use MA20.
    sma10 = smas.sma10
    sma20 = smas.sma20
    price = snapshot.as_of_price

    if sma10 is not None and price > sma10 * 1.001:
        trail_stop_ma = "MA10"
    elif sma20 is not None:
        trail_stop_ma = "MA20"
    else:
        trail_stop_ma = "MA20"

    return RiskLevels(
        stop_price=stop_price,
        stop_pct=stop_pct,
        target_1=target_1,
        target_2=target_2,
        reward_risk=reward_risk,
        position_size_shares=position_size_shares,
        trail_stop_ma=trail_stop_ma,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _compute_base_height(
    pattern: PatternMatch,
    snapshot: PhoenixSnapshot,
    entry_price: float,
) -> float:
    """
    Derive the 'measured move' height from the pattern.

    For VCP / Flat Base / Tight Flag:
        base_height = base_depth_pct × pivot_price
        (depth_pct encodes how deep the base was relative to its high)

    For Shakeout / Pullback:
        use the distance from the support level to the 20-bar prior high
        as a conservative measured move proxy.

    Minimum height: 3% of entry price (prevents near-zero targets).
    """
    name = pattern.pattern_name

    if name in ("VCP", "Flat Base", "Tight Flag") and pattern.base_depth_pct > 0:
        # base_depth_pct = (high − low) / high  →  height = depth_pct × pivot
        base_height = pattern.base_depth_pct * pattern.pivot_price

    elif name == "Shakeout":
        # Measured move: from support (pivot_price) to recent 20-bar high
        bars = snapshot.bars
        recent_high = max(b.high for b in bars[-21:]) if len(bars) >= 21 else entry_price
        base_height = recent_high - pattern.pivot_price

    elif name == "Pullback":
        # Measured move: from the MA (pivot) to the prior recent swing high
        bars = snapshot.bars
        prior_high = max(b.high for b in bars[-21:-1]) if len(bars) >= 21 else entry_price
        base_height = prior_high - pattern.pivot_price

    else:
        # No pattern or unknown — use 5% of entry as default
        base_height = entry_price * 0.05

    # Floor: at least 3% of entry price
    min_height = entry_price * 0.03
    return max(base_height, min_height)
