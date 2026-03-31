"""
reporting.py — Plain-text report builder for the technical analysis agent.

``build_text_report()`` takes the evaluation dict produced by
``rules.evaluate_snapshot()`` and returns a multi-line human-readable
string identical in spirit to the fundamental agent's reporting module.
"""

from typing import Any, Dict, List


# Signal band → arrow glyph for visual scanning
_ARROW = {
    "strong": "▲▲",
    "good": "▲",
    "mixed_positive": "►",
    "mixed": "●",
    "weak": "▼",
}

# Composite band → directional signal label
_BAND_TO_SIGNAL = {
    "strong": "BULLISH",
    "good": "BULLISH",
    "mixed_positive": "BULLISH",
    "mixed": "NEUTRAL",
    "weak": "BEARISH",
}


def build_text_report(result: Dict[str, Any]) -> str:
    """
    Build a formatted text report from the evaluation dict.

    Args:
        result: The complete evaluation dict produced by
                ``rules.evaluate_snapshot()``.

    Returns:
        Multi-line string ready for terminal printing.
    """
    lines: List[str] = []
    company = result.get("company", {})
    ticker = company.get("ticker", "???")
    name = company.get("company_name", ticker)
    sector = company.get("sector", "Unknown")
    industry = company.get("industry", "Unknown")

    price_info = result.get("as_of_price", {})
    price = price_info.get("price")
    price_date = price_info.get("price_date")

    lines.append(f"{name} ({ticker}) — Technical Analysis")
    lines.append(f"As of: {price_date}  |  Price: ${price}")
    lines.append(f"Sector / Industry: {sector} / {industry}")
    lines.append("")

    # ── Composite score ──────────────────────────────────────────── #
    exp = result.get("experimental_score", {})
    if exp and exp.get("available"):
        score = exp.get("score")
        band = exp.get("band", "mixed")
        confidence = exp.get("confidence", "?")
        signal = _BAND_TO_SIGNAL.get(band, "NEUTRAL")
        arrow = _ARROW.get(band, "●")
        lines.append(
            f"COMPOSITE SCORE: {score}/100  |  Band: {band.upper()}  |  "
            f"Signal: {signal} {arrow}  |  Confidence: {confidence.upper()}"
        )
        lines.append("")
    else:
        lines.append("COMPOSITE SCORE: N/A (insufficient data)")
        lines.append("")

    # ── Framework breakdown ──────────────────────────────────────── #
    lines.append("FRAMEWORKS:")
    frameworks = result.get("frameworks", {})

    _LABELS = {
        "ema_trend": "EMA Trend",
        "macd_system": "MACD System",
        "rsi_regime": "RSI Regime",
        "bollinger": "Bollinger Bands",
        "volume_obv": "Volume (OBV)",
        "adx_stochastic": "ADX + Stochastic",
        "pattern_recognition": "Pattern Recog",
    }

    for key, label in _LABELS.items():
        fw = frameworks.get(key, {})
        score_pct = fw.get("score_pct")
        if score_pct is None:
            lines.append(f"  {label:<20s}  N/A")
            continue

        arrow = "▲" if score_pct >= 60 else ("▼" if score_pct < 40 else "●")
        detail_parts = _framework_detail_line(key, fw)
        lines.append(
            f"  {label:<20s}  {score_pct:>5.1f}/100  {arrow}  {detail_parts}"
        )

    lines.append("")

    # ── Patterns ─────────────────────────────────────────────────── #
    patterns = result.get("patterns", [])
    if patterns:
        lines.append("PATTERNS DETECTED (last 12 months):")
        for p in patterns:
            direction_arrow = "▲" if p.get("direction") == "bullish" else "▼"
            conf = p.get("confidence", 0)
            bo = "BREAKOUT ✓" if p.get("breakout_confirmed") else "no breakout"
            vol = "vol ✓" if p.get("volume_confirmation") else ""
            lines.append(
                f"  {direction_arrow} {p.get('name', '?'):<25s}  "
                f"{p.get('start_date', '?')} → {p.get('end_date', '?')}  "
                f"conf={conf:.2f}  {bo}  {vol}"
            )
        lines.append("")
    else:
        lines.append("PATTERNS: None detected in the lookback window.")
        lines.append("")

    # ── Key indicators ───────────────────────────────────────────── #
    ki = result.get("key_indicators", {})
    if ki:
        lines.append("KEY INDICATORS:")
        lines.append(
            f"  Close: ${ki.get('close')}  |  EMA-20: {ki.get('ema_20')}  |  "
            f"EMA-50: {ki.get('ema_50')}  |  EMA-200: {ki.get('ema_200')}"
        )
        lines.append(
            f"  RSI-14: {ki.get('rsi_14')}  |  MACD: {ki.get('macd')}  |  "
            f"ADX: {ki.get('adx')}  |  Stoch %K: {ki.get('stoch_k')}"
        )
        lines.append(
            f"  BB %B: {ki.get('bb_pct_b')}  |  BB BW: {ki.get('bb_bandwidth')}  |  "
            f"OBV trend: {ki.get('obv_trend')}"
        )
        lines.append("")

    # ── Warnings ─────────────────────────────────────────────────── #
    warnings = result.get("warnings", [])
    if warnings:
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)


def _framework_detail_line(key: str, fw: Dict[str, Any]) -> str:
    """
    Build a short detail string for a given framework.

    Each framework exposes a ``details`` dict; we pick the most
    informative fields for the one-line summary.
    """
    d = fw.get("details", {})

    if key == "ema_trend":
        gc = d.get("golden_cross")
        slope = d.get("ema_20_slope", "?")
        gc_str = "Golden Cross" if gc else ("Death Cross" if gc is False else "")
        return f"slope={slope} {gc_str}"

    if key == "macd_system":
        div = d.get("divergence") or "none"
        hist = "hist rising" if d.get("histogram_rising") else "hist falling"
        return f"{hist}, div={div}"

    if key == "rsi_regime":
        rsi_val = d.get("rsi")
        div = d.get("divergence") or "none"
        return f"RSI={rsi_val}, div={div}"

    if key == "bollinger":
        pct_b = d.get("pct_b")
        sq = "SQUEEZE" if d.get("squeeze") else ""
        return f"%B={pct_b} {sq}"

    if key == "volume_obv":
        trend = d.get("obv_trend", "?")
        conf = "confirms" if d.get("confirms_price") else "diverges"
        return f"OBV {trend}, {conf} price"

    if key == "adx_stochastic":
        adx_val = d.get("adx")
        sk = d.get("stoch_k")
        return f"ADX={adx_val}, %K={sk}"

    if key == "pattern_recognition":
        bd = d.get("bullish_count", 0)
        be = d.get("bearish_count", 0)
        return f"{bd} bullish, {be} bearish patterns"

    return ""
