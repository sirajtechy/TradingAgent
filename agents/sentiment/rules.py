from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import SentimentSettings
from .models import DimensionScore, SentimentSnapshot


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _signal_from_score(score: float) -> str:
    if score >= 58:
        return "bullish"
    if score <= 42:
        return "bearish"
    return "neutral"


def _signal_label(score: float) -> str:
    if score >= 58:
        return "positive"
    if score <= 42:
        return "negative"
    return "neutral"


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


def _extract_score(eval_dict: Optional[Dict[str, Any]]) -> Optional[float]:
    if eval_dict is None:
        return None
    s = eval_dict.get("score")
    if s is None:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def evaluate_sentiment(
    snapshot: SentimentSnapshot,
    settings: Optional[SentimentSettings] = None,
) -> Dict[str, Any]:
    """
    Deterministic multi-dimension sentiment score for a ticker.

    Aggregates News, Insider, Macro (+ future Geopolitics) envelopes
    into a single 0-100 score with per-dimension breakdown.
    """
    cfg = settings or SentimentSettings()
    dimensions: List[DimensionScore] = []
    weights: List[Tuple[str, float]] = []

    # News dimension (split into headline + analyst sub-dimensions)
    news_score = _extract_score(snapshot.news_eval)
    if news_score is not None:
        dimensions.append(DimensionScore("news", news_score, _signal_label(news_score), True))
        weights.append(("news", cfg.weight_news))

        analyst_score = (snapshot.news_eval or {}).get("subscores", {}).get("analyst_grades")
        if analyst_score is not None:
            dimensions.append(DimensionScore("analyst", float(analyst_score), _signal_label(float(analyst_score)), True))
            weights.append(("analyst", cfg.weight_analyst))
    else:
        dimensions.append(DimensionScore("news", 50.0, "neutral", False))
        dimensions.append(DimensionScore("analyst", 50.0, "neutral", False))

    # Insider dimension
    insider_score = _extract_score(snapshot.insider_eval)
    if insider_score is not None:
        dimensions.append(DimensionScore("insider", insider_score, _signal_label(insider_score), True))
        weights.append(("insider", cfg.weight_insider))
    else:
        dimensions.append(DimensionScore("insider", 50.0, "neutral", False))

    # Macro dimension (session-level)
    macro_score = _extract_score(snapshot.macro_eval)
    if macro_score is not None:
        dimensions.append(DimensionScore("macro", macro_score, _signal_label(macro_score), True))
        weights.append(("macro", cfg.weight_macro))
    else:
        dimensions.append(DimensionScore("macro", 50.0, "neutral", False))

    # Geopolitics dimension (session-level)
    geo_score = _extract_score(snapshot.geopolitics_eval)
    if geo_score is not None:
        dimensions.append(DimensionScore("geopolitics", geo_score, _signal_label(geo_score), True))
        weights.append(("geopolitics", cfg.weight_geopolitics))
    else:
        dimensions.append(DimensionScore("geopolitics", 50.0, "neutral", False))

    # Weighted composite
    dim_map = {d.dimension: d.score for d in dimensions if d.available}
    if not weights:
        composite = 50.0
    else:
        total_w = sum(w for _, w in weights)
        composite = sum(dim_map.get(k, 50.0) * w for k, w in weights) / total_w
    composite = round(_clamp(composite), 2)

    signal = _signal_from_score(composite)
    sentiment_label = _signal_label(composite)
    band = _band_from_score(composite)

    available_count = sum(1 for d in dimensions if d.available)
    confidence = "high" if available_count >= 4 else ("medium" if available_count >= 2 else "low")
    data_quality = "good" if available_count >= 3 else ("fair" if available_count >= 2 else "poor")

    dimension_map = {d.dimension: d.signal for d in dimensions}
    bullets = _build_bullets(dimensions, sentiment_label)

    data_sources = list(snapshot.data_sources)
    for ev in [snapshot.news_eval, snapshot.insider_eval, snapshot.macro_eval]:
        if ev:
            for src in ev.get("data_sources") or []:
                if src not in data_sources:
                    data_sources.append(src)

    return {
        "signal": signal,
        "score": composite,
        "band": band,
        "confidence": confidence,
        "sentiment": sentiment_label,
        "subscores": {d.dimension: d.score for d in dimensions},
        "dimensions": dimension_map,
        "ohlcv_context": snapshot.ohlcv_context,
        "data_quality": data_quality,
        "warnings": list(snapshot.warnings),
        "data_sources": data_sources,
        "bullets": bullets,
        "abstain": available_count == 0,
    }


def _build_bullets(dimensions: List[DimensionScore], sentiment: str) -> List[str]:
    bullets: List[str] = []
    avail = [d for d in dimensions if d.available]
    if avail:
        labels = ", ".join(f"{d.dimension}={d.signal}" for d in avail)
        bullets.append(f"• Dimensions: {labels}")
    bullets.append(f"• Composite sentiment: {sentiment}")
    neg = [d for d in avail if d.signal == "negative"]
    if neg:
        bullets.append(f"• Headwinds: {', '.join(d.dimension for d in neg)}")
    return bullets[:3]
