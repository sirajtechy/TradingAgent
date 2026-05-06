"""
reporting.py — Human-readable text report builder for the Phoenix Agent.

Converts a PhoenixSignal (or its dict equivalent) into a formatted,
terminal-ready multi-line report that mirrors the style of the Technical
and Fundamental agents.

Public API
──────────
  build_text_report(signal) → str
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from .models import (
    EntrySetup,
    PatternMatch,
    PhoenixSignal,
    RiskLevels,
    StageResult,
)


# ─────────────────────────────────────────────────────────────────────────────
# Signal → visual cues
# ─────────────────────────────────────────────────────────────────────────────

_SIGNAL_ARROW = {"BUY": "▲▲", "WATCH": "►", "AVOID": "▼▼"}
_SIGNAL_BAR   = {"BUY": "█████", "WATCH": "███░░", "AVOID": "█░░░░"}
_STAGE_EMOJI  = {1: "○", 2: "●", 3: "◑", 4: "○"}


def build_text_report(signal: PhoenixSignal) -> str:
    """
    Build a formatted text report from a PhoenixSignal.

    Returns a multi-line string ready for terminal printing or JSON embedding.
    """
    lines: List[str] = []
    sep  = "─" * 62
    sep2 = "═" * 62

    arrow = _SIGNAL_ARROW.get(signal.signal, "●")
    bar   = _SIGNAL_BAR.get(signal.signal, "░░░░░")

    # ── Header ────────────────────────────────────────────────────────────
    lines.append(sep2)
    lines.append(f"  Phoenix Agent  ·  {signal.ticker}  ·  {signal.as_of_date.isoformat()}")
    lines.append(sep2)
    lines.append("")
    lines.append(f"  Signal:   {arrow}  {signal.signal}   [{bar}]   Score: {signal.score:.1f} / 100")
    lines.append("")

    # ── Hard filter status ────────────────────────────────────────────────
    if not signal.hard_filter_passed:
        lines.append(f"  ✗  HARD FILTER FAILED: {signal.hard_filter_reason}")
        lines.append("")

    # ── Stage ─────────────────────────────────────────────────────────────
    st = signal.stage
    stage_icon = _STAGE_EMOJI.get(st.stage, "○")
    lines.append(sep)
    lines.append("  STAGE ANALYSIS")
    lines.append(sep)
    lines.append(f"  {stage_icon}  Stage {st.stage} — {st.label}  |  Action: {st.action}")
    lines.append(f"  MA Alignment (P>20>50>200): {'YES ✓' if st.ma_alignment else 'NO  ✗'}")
    slopes_str = "  ".join(
        f"{k.upper()}: {v}" for k, v in st.ma_slopes.items()
    )
    lines.append(f"  Slopes: {slopes_str}")
    if st.notes:
        for note in st.notes[:4]:
            lines.append(f"    · {note}")
    lines.append("")

    # ── Score breakdown ───────────────────────────────────────────────────
    lines.append(sep)
    lines.append("  SCORE BREAKDOWN  (no RSI / MACD / Bollinger)")
    lines.append(sep)
    bd = signal.score_breakdown
    _score_bar = lambda pts, max_pts: "█" * int(pts / max_pts * 10) + "░" * (10 - int(pts / max_pts * 10))
    vol_pts  = bd.get("volume",    0)
    str_pts  = bd.get("structure", 0)
    pat_pts  = bd.get("pattern",   0)
    stg_pts  = bd.get("stage",     0)
    lines.append(f"  Volume    (40%) {_score_bar(vol_pts,  40)  } {vol_pts:>5.1f} / 40")
    lines.append(f"  Structure (30%) {_score_bar(str_pts,  30)  } {str_pts:>5.1f} / 30")
    lines.append(f"  Pattern   (20%) {_score_bar(pat_pts,  20)  } {pat_pts:>5.1f} / 20")
    lines.append(f"  Stage     (10%) {_score_bar(stg_pts,  10)  } {stg_pts:>5.1f} / 10")
    # Sub-components
    lines.append(f"    Vol trend: {bd.get('_vol_trend', 0):.1f}  "
                 f"Breakout vol: {bd.get('_breakout_vol', 0):.1f}  "
                 f"Base dryup: {bd.get('_base_dryup', 0):.1f}")
    lines.append(f"    Above 200DMA: {bd.get('_above_200dma', 0):.0f}  "
                 f"MA align: {bd.get('_ma_alignment', 0):.0f}  "
                 f"MA slopes: {bd.get('_ma_slopes', 0):.0f}  "
                 f"Proximity: {bd.get('_proximity_ma20', 0):.0f}")
    lines.append("")

    # ── Pattern ───────────────────────────────────────────────────────────
    if signal.pattern:
        pat = signal.pattern
        lines.append(sep)
        lines.append("  PATTERN DETECTION")
        lines.append(sep)
        confirmed_str = "CONFIRMED ✓" if pat.confirmed else "pending ○"
        vol_str       = "vol ✓" if pat.volume_confirmed else "vol ✗"
        lines.append(f"  Pattern:   {pat.pattern_name}")
        lines.append(f"  Status:    {confirmed_str}  |  {vol_str}")
        lines.append(f"  Pivot:     ${pat.pivot_price:.2f}")
        lines.append(f"  Confidence:{pat.confidence:.0%}")
        lines.append(f"  Depth:     {pat.base_depth_pct * 100:.1f}%")
        if pat.vcp_contractions:
            lines.append(f"  VCP contractions: {pat.vcp_contractions}")
        lines.append(f"  · {pat.description}")
        lines.append("")

    # ── Entry ─────────────────────────────────────────────────────────────
    if signal.entry and signal.entry.entry_type != "none":
        ent = signal.entry
        lines.append(sep)
        lines.append("  ENTRY SETUP")
        lines.append(sep)
        lines.append(f"  Type:      {ent.entry_type.replace('_', ' ').title()}")
        lines.append(f"  Price:     ${ent.entry_price:.2f}")
        lines.append(f"  · {ent.trigger_description}")
        lines.append("")

    # ── Risk ──────────────────────────────────────────────────────────────
    if signal.risk:
        rsk = signal.risk
        lines.append(sep)
        lines.append("  RISK MANAGEMENT")
        lines.append(sep)
        lines.append(f"  Stop (LOC):    ${rsk.stop_price:.2f}  ({rsk.stop_pct * 100:.1f}% risk)")
        lines.append(f"  Target 1:      ${rsk.target_1:.2f}  (1× measured move)")
        lines.append(f"  Target 2:      ${rsk.target_2:.2f}  (1.5× measured move)")
        lines.append(f"  Reward / Risk: {rsk.reward_risk:.2f}×")
        if rsk.position_size_shares is not None:
            lines.append(f"  Position size: {rsk.position_size_shares:.0f} shares  (1% capital risk on $100k)")
        lines.append(f"  Trail stop:    {rsk.trail_stop_ma}")
        lines.append("")

    # ── Warnings ──────────────────────────────────────────────────────────
    if signal.warnings:
        lines.append(sep)
        lines.append("  NOTES & WARNINGS")
        lines.append(sep)
        for w in signal.warnings:
            lines.append(f"  ⚠  {w}")
        lines.append("")

    lines.append(sep2)
    lines.append(f"  Phoenix Agent — @pheonix_trader strategy  ·  No RSI / MACD / Bollinger")
    lines.append(sep2)

    return "\n".join(lines)
