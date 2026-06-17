"""Build a complete per-agent breakdown for human decision-making."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.paths import ROOT


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

_PRIMARY_SOURCE_PREFIX = {
    "macro": ("fred:",),
    "market_summary": ("polygon:",),
    "news": ("fmp:",),
    "geopolitics": ("fmp:",),
    "phoenix": ("polygon:",),
    "fundamental": ("fmp:",),
    "insider": ("sec:", "edgar:", "fmp:"),
}


def _normalize_bullet(text: str) -> str:
    return str(text).lstrip("• ").strip()


def _dedupe_bullets(bullets: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for raw in bullets:
        key = _normalize_bullet(raw).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(_normalize_bullet(raw))
    return out


def _report_text(native: Optional[Dict[str, Any]]) -> Optional[str]:
    if not native:
        return None
    report = native.get("report")
    return str(report) if report else None


def _data_sources_from_bundle(bundle: Dict[str, Any]) -> List[str]:
    native = bundle.get("native") or {}
    envelope = bundle.get("envelope") or {}
    sources: List[str] = list(native.get("data_sources") or [])
    for src in (envelope.get("extras") or {}).get("data_sources") or []:
        if src not in sources:
            sources.append(str(src))
    return sources


def _source_tier(agent_id: str, sources: List[str]) -> str:
    prefixes = _PRIMARY_SOURCE_PREFIX.get(agent_id, ())
    if not sources:
        return "missing"
    if any(any(str(s).startswith(p) for p in prefixes) for s in sources):
        return "primary"
    if any("yfinance" in str(s) for s in sources):
        return "fallback"
    return "mixed"


def _bullets_from_bundle(bundle: Dict[str, Any]) -> List[str]:
    native = bundle.get("native") or {}
    bullets: List[str] = []
    if isinstance(native.get("bullets"), list):
        bullets.extend(str(b) for b in native["bullets"])
    return _dedupe_bullets(bullets)[:8]


def _headlines_from_native(native: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not native:
        return []
    raw = native.get("headlines")
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw[:10]:
        if isinstance(item, dict):
            out.append(dict(item))
    return out


def _build_one_liner(
    agent_id: str,
    section: Dict[str, Any],
    native: Optional[Dict[str, Any]],
    bullets: List[str],
) -> str:
    signal = section.get("signal") or section.get("phoenix_signal") or section.get("sentiment_label")
    score = section.get("score")
    score_txt = f" (score {score:.0f})" if isinstance(score, (int, float)) else ""

    if agent_id == "phoenix":
        ps = section.get("phoenix_signal") or signal or "WATCH"
        stage = section.get("stage") or "unknown stage"
        pattern = section.get("pattern")
        pat = f", {pattern}" if pattern else ""
        return f"Phoenix {ps}{score_txt} — {stage}{pat}; price-action gate for entries."

    if agent_id == "fundamental":
        name = ""
        if native:
            name = str(native.get("company_name") or native.get("name") or "").strip()
        label = f" for {name}" if name else ""
        return f"Fundamentals {signal or 'neutral'}{score_txt}{label}; quality and growth composite."

    if agent_id == "macro":
        metrics = section.get("macro_metrics") or (native or {}).get("metrics") or {}
        parts: List[str] = []
        if metrics.get("fed_funds") is not None:
            parts.append(f"Fed {metrics['fed_funds']:.2f}%")
        if metrics.get("cpi_yoy_pct") is not None:
            parts.append(f"CPI {metrics['cpi_yoy_pct']:.1f}% YoY")
        if metrics.get("yield_spread_10y2y") is not None:
            parts.append(f"curve {metrics['yield_spread_10y2y']:+.2f}%")
        detail = ", ".join(parts) if parts else (bullets[0] if bullets else "limited macro data")
        return f"Macro {signal or 'neutral'}{score_txt}: {detail}."

    if agent_id == "market_summary":
        vix = section.get("vix")
        regime = section.get("vix_regime") or "unknown"
        spy = (native or {}).get("spy_change_20d_pct")
        vix_txt = f"VIX {vix:.1f} ({regime})" if isinstance(vix, (int, float)) else f"VIX {regime}"
        spy_txt = f", SPY 20d {spy:+.1f}%" if isinstance(spy, (int, float)) else ""
        return f"Market {section.get('market_wide_signal') or signal or 'neutral'}{score_txt}: {vix_txt}{spy_txt}."

    if agent_id == "news":
        count = (native or {}).get("headline_count")
        count_txt = f"{count} headlines" if count else "headlines"
        lead = bullets[0] if bullets else "no standout headline"
        if len(lead) > 100:
            lead = lead[:97] + "…"
        return f"News {signal or 'neutral'}{score_txt}: {count_txt}; {lead}."

    if agent_id == "geopolitics":
        geo_count = section.get("geo_headline_count") or 0
        lead = bullets[0] if bullets else "no geo themes flagged"
        if len(lead) > 100:
            lead = lead[:97] + "…"
        return f"Geopolitics {signal or 'neutral'}{score_txt}: {geo_count} geo headlines; {lead}."

    if agent_id == "insider":
        return f"Insider {signal or 'neutral'}{score_txt}; Form 4 common-stock sales (code S)."

    if agent_id == "sentiment":
        dims = section.get("dimensions") or {}
        dim_txt = ", ".join(f"{k}={v}" for k, v in list(dims.items())[:4]) if dims else "composite read"
        return f"Sentiment {section.get('sentiment_label') or signal or 'neutral'}{score_txt}: {dim_txt}."

    return bullets[0] if bullets else f"{agent_id.replace('_', ' ').title()} {signal or 'n/a'}{score_txt}."


def _build_insights(agent_id: str, section: Dict[str, Any], native: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    insights: List[Dict[str, str]] = []

    if agent_id == "macro":
        metrics = section.get("macro_metrics") or (native or {}).get("metrics") or {}
        mapping = [
            ("Fed funds", metrics.get("fed_funds"), metrics.get("fed_funds_date")),
            ("CPI YoY", metrics.get("cpi_yoy_pct"), None),
            ("Unemployment", metrics.get("unemployment"), metrics.get("unemployment_date")),
            ("10Y-2Y spread", metrics.get("yield_spread_10y2y"), metrics.get("yield_spread_date")),
        ]
        for label, val, dt in mapping:
            if val is not None:
                suffix = f" ({dt})" if dt else ""
                insights.append({"label": label, "value": f"{val}{suffix}"})

    if agent_id == "market_summary":
        if section.get("vix") is not None:
            insights.append({"label": "VIX", "value": f"{section['vix']} ({section.get('vix_regime', 'n/a')})"})
        for row in section.get("sector_leaders") or []:
            insights.append(
                {
                    "label": f"Leader: {row.get('label', row.get('ticker'))}",
                    "value": f"{row.get('vs_spy_20d_pct', 0):+.2f}% vs SPY (20d)",
                }
            )
        for row in section.get("sector_laggards") or []:
            insights.append(
                {
                    "label": f"Laggard: {row.get('label', row.get('ticker'))}",
                    "value": f"{row.get('vs_spy_20d_pct', 0):+.2f}% vs SPY (20d)",
                }
            )

    if agent_id == "news":
        for action in (native or {}).get("priority_actions") or []:
            insights.append(
                {
                    "label": str(action.get("firm") or "Analyst"),
                    "value": f"{action.get('action')} → {action.get('grade')} ({action.get('date')})",
                }
            )
        subscores = (native or {}).get("subscores") or {}
        for key, val in subscores.items():
            insights.append({"label": key.replace("_", " ").title(), "value": str(val)})

    if agent_id == "geopolitics":
        exposure = section.get("sector_exposure") or {}
        for sector, count in sorted(exposure.items(), key=lambda x: -x[1])[:4]:
            insights.append({"label": sector, "value": f"{count} keyword hit(s)"})

    if agent_id == "phoenix" and native:
        levels = native.get("trade_levels") or {}
        for key in ("entry", "stop", "target"):
            if levels.get(key) is not None:
                insights.append({"label": key.title(), "value": str(levels[key])})

    if agent_id == "fundamental" and native:
        es = native.get("experimental_score") or {}
        if es.get("total") is not None:
            insights.append({"label": "Experimental score", "value": str(es.get("total"))})

    if agent_id == "insider" and native:
        metrics = native.get("metrics") or section.get("metrics") or {}
        if metrics.get("sell_value"):
            insights.append({"label": "Total sold", "value": f"${metrics['sell_value']:,.0f}"})
        if metrics.get("total_shares_sold"):
            avg = metrics.get("avg_sale_price")
            avg_txt = f" @ avg ${avg:,.2f}" if avg else ""
            period = ""
            first_d = metrics.get("first_sale_date")
            last_d = metrics.get("last_sale_date")
            if first_d and last_d:
                period = f" · {first_d}" if first_d == last_d else f" · {first_d} – {last_d}"
            insights.append(
                {
                    "label": "Shares sold (all insiders)",
                    "value": f"{metrics['total_shares_sold']:,.0f}{avg_txt}{period}",
                }
            )
        for row in (native.get("per_insider_sales") or section.get("per_insider_sales") or [])[:8]:
            owner = row.get("owner") or "Insider"
            title = row.get("title")
            label = f"{owner}" + (f" ({title})" if title else "")
            period = row.get("sale_period") or row.get("last_sale_date") or ""
            period_txt = f" · {period}" if period else ""
            insights.append(
                {
                    "label": label,
                    "value": (
                        f"${row.get('dollars', 0):,.0f} · "
                        f"{row.get('shares', 0):,.0f} sh @ ${row.get('avg_price', 0):,.2f} · "
                        f"{row.get('sale_count', 0)} sale(s){period_txt}"
                    ),
                }
            )

    if agent_id == "sentiment":
        dims = section.get("dimensions") or {}
        for key, val in dims.items():
            insights.append({"label": key.replace("_", " ").title(), "value": str(val)})

    return insights


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
            "data_sources": _data_sources_from_bundle(bundle),
            "source_tier": _source_tier(agent_id, _data_sources_from_bundle(bundle)),
            "headlines": _headlines_from_native(native),
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
            section["recent_trades"] = native.get("recent_trades")
            section["per_insider_sales"] = native.get("per_insider_sales")

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

        section["one_liner"] = _build_one_liner(agent_id, section, native, section["bullets"])
        section["insights"] = _build_insights(agent_id, section, native)
        if agent_id == "sentiment":
            section["source_tier"] = "derived"

        sections[agent_id] = section

    data_legitimacy = [
        {
            "agent_id": aid,
            "source_tier": sections[aid].get("source_tier"),
            "data_sources": sections[aid].get("data_sources") or [],
            "data_quality": sections[aid].get("data_quality"),
        }
        for aid in ALL_AGENT_IDS
    ]

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
        "data_legitimacy": data_legitimacy,
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
        if sec.get("one_liner"):
            lines.append(f"  {sec['one_liner']}")
        if sec.get("phoenix_signal"):
            lines.append(f"  Phoenix native: {sec['phoenix_signal']}")
        if sec.get("error"):
            lines.append(f"  Error: {sec['error']}")
        for bullet in sec.get("bullets") or []:
            lines.append(f"  • {bullet}")
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


def default_breakdown_markdown_path(ticker: str, as_of_date: str) -> Path:
    """Default journal path: ``data/output/research/<date>/<TICKER>_breakdown.md``."""
    tk = ticker.strip().upper()
    return ROOT / "data" / "output" / "research" / as_of_date / f"{tk}_breakdown.md"


def render_agent_breakdown_markdown(
    breakdown: Dict[str, Any],
    *,
    fusion: Optional[Dict[str, Any]] = None,
) -> str:
    """Render ``agent_breakdown`` JSON as a human-readable markdown journal."""
    ticker = breakdown.get("ticker") or "UNKNOWN"
    as_of = breakdown.get("as_of_date") or "unknown"
    note = breakdown.get("note") or (
        "All agents run regardless of Phoenix BUY/WATCH/AVOID. "
        "Use this breakdown to decide buy, hold, or avoid."
    )
    available = breakdown.get("agents_available", 0)
    total = breakdown.get("agents_total", len(ALL_AGENT_IDS))
    decision_by = breakdown.get("decision_by", "human")

    lines: List[str] = [
        f"# Agent Breakdown — {ticker} @ {as_of}",
        "",
        f"> **Human decision mode** ({decision_by}): {note}",
        "",
        f"**Coverage:** {available}/{total} agents available",
        "",
        "---",
        "",
    ]

    agents = breakdown.get("agents") or {}
    for agent_id in ALL_AGENT_IDS:
        sec = agents.get(agent_id) or {}
        title = agent_id.replace("_", " ").title()
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"- **Status:** {sec.get('status', 'missing')}")

        signal = sec.get("signal")
        score = sec.get("score")
        if signal is not None:
            score_text = f" ({score})" if score is not None else ""
            lines.append(f"- **Signal:** {signal}{score_text}")
        elif score is not None:
            lines.append(f"- **Score:** {score}")

        if sec.get("band"):
            lines.append(f"- **Band:** {sec['band']}")
        if sec.get("confidence"):
            lines.append(f"- **Confidence:** {sec['confidence']}")
        if sec.get("phoenix_signal"):
            lines.append(f"- **Phoenix native:** {sec['phoenix_signal']}")
        if sec.get("error"):
            lines.append(f"- **Error:** {sec['error']}")

        if sec.get("one_liner"):
            lines.append("")
            lines.append(f"**Summary:** {sec['one_liner']}")

        if sec.get("data_sources"):
            lines.append(f"- **Data sources:** {', '.join(sec['data_sources'][:5])}")
            lines.append(f"- **Source tier:** {sec.get('source_tier', 'unknown')}")

        bullets = sec.get("bullets") or []
        if bullets:
            lines.append("")
            lines.append("**Key points:**")
            for bullet in bullets:
                lines.append(f"- {bullet}")

        insights = sec.get("insights") or []
        if insights:
            lines.append("")
            lines.append("**Metrics:**")
            for row in insights:
                lines.append(f"- {row.get('label')}: {row.get('value')}")

        headlines = sec.get("headlines") or []
        if headlines:
            lines.append("")
            lines.append("**Headlines:**")
            for h in headlines[:5]:
                title = h.get("title") or ""
                src = h.get("source") or ""
                dt = h.get("date") or ""
                lines.append(f"- {title} ({src}, {dt})")

        lines.append("")
        lines.append("---")
        lines.append("")

    if fusion:
        lines.append("## Fusion (reference only)")
        lines.append("")
        lines.append(
            f"- **Score:** {fusion.get('orchestrator_score')} · "
            f"**Signal:** {fusion.get('final_signal')} · "
            f"**Advisory:** {fusion.get('advisory_verdict')}"
        )
        if fusion.get("note"):
            lines.append(f"- {fusion['note']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_agent_breakdown_markdown(
    breakdown: Dict[str, Any],
    path: Union[str, Path],
    *,
    fusion: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write rendered breakdown markdown to ``path`` (creates parent dirs)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        render_agent_breakdown_markdown(breakdown, fusion=fusion),
        encoding="utf-8",
    )
    return out


def export_agent_breakdown_markdown(
    analyze_doc: Dict[str, Any],
    path: Optional[Union[str, Path]] = None,
) -> Path:
    """Export ``agent_breakdown`` from a full-fusion analyze JSON document."""
    breakdown = analyze_doc.get("agent_breakdown")
    if not breakdown:
        raise ValueError("analyze document missing agent_breakdown (use --fusion full)")

    ticker = breakdown.get("ticker") or analyze_doc.get("ticker", "UNKNOWN")
    as_of = breakdown.get("as_of_date") or analyze_doc.get("as_of_date", "unknown")
    out = Path(path) if path else default_breakdown_markdown_path(ticker, as_of)
    return write_agent_breakdown_markdown(breakdown, out, fusion=analyze_doc.get("fusion"))
