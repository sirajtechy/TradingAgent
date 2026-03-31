"""
backtest.py — Monthly backtest engine for the technical analysis agent.

Mirrors the fundamental agent's backtest module:
  1. Run analysis as of *signal_date*.
  2. Fetch month-end price at *result_date*.
  3. Compare predicted signal vs actual direction.
  4. Build a text report and JSON output.

Uses the same ``BAND_TO_SIGNAL`` mapping so confusion matrix semantics
are identical across both agents.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .data_client import YFinanceTechnicalClient
from .service import analyze_ticker


# Map composite band → directional signal (must match reporting._BAND_TO_SIGNAL).
BAND_TO_SIGNAL = {
    "strong": "bullish",
    "good": "bullish",
    "mixed_positive": "bullish",
    "mixed": "neutral",
    "weak": "bearish",
}


def run_monthly_backtest(
    ticker: str,
    months: List[Tuple[date, date]],
) -> Dict[str, Any]:
    """
    Run a monthly backtest for *ticker* across *months*.

    Args:
        ticker: Stock symbol (e.g. ``"AAPL"``).
        months: List of ``(signal_date, result_date)`` pairs.
                signal_date = date on which analysis is run.
                result_date = month-end date for price comparison.

    Returns:
        Dict containing ``ticker``, ``periods`` list, and ``summary``.
    """
    client = YFinanceTechnicalClient()
    periods: List[Dict[str, Any]] = []

    for signal_date, result_date in months:
        period = _run_period(
            ticker=ticker,
            signal_date=signal_date,
            result_date=result_date,
            client=client,
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
    client: YFinanceTechnicalClient,
) -> Dict[str, Any]:
    """
    Evaluate a single (signal_date → result_date) period.

    Catches errors and returns an ``error`` field rather than blowing up
    the entire backtest.
    """
    try:
        result = analyze_ticker(
            ticker=ticker,
            as_of_date=signal_date.isoformat(),
        )
    except Exception as exc:
        return {
            "month": signal_date.strftime("%B %Y"),
            "signal_date": signal_date.isoformat(),
            "result_date": result_date.isoformat(),
            "error": str(exc),
            "signal": "unknown",
            "signal_correct": None,
        }

    # Start price from analysis
    start_price = result["as_of_price"]["price"]
    start_price_date = result["as_of_price"]["price_date"]

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
            "signal": "unknown",
            "signal_correct": None,
        }

    price_return_pct = ((end_price - start_price) / start_price) * 100.0
    actual_direction = "up" if price_return_pct >= 0 else "down"

    exp = result.get("experimental_score", {})
    score = exp.get("score") if exp and exp.get("available") else None
    band = exp.get("band") if exp and exp.get("available") else None
    signal = BAND_TO_SIGNAL.get(band, "neutral") if band else "unknown"

    if signal == "bullish":
        correct = actual_direction == "up"
    elif signal == "bearish":
        correct = actual_direction == "down"
    else:
        correct = None  # neutral — no directional prediction

    # Compact framework summary
    framework_summary: Dict[str, Any] = {}
    for name, fw in result.get("frameworks", {}).items():
        framework_summary[name] = {
            "applicable": fw.get("applicable"),
            "score_pct": fw.get("score_pct"),
        }

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
        "experimental_score": score,
        "score_band": band,
        "signal": signal,
        "signal_correct": correct,
        "frameworks": framework_summary,
    }


def build_backtest_report(backtest: Dict[str, Any]) -> str:
    """
    Format a backtest result dict as a plain-text report.

    Args:
        backtest: The dict returned by ``run_monthly_backtest()``.

    Returns:
        Multi-line human-readable string.
    """
    lines: List[str] = []
    lines.append(f"TECHNICAL BACKTEST REPORT  —  {backtest['ticker']}")
    lines.append("=" * 64)
    lines.append("")

    for p in backtest["periods"]:
        if "error" in p:
            lines.append(f"┌─ {p['month']}")
            lines.append(f"│  ERROR: {p['error']}")
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
            f"│  Signal date : {p['signal_date']}  →  price "
            f"${p['start_price']} (actual: {p['start_price_date']})"
        )
        lines.append(
            f"│  Month-end   : {p['end_price_date']}  →  price "
            f"${p['end_price']}"
        )
        lines.append(f"│  Return      : {p['price_return_pct']:+.2f}%  {arrow}")
        lines.append(
            f"│  Score       : {p['experimental_score']} / 100  "
            f"[{p['score_band']}]"
        )
        lines.append(f"│  Signal      : {p['signal'].upper()}")
        lines.append(f"└  Result      : {verdict}")

        fw = p.get("frameworks", {})
        parts = []
        for name, val in fw.items():
            if val.get("applicable") and val.get("score_pct") is not None:
                parts.append(f"{name[:6]} {val['score_pct']}%")
        if parts:
            lines.append(f"   Frameworks  : {' | '.join(parts)}")
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
        lines.append("  Hit rate               : N/A")
    lines.append("")
    lines.append(f"  ⚠  {s['warning']}")
    return "\n".join(lines)
