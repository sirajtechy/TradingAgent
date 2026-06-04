"""
extension.py — Extension / chase guardrails for Phoenix BUY signals.

Surfaces how far price has already moved on daily and weekly bars at the
signal date. Informational only — does not change BUY/WATCH/AVOID.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import PhoenixSettings
from .models import OHLCVBar, PatternMatch, PhoenixSnapshot


def _pct_change(current: float, prior: float) -> Optional[float]:
    if prior is None or prior == 0:
        return None
    return round((current - prior) / prior * 100.0, 2)


def _weekly_closes(bars: List[OHLCVBar]) -> List[float]:
    """Last close of each ISO week (Mon–Sun), oldest first."""
    if not bars:
        return []
    buckets: Dict[tuple, float] = {}
    for b in bars:
        iso = b.bar_date.isocalendar()
        key = (iso[0], iso[1])
        buckets[key] = b.close
    return [buckets[k] for k in sorted(buckets.keys())]


def compute_extension_guardrail(
    snapshot: Optional[PhoenixSnapshot],
    pattern: Optional[PatternMatch],
    settings: Optional[PhoenixSettings] = None,
) -> Dict[str, Any]:
    """
    Build extension / chase context at the signal date (no lookahead).

    Returns a JSON-safe dict with chase_risk, flags, metrics, summary, action_hint.
    """
    cfg = settings or PhoenixSettings()
    empty_metrics: Dict[str, Any] = {
        "daily_change_1d_pct": None,
        "daily_change_5d_pct": None,
        "daily_change_10d_pct": None,
        "weekly_change_1w_pct": None,
        "weekly_change_4w_pct": None,
        "pct_above_sma20": None,
        "pct_above_sma50": None,
        "pct_from_pivot": None,
    }

    if snapshot is None or not snapshot.bars:
        return {
            "chase_risk": "unknown",
            "flags": [],
            "metrics": empty_metrics,
            "summary": "Insufficient bar data for extension check.",
            "action_hint": None,
        }

    bars = snapshot.bars
    price = snapshot.as_of_price
    smas = snapshot.smas
    metrics = dict(empty_metrics)

    if len(bars) >= 2:
        metrics["daily_change_1d_pct"] = _pct_change(price, bars[-2].close)
    if len(bars) >= 6:
        metrics["daily_change_5d_pct"] = _pct_change(price, bars[-6].close)
    if len(bars) >= 11:
        metrics["daily_change_10d_pct"] = _pct_change(price, bars[-11].close)

    weekly = _weekly_closes(bars)
    if len(weekly) >= 2:
        metrics["weekly_change_1w_pct"] = _pct_change(weekly[-1], weekly[-2])
    if len(weekly) >= 5:
        metrics["weekly_change_4w_pct"] = _pct_change(weekly[-1], weekly[-5])

    if smas.sma20 is not None and smas.sma20 > 0:
        metrics["pct_above_sma20"] = round((price - smas.sma20) / smas.sma20 * 100.0, 2)
    if smas.sma50 is not None and smas.sma50 > 0:
        metrics["pct_above_sma50"] = round((price - smas.sma50) / smas.sma50 * 100.0, 2)

    pivot = pattern.pivot_price if pattern and pattern.pattern_name != "None" else None
    if pivot and pivot > 0:
        metrics["pct_from_pivot"] = round((price - pivot) / pivot * 100.0, 2)

    flags: List[str] = []
    d5 = metrics["daily_change_5d_pct"]
    d10 = metrics["daily_change_10d_pct"]
    w1 = metrics["weekly_change_1w_pct"]
    w4 = metrics["weekly_change_4w_pct"]
    above20 = metrics["pct_above_sma20"]
    above50 = metrics["pct_above_sma50"]
    from_pivot = metrics["pct_from_pivot"]

    if d5 is not None and d5 >= cfg.extension_daily_warn_pct:
        flags.append("daily_up_5pct_5d")
    if d10 is not None and d10 >= cfg.extension_daily_severe_pct:
        flags.append("daily_up_10pct_10d")
    if w1 is not None and w1 >= cfg.extension_weekly_warn_pct:
        flags.append("weekly_up_5pct_1w")
    if w4 is not None and w4 >= cfg.extension_weekly_severe_pct:
        flags.append("weekly_up_10pct_4w")
    if above20 is not None and above20 > 10.0:
        flags.append("extended_above_sma20")
    if above50 is not None and above50 > 15.0:
        flags.append("extended_above_sma50")
    if from_pivot is not None and from_pivot > 5.0:
        flags.append("extended_from_pivot")

    severity = 0
    if d10 is not None and d10 >= cfg.extension_daily_severe_pct:
        severity += 2
    elif d5 is not None and d5 >= cfg.extension_daily_warn_pct:
        severity += 1
    if w4 is not None and w4 >= cfg.extension_weekly_severe_pct:
        severity += 2
    elif w1 is not None and w1 >= cfg.extension_weekly_warn_pct:
        severity += 1
    if from_pivot is not None and from_pivot > 8.0:
        severity += 1

    if severity >= 3:
        chase_risk = "elevated"
    elif severity >= 1:
        chase_risk = "moderate"
    else:
        chase_risk = "low"

    parts: List[str] = []
    if d5 is not None:
        parts.append(f"{d5:+.1f}% over 5 daily bars")
    if w4 is not None:
        parts.append(f"{w4:+.1f}% over 4 weeks")
    if above20 is not None:
        parts.append(f"{above20:+.1f}% above SMA20")

    if parts:
        summary = (
            f"Extension check: price already moved ({', '.join(parts)}). "
            f"Chase risk: {chase_risk}."
        )
    else:
        summary = f"Extension check: no significant recent extension. Chase risk: {chase_risk}."

    justification_parts: List[str] = []
    if d5 is not None:
        justification_parts.append(f"5d {d5:+.1f}%")
    if d10 is not None:
        justification_parts.append(f"10d {d10:+.1f}%")
    if w4 is not None:
        justification_parts.append(f"4w {w4:+.1f}%")
    if above20 is not None:
        justification_parts.append(f"vs SMA20 {above20:+.1f}%")
    if from_pivot is not None and from_pivot > 0:
        justification_parts.append(f"vs pivot {from_pivot:+.1f}%")
    justification = (
        " · ".join(justification_parts) if justification_parts else "Flat vs recent bars (no 5%+ move)"
    )

    if chase_risk == "elevated":
        action_hint = (
            "BUY setup valid but price is extended — consider smaller size, "
            "limit entry, or wait for pullback toward SMA20."
        )
    elif chase_risk == "moderate":
        action_hint = "BUY setup valid with moderate extension — use disciplined entry and stop."
    else:
        action_hint = "Extension low relative to thresholds — standard entry rules apply."

    return {
        "chase_risk": chase_risk,
        "flags": flags,
        "metrics": metrics,
        "summary": summary,
        "justification": justification,
        "action_hint": action_hint,
    }
