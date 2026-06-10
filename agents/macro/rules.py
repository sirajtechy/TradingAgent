from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _score_fed_funds(current: float, prior: Optional[float]) -> float:
    """Lower/stable/rising fed funds — rising rates weigh on 1-month swing risk."""
    if prior is None:
        return 50.0
    delta = current - prior
    if delta <= -0.10:
        return 70.0
    if delta <= 0.05:
        return 55.0
    if delta <= 0.25:
        return 45.0
    return 30.0


def _score_cpi_yoy(cpi_yoy: float, prior_yoy: Optional[float]) -> float:
    """Disinflation supportive; re-acceleration negative."""
    if cpi_yoy <= 2.5:
        base = 75.0
    elif cpi_yoy <= 3.5:
        base = 60.0
    elif cpi_yoy <= 5.0:
        base = 45.0
    else:
        base = 30.0
    if prior_yoy is not None and cpi_yoy < prior_yoy - 0.3:
        base += 8.0
    elif prior_yoy is not None and cpi_yoy > prior_yoy + 0.3:
        base -= 10.0
    return _clamp(base)


def _score_unemployment(rate: float) -> float:
    if rate <= 4.0:
        return 65.0
    if rate <= 5.0:
        return 55.0
    if rate <= 6.0:
        return 40.0
    return 25.0


def _score_yield_spread(spread: float) -> float:
    """Inverted curve is bearish for risk assets."""
    if spread >= 0.75:
        return 70.0
    if spread >= 0.0:
        return 55.0
    if spread >= -0.50:
        return 35.0
    return 20.0


def _band_from_score(score: float) -> str:
    if score >= 70:
        return "strong"
    if score >= 58:
        return "good"
    if score >= 45:
        return "mixed"
    if score >= 35:
        return "mixed_negative"
    return "weak"


def _signal_from_score(score: float) -> str:
    if score >= 58:
        return "bullish"
    if score <= 42:
        return "bearish"
    return "neutral"


def _confidence_from_coverage(present: int, total: int) -> str:
    ratio = present / total if total else 0.0
    if ratio >= 0.9:
        return "high"
    if ratio >= 0.6:
        return "medium"
    return "low"


def evaluate_metrics(metrics: Dict[str, Any], warnings: List[str], data_sources: List[str]) -> Dict[str, Any]:
    """
    Deterministic macro score for ~1-month swing backdrop.

    Inputs are plain metrics from FRED client (no LLM).
    """
    subscores: Dict[str, float] = {}
    weights: List[Tuple[str, float]] = []

    if metrics.get("fed_funds") is not None:
        sub = _score_fed_funds(float(metrics["fed_funds"]), metrics.get("prior_fed_funds"))
        subscores["fed_funds"] = sub
        weights.append(("fed_funds", 0.25))

    if metrics.get("cpi_yoy_pct") is not None:
        sub = _score_cpi_yoy(float(metrics["cpi_yoy_pct"]), metrics.get("prior_cpi_yoy_pct"))
        subscores["cpi_trend"] = sub
        weights.append(("cpi_trend", 0.30))

    if metrics.get("unemployment") is not None:
        sub = _score_unemployment(float(metrics["unemployment"]))
        subscores["unemployment"] = sub
        weights.append(("unemployment", 0.20))

    if metrics.get("yield_spread_10y2y") is not None:
        sub = _score_yield_spread(float(metrics["yield_spread_10y2y"]))
        subscores["yield_curve"] = sub
        weights.append(("yield_curve", 0.25))

    if not weights:
        return {
            "signal": "neutral",
            "score": 50.0,
            "band": "mixed",
            "confidence": "low",
            "subscores": subscores,
            "metrics": metrics,
            "data_quality": "poor",
            "warnings": warnings + ["No macro series available for scoring"],
            "data_sources": data_sources,
            "bullets": ["• Macro data unavailable — abstaining from directional macro view"],
            "abstain": True,
        }

    total_w = sum(w for _, w in weights)
    score = sum(subscores[k] * w for k, w in weights) / total_w
    score = round(_clamp(score), 2)
    signal = _signal_from_score(score)
    band = _band_from_score(score)
    confidence = _confidence_from_coverage(len(weights), 4)
    data_quality = "good" if len(weights) >= 3 else ("fair" if len(weights) >= 2 else "poor")

    bullets = _build_bullets(metrics, signal)

    return {
        "signal": signal,
        "score": score,
        "band": band,
        "confidence": confidence,
        "subscores": subscores,
        "metrics": metrics,
        "data_quality": data_quality,
        "warnings": list(warnings),
        "data_sources": list(data_sources),
        "bullets": bullets,
        "abstain": False,
    }


def _build_bullets(metrics: Dict[str, Any], signal: str) -> List[str]:
    bullets: List[str] = []
    if metrics.get("fed_funds") is not None:
        bullets.append(f"• Fed funds {metrics['fed_funds']:.2f}% as of {metrics.get('fed_funds_date', 'n/a')}")
    if metrics.get("cpi_yoy_pct") is not None:
        bullets.append(f"• CPI YoY {metrics['cpi_yoy_pct']:.1f}%")
    if metrics.get("yield_spread_10y2y") is not None:
        spread = metrics["yield_spread_10y2y"]
        curve = "inverted" if spread < 0 else "positive"
        bullets.append(f"• 10Y-2Y spread {spread:.2f}% ({curve} curve)")
    bullets.append(f"• Macro swing backdrop: {signal}")
    return bullets[:3]
