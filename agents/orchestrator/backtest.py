"""
backtest.py — Monthly backtest engine for the orchestrator agent.

Runs both sub-agents per period, fuses signals via CWAF, then compares
predictions against realised price direction — identical methodology to
the individual agent backtests.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .config import OrchestratorSettings
from .fusion import fuse_signals
from .models import BAND_TO_SIGNAL


def run_monthly_backtest(
    ticker: str,
    months: List[Tuple[date, date]],
    settings: Optional[OrchestratorSettings] = None,
) -> Dict[str, Any]:
    """
    Run the orchestrator backtest over ``(signal_date, result_date)`` pairs.

    Each period:
      1. Run both agents as of ``signal_date``.
      2. Fuse signals via CWAF.
      3. Fetch month-end price at ``result_date``.
      4. Compare prediction vs actual direction.
    """
    from agents.technical.data_client import YFinanceTechnicalClient

    cfg = settings or OrchestratorSettings()
    client = YFinanceTechnicalClient()
    periods: List[Dict[str, Any]] = []

    for signal_date, result_date in months:
        period = _run_period(
            ticker=ticker,
            signal_date=signal_date,
            result_date=result_date,
            client=client,
            settings=cfg,
        )
        periods.append(period)

    directional = [p for p in periods if p["signal_correct"] is not None]
    correct_count = sum(1 for p in directional if p["signal_correct"])
    accuracy = (correct_count / len(directional) * 100.0) if directional else None

    n = len(periods)
    return {
        "ticker": ticker.upper(),
        "periods": periods,
        "summary": {
            "total_periods": n,
            "directional_signals": len(directional),
            "correct_signals": correct_count,
            "accuracy_pct": round(accuracy, 1) if accuracy is not None else None,
            "warning": (
                f"This covers {n} month{'s' if n != 1 else ''} on one stock. "
                f"{n} data point{'s are' if n != 1 else ' is'} not statistically "
                "significant — use this to understand the signal behaviour, not "
                "to validate it."
            ),
        },
    }


def _run_period(
    ticker: str,
    signal_date: date,
    result_date: date,
    client: Any,
    settings: OrchestratorSettings,
) -> Dict[str, Any]:
    """Evaluate a single (signal_date → result_date) period."""
    from agents.technical.service import analyze_ticker as tech_analyze
    from agents.fundamental.service import analyze_ticker as fund_analyze

    # ── Run both agents ─────────────────────────────────────────────
    tech_result: Optional[Dict[str, Any]] = None
    tech_error: Optional[str] = None
    fund_result: Optional[Dict[str, Any]] = None
    fund_error: Optional[str] = None

    try:
        tech_result = tech_analyze(
            ticker=ticker,
            as_of_date=signal_date.isoformat(),
        )
    except Exception as exc:
        tech_error = str(exc)

    try:
        fund_result = fund_analyze(
            ticker=ticker,
            as_of_date=signal_date.isoformat(),
            data_source=settings.fund_data_source,
        )
    except Exception as exc:
        fund_error = str(exc)

    # ── Fuse signals ────────────────────────────────────────────────
    fusion = fuse_signals(
        tech_result=tech_result,
        tech_error=tech_error,
        fund_result=fund_result,
        fund_error=fund_error,
        settings=settings,
    )

    signal = fusion.final_signal

    # ── Get prices ──────────────────────────────────────────────────
    # Start price — prefer from tech result (always has price info)
    start_price = None
    start_price_date = None
    for src in (tech_result, fund_result):
        if src and "as_of_price" in src:
            start_price = src["as_of_price"]["price"]
            start_price_date = src["as_of_price"]["price_date"]
            break

    if start_price is None:
        return {
            "month": signal_date.strftime("%B %Y"),
            "signal_date": signal_date.isoformat(),
            "result_date": result_date.isoformat(),
            "error": "No start price available (both agents may have failed)",
            "signal": signal,
            "signal_correct": None,
        }

    # End price at month-end
    try:
        end_bar = client.get_price_as_of(ticker, result_date)
        end_price = end_bar.close
        end_price_date = end_bar.bar_date.isoformat()
    except Exception as exc:
        return {
            "month": signal_date.strftime("%B %Y"),
            "signal_date": signal_date.isoformat(),
            "result_date": result_date.isoformat(),
            "start_price": round(start_price, 2),
            "start_price_date": str(start_price_date),
            "error": f"End-price fetch failed: {exc}",
            "signal": signal,
            "signal_correct": None,
        }

    price_return_pct = ((end_price - start_price) / start_price) * 100.0
    actual_direction = "up" if price_return_pct >= 0 else "down"

    if signal == "bullish":
        correct = actual_direction == "up"
    elif signal == "bearish":
        correct = actual_direction == "down"
    else:
        correct = None  # neutral — no directional prediction

    # Sub-agent score summaries
    tech_score = None
    fund_score = None
    if fusion.tech_output:
        tech_score = fusion.tech_output.score
    if fusion.fund_output:
        fund_score = fusion.fund_output.score

    return {
        "month": signal_date.strftime("%B %Y"),
        "signal_date": signal_date.isoformat(),
        "result_date": result_date.isoformat(),
        "start_price": round(start_price, 2),
        "start_price_date": str(start_price_date),
        "end_price": round(end_price, 2),
        "end_price_date": end_price_date,
        "price_return_pct": round(price_return_pct, 2),
        "actual_direction": actual_direction,
        "orchestrator_score": fusion.orchestrator_score,
        "signal": signal,
        "signal_correct": correct,
        "confidence": fusion.final_confidence,
        "conflict_detected": fusion.conflict_detected,
        "conflict_resolution": fusion.conflict_resolution,
        "weights_applied": fusion.weights_applied,
        "tech_score": tech_score,
        "fund_score": fund_score,
        "tech_error": tech_error,
        "fund_error": fund_error,
    }


def build_backtest_report(backtest: Dict[str, Any]) -> str:
    """Format backtest results as a plain-text report."""
    lines: List[str] = []
    lines.append(f"ORCHESTRATOR BACKTEST REPORT  —  {backtest['ticker']}")
    lines.append("=" * 64)
    lines.append("")

    for p in backtest["periods"]:
        if "error" in p and "start_price" not in p:
            lines.append(f"┌─ {p['month']}")
            lines.append(f"│  ERROR: {p['error']}")
            lines.append(f"└  Signal: {p['signal']}")
            lines.append("")
            continue

        arrow = "▲ UP  " if p["actual_direction"] == "up" else "▼ DOWN"
        if p["signal_correct"] is True:
            verdict = "✓  CORRECT"
        elif p["signal_correct"] is False:
            verdict = "✗  WRONG"
        else:
            verdict = "—  neutral (no directional call)"

        lines.append(f"┌─ {p['month']}")
        lines.append(
            f"│  Signal date : {p['signal_date']}  →  "
            f"price ${p['start_price']} (actual: {p['start_price_date']})"
        )
        lines.append(
            f"│  Month-end   : {p['end_price_date']}  →  "
            f"price ${p['end_price']}"
        )
        lines.append(f"│  Return      : {p['price_return_pct']:+.2f}%  {arrow}")
        lines.append(
            f"│  Orch Score  : {p['orchestrator_score']:.1f} / 100  "
            f"[conf={p['confidence']:.0%}]"
        )
        lines.append(f"│  Signal      : {p['signal'].upper()}")
        if p.get("conflict_detected"):
            lines.append(f"│  Conflict    : {p['conflict_resolution']}")

        # Sub-agent scores
        parts = []
        if p.get("tech_score") is not None:
            parts.append(f"TA={p['tech_score']:.1f}")
        if p.get("fund_score") is not None:
            parts.append(f"FA={p['fund_score']:.1f}")
        if parts:
            lines.append(f"│  Sub-agents  : {' | '.join(parts)}")

        lines.append(f"└  Result      : {verdict}")
        lines.append("")

    s = backtest["summary"]
    lines.append("─" * 64)
    lines.append("SUMMARY")
    lines.append(f"  Months analysed        : {s['total_periods']}")
    lines.append(
        f"  Directional signals    : {s['directional_signals']}  "
        f"(neutral excluded)"
    )
    lines.append(f"  Correct predictions    : {s['correct_signals']}")
    if s["accuracy_pct"] is not None:
        lines.append(f"  Hit rate               : {s['accuracy_pct']}%")
    else:
        lines.append(f"  Hit rate               : N/A")
    lines.append("")
    lines.append(f"  ⚠  {s['warning']}")
    return "\n".join(lines)
