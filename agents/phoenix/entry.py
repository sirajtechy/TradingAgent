"""
entry.py — Entry type mapper for the Phoenix Agent.

Phoenix Trader uses 4 distinct entry methods.  This module maps the detected
PatternMatch to the correct entry type and computes the recommended entry price.

Priority order (first match wins):
  1. Standard Breakout  — VCP / Flat Base / Tight Flag + volume confirmed
  2. Pivot Breakout     — VCP pivot inside a larger base (volume not yet confirmed)
  3. Shakeout Entry     — Shakeout pattern (snap-back already confirmed)
  4. Pullback Entry     — Pullback to MA10 or MA20

If no pattern qualifies (PatternMatch.pattern_name == 'None'), returns a
'none' EntrySetup so downstream scoring/risk nodes degrade gracefully.

Public API
──────────
  evaluate_entry(pattern, snapshot, settings) → EntrySetup
"""

from __future__ import annotations

from .config import PhoenixSettings
from .models import EntrySetup, PatternMatch, PhoenixSnapshot


def evaluate_entry(
    pattern: PatternMatch,
    snapshot: PhoenixSnapshot,
    settings: PhoenixSettings | None = None,
) -> EntrySetup:
    """
    Map a detected PatternMatch to a Phoenix entry type.

    Parameters
    ----------
    pattern:   Best PatternMatch from detect_all_patterns().
    snapshot:  PhoenixSnapshot (used for current price and SMA values).
    settings:  PhoenixSettings; uses defaults if None.

    Returns
    -------
    EntrySetup with entry_type, entry_price, and trigger_description.
    """
    if settings is None:
        settings = PhoenixSettings()

    name     = pattern.pattern_name
    price    = snapshot.as_of_price
    smas     = snapshot.smas

    # ── No pattern ────────────────────────────────────────────────────────
    if name == "None" or pattern.pivot_price <= 0:
        return EntrySetup(
            entry_type="none",
            entry_price=price,
            trigger_description="No qualifying entry setup detected.",
        )

    # ── Priority 1 — Standard Breakout ───────────────────────────────────
    # VCP, Flat Base, Tight Flag that have volume confirmation AND price breakout
    if name in ("VCP", "Flat Base", "Tight Flag") and pattern.confirmed:
        return EntrySetup(
            entry_type="standard_breakout",
            entry_price=round(pattern.pivot_price * 1.001, 4),  # 0.1% above pivot (chase buffer)
            trigger_description=(
                f"{name} breakout confirmed: close above pivot ${pattern.pivot_price:.2f} "
                f"on {'>=' if pattern.volume_confirmed else '<'} 2× average volume. "
                f"Enter at market or limit ${pattern.pivot_price * 1.001:.2f}."
            ),
        )

    # ── Priority 2 — Pivot Breakout ───────────────────────────────────────
    # VCP or Flat Base detected but volume not yet confirmed — wait for trigger
    if name in ("VCP", "Flat Base", "Tight Flag") and not pattern.confirmed:
        # For VCP with multiple contractions, the pivot is inside a larger base
        if name == "VCP" and pattern.vcp_contractions >= 2:
            entry_label = "Pivot Breakout (VCP multi-contraction)"
        else:
            entry_label = "Pivot Breakout"

        return EntrySetup(
            entry_type="pivot_breakout",
            entry_price=round(pattern.pivot_price, 4),
            trigger_description=(
                f"{entry_label}: set alert at pivot ${pattern.pivot_price:.2f}. "
                f"{'Price not yet above pivot.' if snapshot.as_of_price <= pattern.pivot_price else 'Price above pivot but volume unconfirmed.'} "
                f"Buy when close > ${pattern.pivot_price:.2f} on 2× volume."
            ),
        )

    # ── Priority 3 — Shakeout Entry ───────────────────────────────────────
    if name == "Shakeout":
        # Entry is on the snap-back — already at current price or just above support
        support_level = pattern.pivot_price  # pivot_price = the support level
        entry_price   = max(price, support_level * 1.001)  # just above support
        return EntrySetup(
            entry_type="shakeout",
            entry_price=round(entry_price, 4),
            trigger_description=(
                f"Shakeout entry: snap-back above support ${support_level:.2f} confirmed. "
                f"Enter at or near current price ${price:.2f}. "
                f"Stop: below the shakeout low."
            ),
        )

    # ── Priority 4 — Pullback Entry ───────────────────────────────────────
    if name == "Pullback":
        # Pivot price is the MA level (MA10 or MA20)
        ma_level = pattern.pivot_price
        entry_price = price  # enter at current price (bounce has started)

        # Identify which MA from description
        ma_name = "MA10" if "MA10" in pattern.description else "MA20"
        sma_val = smas.sma10 if ma_name == "MA10" else smas.sma20

        return EntrySetup(
            entry_type="pullback",
            entry_price=round(entry_price, 4),
            trigger_description=(
                f"Pullback entry to {ma_name} (${ma_level:.2f}): "
                f"price ${price:.2f} pulling back to moving average on low volume. "
                f"Enter as price bounces above {ma_name}. "
                f"Stop: daily close below {ma_name}."
            ),
        )

    # ── Fallback — should not normally reach here ─────────────────────────
    return EntrySetup(
        entry_type="none",
        entry_price=price,
        trigger_description=f"Pattern '{name}' detected but no entry rule matched.",
    )
