from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .config import load_settings
from .fmp_client import FMPClient
from .service import analyze_ticker


# Map experimental score band to a directional signal.
# v2: tightened thresholds — bullish requires score >= 62.
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
    shariah_standard: str = "aaoifi",
    api_key: Optional[str] = None,
    data_source: str = "fmp",
) -> Dict[str, Any]:
    """
    For each (signal_date, result_date) pair:
      - Run fundamental analysis on signal_date
      - Fetch the month-end closing price on result_date
      - Compute the return and whether the signal was correct
    """
    from .yf_client import YFinanceClient
    if data_source == "yfinance":
        client = YFinanceClient()
    else:
        settings = load_settings(api_key=api_key)
        client = FMPClient(settings=settings)

    periods = []
    for signal_date, result_date in months:
        period = _run_period(
            ticker=ticker,
            signal_date=signal_date,
            result_date=result_date,
            shariah_standard=shariah_standard,
            client=client,
            api_key=api_key,
            data_source=data_source,
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
                f"{n} data point{'s are' if n != 1 else ' is'} not statistically significant — "
                "use this to understand the signal behaviour, not to validate it."
            ),
        },
    }


def _run_period(
    ticker: str,
    signal_date: date,
    result_date: date,
    shariah_standard: str,
    client: Any,
    api_key: Optional[str],
    data_source: str = "fmp",
) -> Dict[str, Any]:
    result = analyze_ticker(
        ticker=ticker,
        as_of_date=signal_date.isoformat(),
        shariah_standard=shariah_standard,
        include_experimental_score=True,
        api_key=api_key,
        data_source=data_source,
    )

    start_price = result["as_of_price"]["price"]
    start_price_date = result["as_of_price"]["price_date"]

    end_point = client.get_price_as_of(ticker, result_date)
    end_price = end_point.price
    end_price_date = end_point.price_date.isoformat()

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
        correct = None  # neutral gives no directional prediction

    framework_summary = {}
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
        "data_quality": result.get("data_quality"),
    }


def build_backtest_report(backtest: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"BACKTEST REPORT  —  {backtest['ticker']}")
    lines.append("=" * 64)
    lines.append("")

    for p in backtest["periods"]:
        arrow = "▲ UP  " if p["actual_direction"] == "up" else "▼ DOWN"
        if p["signal_correct"] is True:
            verdict = "✓  CORRECT"
        elif p["signal_correct"] is False:
            verdict = "✗  WRONG"
        else:
            verdict = "—  neutral (no directional call)"

        lines.append(f"┌─ {p['month']}")
        lines.append(f"│  Signal date : {p['signal_date']}  →  price ${p['start_price']} (actual: {p['start_price_date']})")
        lines.append(f"│  Month-end   : {p['end_price_date']}  →  price ${p['end_price']}")
        lines.append(f"│  Return      : {p['price_return_pct']:+.2f}%  {arrow}")
        lines.append(f"│  Score       : {p['experimental_score']} / 100  [{p['score_band']}]")
        lines.append(f"│  Signal      : {p['signal'].upper()}")
        lines.append(f"└  Result      : {verdict}")

        fw = p["frameworks"]
        parts = []
        for name, val in fw.items():
            if val.get("applicable") and val.get("score_pct") is not None:
                parts.append(f"{name.capitalize()[:6]} {val['score_pct']}%")
        if parts:
            lines.append(f"   Frameworks  : {' | '.join(parts)}")
        lines.append("")

    s = backtest["summary"]
    lines.append("─" * 64)
    lines.append("SUMMARY")
    lines.append(f"  Months analysed        : {s['total_periods']}")
    lines.append(f"  Directional signals    : {s['directional_signals']}  (neutral excluded)")
    lines.append(f"  Correct predictions    : {s['correct_signals']}")
    if s["accuracy_pct"] is not None:
        lines.append(f"  Hit rate               : {s['accuracy_pct']}%")
    else:
        lines.append(f"  Hit rate               : N/A")
    lines.append("")
    lines.append(f"  ⚠  {s['warning']}")
    return "\n".join(lines)
