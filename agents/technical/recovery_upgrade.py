"""
recovery_upgrade.py — Post-process Phoenix output to capture early-recovery setups.

Phoenix is a strict trend-continuation model. After a broad-market correction,
its hard gates (price > SMA200, >= +50% from 52w low) categorically reject
nearly every name even when many are mid-reversal with real alpha ahead.

This module sits OUTSIDE Phoenix and inspects each AVOID result. If the broad
market is in a post-correction recovery regime AND the individual ticker
passes a separate, narrower "reclaim" gate, the result is upgraded from AVOID
to WATCH with ``phoenix_entry_mode = "recovery_upgrade"`` so downstream
strategies and the dashboard can distinguish standard-trend setups from
recovery-mode setups.

We never upgrade to BUY — BUY in Phoenix's lexicon means "full conviction
trend continuation", which is structurally incompatible with a name still
inside its 200-day downtrend. WATCH means "actionable but with caveats" —
the right semantic for a reversal entry.

The reclaim gate is "is this name participating in the broader recovery?"
NOT "has this name fully re-established a Stage-2 trend?" In a sharp crash
(2025-04, 2020-03, 2022-Q4) even names that go on to deliver +20pp alpha
spend the first 2-3 weeks of the rebound well below SMA50 and 40%+ below
their 52w high. Trend-continuation-style gates would categorically reject
all of them — the same failure mode Phoenix already has.

The reclaim gate (all must hold):
  - Price >= ``min_bounce_off_low_pct`` (5%) above its 30-day low — real
    bounce, not just a wick.
  - Price > 7-session-prior price — positive medium-term momentum.
  - No new 20-day low in last ``new_low_lookback`` (5) sessions — downtrend
    break confirmed.
  - Above EMA10 OR EMA10 reclaimed in last ``ema10_reclaim_window`` (3)
    sessions — currently in early uptrend.
  - At least one up-day in last 5 sessions with volume >= ``vol_confirm_mult``
    (1.3x) of the 20-day pre-bounce baseline — institutional confirmation.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from agents.phoenix.models import PhoenixSnapshot
from agents.strategies.common.features import ema_at, sma_at, slope_rising
from agents.strategies.common.recovery_regime import detect_recovery_regime

_MIN_BOUNCE_OFF_LOW_PCT = 5.0
_BOUNCE_LOW_WINDOW = 30
_EMA10_RECLAIM_WINDOW = 5
_NEW_LOW_LOOKBACK = 5
_NEW_LOW_WINDOW = 20
_VOL_CONFIRM_MULT = 1.20
# Volume baseline uses 90 days BEFORE the drawdown window starts. Trailing
# 30-day averages are contaminated by panic-day volume and inflate the
# baseline by 2-3x, making subsequent normal volume look weak.
_VOL_BASELINE_DAYS = 90
_VOL_BASELINE_GAP = 30


def maybe_upgrade_phoenix(
    phoenix_result: Dict[str, Any],
    snapshot: Optional[PhoenixSnapshot],
    spy_snapshot: Optional[PhoenixSnapshot],
) -> Dict[str, Any]:
    """
    If Phoenix is AVOID due to hard-filter failure AND the market is in
    post-correction recovery AND this ticker passes the reclaim gate, upgrade
    the result to WATCH with provenance fields. Otherwise return the result
    unchanged.

    Always sets ``phoenix_entry_mode`` to ``"standard"`` or
    ``"recovery_upgrade"`` so downstream code can branch on it without parsing
    other fields.
    """
    if not isinstance(phoenix_result, dict):
        return phoenix_result

    result = deepcopy(phoenix_result)
    result.setdefault("phoenix_entry_mode", "standard")
    result.setdefault("recovery_regime", None)
    result.setdefault("recovery_reclaim", None)

    # Only consider upgrading AVOID-due-to-hard-filter results
    raw_signal = str(result.get("signal") or "").upper()
    hard_pass = bool(result.get("hard_filter_passed"))
    if raw_signal != "AVOID" or hard_pass:
        return result

    if snapshot is None or spy_snapshot is None:
        return result

    regime = detect_recovery_regime(spy_snapshot)
    result["recovery_regime"] = regime
    if not regime.get("is_recovery"):
        return result

    reclaim = _evaluate_reclaim_gate(snapshot)
    result["recovery_reclaim"] = reclaim
    if not reclaim.get("passes"):
        return result

    result["signal"] = "WATCH"
    result["phoenix_entry_mode"] = "recovery_upgrade"
    result["hard_filter_reason"] = (
        f"Standard trend gate failed ({result.get('hard_filter_reason') or 'see filters'}) "
        "but reclaim gate passed in post-correction recovery regime."
    )
    warnings = list(result.get("warnings") or [])
    warnings.append(
        "Phoenix upgraded AVOID → WATCH via recovery pathway (Stage 1 → 2 transition). "
        "Position size tighter than standard-trend setups."
    )
    result["warnings"] = warnings
    return result


def _evaluate_reclaim_gate(snapshot: PhoenixSnapshot) -> Dict[str, Any]:
    """Per-ticker checks for credible participation in a market-wide recovery."""
    bars = snapshot.bars or []
    if len(bars) < 50:
        return {"passes": False, "reason": "insufficient_bars", "checks": []}

    closes = [b.close for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]
    price = closes[-1]

    checks: List[Tuple[str, bool, str]] = []

    # 1. Real bounce: price >= 5% above its 30-day low (filters out names
    # still pinned to their lows that haven't participated in the bounce).
    window_low = min(lows[-_BOUNCE_LOW_WINDOW:]) if len(lows) >= _BOUNCE_LOW_WINDOW else min(lows)
    bounce_pct = ((price - window_low) / window_low * 100.0) if window_low > 0 else 0.0
    bounce_ok = bounce_pct >= _MIN_BOUNCE_OFF_LOW_PCT
    checks.append((
        "bounce_off_30d_low",
        bounce_ok,
        f"{bounce_pct:.1f}% above 30d low (need >= {_MIN_BOUNCE_OFF_LOW_PCT:.1f}%)",
    ))

    # 2. No new 20-day low in last 5 sessions — downtrend break confirmed.
    no_new_low = True
    if len(lows) >= _NEW_LOW_WINDOW + _NEW_LOW_LOOKBACK:
        for i in range(-_NEW_LOW_LOOKBACK, 0):
            recent_low = lows[i]
            window_low_check = min(lows[i - _NEW_LOW_WINDOW + 1:i])
            if recent_low < window_low_check:
                no_new_low = False
                break
    checks.append(("no_recent_new_low", no_new_low, f"no 20d low in last {_NEW_LOW_LOOKBACK}d"))

    # 3. Currently in early EMA10 uptrend: above EMA10 OR just crossed it.
    ema10 = ema_at(bars, 10)
    above_ema10 = ema10 is not None and price > ema10
    ema10_reclaim = False
    if not above_ema10:
        for offset in range(1, _EMA10_RECLAIM_WINDOW + 1):
            prior_ema = ema_at(bars, 10, offset=offset)
            prior_price = closes[-1 - offset] if len(closes) > offset else price
            if prior_ema is not None and prior_price <= prior_ema:
                ema10_reclaim = True
                break
    ema10_ok = above_ema10 or ema10_reclaim
    checks.append((
        "ema10_participation",
        ema10_ok,
        f"above_now={above_ema10} reclaimed_in_last_{_EMA10_RECLAIM_WINDOW}d={ema10_reclaim}",
    ))

    # 4. Volume NOT drying up — at least one up-day in last 5 sessions where
    # volume holds at >= 60% of the 90-day pre-drawdown baseline. (We do NOT
    # demand 1.2x+ "institutional re-entry" volume at the ticker level — the
    # broad-tape FTD already validated that at the index level, and recovery-
    # phase volume on individual names is naturally below pre-crash baseline
    # for the first several weeks. Demanding >= 1.2x rejects every large-cap.)
    vol_holds = False
    needed = _VOL_BASELINE_DAYS + _VOL_BASELINE_GAP + 5
    if len(volumes) >= needed:
        baseline_end = len(volumes) - _VOL_BASELINE_GAP - 5
        baseline_start = baseline_end - _VOL_BASELINE_DAYS
        vol_baseline = sum(volumes[baseline_start:baseline_end]) / _VOL_BASELINE_DAYS
        for i in range(-5, 0):
            if closes[i] <= closes[i - 1]:
                continue
            if vol_baseline > 0 and volumes[i] / vol_baseline >= 0.60:
                vol_holds = True
                break
    else:
        vol_holds = True  # insufficient history for distribution test — assume ok
    checks.append((
        "volume_not_drying_up",
        vol_holds,
        ">= 0.60x 90d pre-drawdown avg on at least one up-day in last 5d",
    ))

    passes = all(ok for _, ok, _ in checks)
    return {
        "passes": passes,
        "reason": "ok" if passes else "criteria_unmet",
        "checks": [{"name": n, "passed": ok, "detail": d} for n, ok, d in checks],
    }


def _crossed_above_sma_recently(bars, *, period: int, window: int) -> bool:
    """
    True iff price is currently > SMA(period) AND was <= SMA(period) at any
    bar within the last ``window`` sessions. Captures any reclaim of the MA
    in the window, regardless of how many sessions ago it occurred.
    """
    if len(bars) < period + 1:
        return False
    closes = [b.close for b in bars]
    if closes[-1] <= 0:
        return False
    sma_now = sum(closes[-period:]) / period
    if closes[-1] <= sma_now:
        return False
    lookback = min(window, len(closes) - period)
    for offset in range(1, lookback + 1):
        end = len(closes) - offset + 1
        start = end - period
        if start < 0:
            continue
        sma_then = sum(closes[start:end]) / period
        price_then = closes[-offset]
        if price_then <= sma_then:
            return True
    return False
