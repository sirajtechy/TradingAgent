"""Build a complete per-agent breakdown for human decision-making."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


ALL_AGENT_IDS = (
    "phoenix",
    "fundamental",
    "macro",
    "market_summary",
    "geopolitics",
    "news",
    "insider",
    "sentiment",
)


def _report_text(native: Optional[Dict[str, Any]]) -> Optional[str]:
    if not native:
        return None
    report = native.get("report")
    return str(report) if report else None


def _bullets_from_bundle(bundle: Dict[str, Any]) -> List[str]:
    native = bundle.get("native") or {}
    envelope = bundle.get("envelope") or {}
    bullets: List[str] = []
    for source in (native, envelope.get("extras") or {}):
        if isinstance(source.get("bullets"), list):
            bullets.extend(str(b) for b in source["bullets"])
    return bullets[:6]


def build_agent_breakdown(
    agents: Dict[str, Dict[str, Any]],
    *,
    ticker: str,
    as_of_date: str,
) -> Dict[str, Any]:
    """
    Structured breakdown of every agent for human review.

    No agent is omitted — failures appear with error + status unavailable.
    """
    sections: Dict[str, Any] = {}
    available_count = 0

    for agent_id in ALL_AGENT_IDS:
        bundle = agents.get(agent_id) or {}
        native = bundle.get("native")
        envelope = bundle.get("envelope")
        error = bundle.get("error")
        status = "ok" if native and envelope else ("error" if error else "missing")

        if status == "ok":
            available_count += 1

        section: Dict[str, Any] = {
            "agent_id": agent_id,
            "status": status,
            "error": error,
            "signal": (envelope or {}).get("signal") if envelope else None,
            "score": (envelope or {}).get("score") if envelope else None,
            "band": (envelope or {}).get("band") if envelope else None,
            "confidence": (envelope or {}).get("confidence") if envelope else None,
            "abstain": (envelope or {}).get("abstain") if envelope else None,
            "data_quality": (envelope or {}).get("data_quality") if envelope else None,
            "warnings": list((envelope or {}).get("warnings") or []),
            "bullets": _bullets_from_bundle(bundle),
            "report": _report_text(native),
            "extras": dict((envelope or {}).get("extras") or {}),
        }

        if agent_id == "phoenix" and native:
            section["phoenix_signal"] = native.get("signal")
            section["stage"] = (native.get("stage") or {}).get("label")
            section["pattern"] = native.get("pattern")
            section["hard_filter_reason"] = native.get("hard_filter_reason")
            section["extension_guardrail"] = native.get("extension_guardrail")
            section["trade_levels"] = native.get("trade_levels")

        if agent_id == "fundamental" and native:
            es = native.get("experimental_score") or {}
            section["experimental_score"] = es
            section["frameworks"] = native.get("frameworks")

        if agent_id == "sentiment" and native:
            section["sentiment_label"] = native.get("sentiment")
            section["dimensions"] = native.get("dimensions")

        if agent_id == "insider" and native:
            section["metrics"] = native.get("metrics")
            section["subscores"] = native.get("subscores")

        if agent_id == "geopolitics" and native:
            section["sector_exposure"] = native.get("sector_exposure")
            section["geo_headline_count"] = native.get("geo_headline_count")

        if agent_id == "market_summary" and native:
            section["market_wide_signal"] = native.get("market_wide_signal")
            section["vix"] = native.get("vix")
            section["vix_regime"] = native.get("vix_regime")
            section["sector_leaders"] = native.get("sector_leaders")
            section["sector_laggards"] = native.get("sector_laggards")

        if agent_id == "macro" and native:
            section["macro_metrics"] = native.get("metrics")

        sections[agent_id] = section

    return {
        "ticker": ticker,
        "as_of_date": as_of_date,
        "agents_available": available_count,
        "agents_total": len(ALL_AGENT_IDS),
        "decision_by": "human",
        "note": (
            "All agents run regardless of Phoenix BUY/WATCH/AVOID. "
            "Use this breakdown to decide buy, hold, or avoid."
        ),
        "agents": sections,
    }


def build_deterministic_digest(
    *,
    ticker: str,
    as_of_date: str,
    agents: Dict[str, Dict[str, Any]],
    fusion: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compile agent bullets into a human-readable digest without external LLM."""
    lines: List[str] = [
        f"Research digest — {ticker} @ {as_of_date}",
        "",
    ]

    breakdown = build_agent_breakdown(agents, ticker=ticker, as_of_date=as_of_date)
    for agent_id in ALL_AGENT_IDS:
        sec = breakdown["agents"][agent_id]
        header = f"[{agent_id.upper()}] status={sec['status']}"
        if sec.get("signal"):
            header += f" signal={sec['signal']} score={sec.get('score')}"
        lines.append(header)
        if sec.get("phoenix_signal"):
            lines.append(f"  Phoenix native: {sec['phoenix_signal']}")
        if sec.get("error"):
            lines.append(f"  Error: {sec['error']}")
        for bullet in sec.get("bullets") or []:
            lines.append(f"  {bullet}")
        if sec.get("report") and not sec.get("bullets"):
            first_line = str(sec["report"]).split("\n")[0][:120]
            lines.append(f"  {first_line}")
        lines.append("")

    if fusion:
        lines.append(
            f"[FUSION REFERENCE ONLY] score={fusion.get('orchestrator_score')} "
            f"signal={fusion.get('final_signal')} "
            f"(advisory: {fusion.get('advisory_verdict')})"
        )

    text = "\n".join(lines).strip()
    return {
        "sentiment": "neutral",
        "bullets": [text],
        "confidence": "medium",
        "source": "deterministic_digest",
    }
