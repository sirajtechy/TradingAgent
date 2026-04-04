"""
reporting.py — Build human-readable text reports for orchestrator output.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .models import FusionResult


_SIGNAL_ICON = {
    "bullish": "▲ BULLISH",
    "neutral": "— NEUTRAL",
    "bearish": "▼ BEARISH",
}

_CONF_BAR = {
    # Rough confidence buckets for display
    "high": "████████░░",
    "medium": "█████░░░░░",
    "low": "██░░░░░░░░",
}


def build_text_report(
    ticker: str,
    analysis_date: str,
    fusion: FusionResult,
    tech_result: Optional[Dict[str, Any]] = None,
    fund_result: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a structured text report from the fusion result."""
    lines: list[str] = []

    lines.append(f"ORCHESTRATOR REPORT  —  {ticker.upper()}")
    lines.append("=" * 64)
    lines.append(f"Analysis date : {analysis_date or 'latest'}")
    lines.append("")

    # ── Final verdict ───────────────────────────────────────────
    icon = _SIGNAL_ICON.get(fusion.final_signal, fusion.final_signal)
    lines.append(f"  SIGNAL      : {icon}")
    lines.append(f"  SCORE       : {fusion.orchestrator_score:.1f} / 100")
    lines.append(f"  CONFIDENCE  : {fusion.final_confidence:.0%}")
    lines.append("")

    # ── Weights ─────────────────────────────────────────────────
    wt = fusion.weights_applied.get("tech", 0)
    wf = fusion.weights_applied.get("fund", 0)
    lines.append(f"  Weights     : Tech {wt:.0%}  |  Fund {wf:.0%}")

    if fusion.conflict_detected:
        lines.append(f"  Conflict    : YES  — {fusion.conflict_resolution}")
    else:
        lines.append(f"  Conflict    : No")

    if fusion.note and not fusion.conflict_detected:
        lines.append(f"  Note        : {fusion.note}")
    lines.append("")

    # ── Technical agent summary ─────────────────────────────────
    lines.append("─" * 64)
    if fusion.tech_error:
        lines.append(f"TECHNICAL AGENT : ERROR — {fusion.tech_error}")
    elif fusion.tech_output:
        t = fusion.tech_output
        lines.append(f"TECHNICAL AGENT")
        lines.append(f"  Signal      : {_SIGNAL_ICON.get(t.signal, t.signal)}")
        lines.append(f"  Score       : {t.score:.1f} / 100  [{t.band}]")
        lines.append(f"  Confidence  : {t.confidence}  (computed: {t.computed_confidence:.2f})")
        if t.subscores:
            parts = [f"{k}: {v:.0f}%" if isinstance(v, (int, float)) else f"{k}: {v}"
                     for k, v in t.subscores.items()]
            lines.append(f"  Subscores   : {' | '.join(parts)}")
    else:
        lines.append("TECHNICAL AGENT : not available")
    lines.append("")

    # ── Fundamental agent summary ───────────────────────────────
    lines.append("─" * 64)
    if fusion.fund_error:
        lines.append(f"FUNDAMENTAL AGENT : ERROR — {fusion.fund_error}")
    elif fusion.fund_output:
        f = fusion.fund_output
        lines.append(f"FUNDAMENTAL AGENT")
        lines.append(f"  Signal      : {_SIGNAL_ICON.get(f.signal, f.signal)}")
        lines.append(f"  Score       : {f.score:.1f} / 100  [{f.band}]")
        lines.append(f"  Confidence  : {f.confidence}  (computed: {f.computed_confidence:.2f})")
        if f.data_quality:
            lines.append(f"  Data quality: {f.data_quality}")
        if f.subscores:
            parts = [f"{k}: {v:.0f}%" if isinstance(v, (int, float)) else f"{k}: {v}"
                     for k, v in f.subscores.items()]
            lines.append(f"  Subscores   : {' | '.join(parts)}")
    else:
        lines.append("FUNDAMENTAL AGENT : not available")

    lines.append("")
    lines.append("=" * 64)
    return "\n".join(lines)
