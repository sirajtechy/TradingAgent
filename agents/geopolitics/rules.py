from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import GeopoliticsSettings
from .models import GeoHeadline, GeopoliticsSnapshot


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _score_keyword_density(headlines: List[GeoHeadline]) -> float:
    """More geo-keyword matches = higher risk (lower score for equities)."""
    if not headlines:
        return 65.0
    total_matches = sum(len(h.matched_keywords) for h in headlines)
    if total_matches <= 2:
        return 60.0
    if total_matches <= 5:
        return 48.0
    if total_matches <= 10:
        return 35.0
    return 22.0


def _score_headline_concentration(headlines: List[GeoHeadline], total_scanned: int) -> float:
    """What fraction of scanned headlines are geo-relevant? Higher = riskier."""
    if total_scanned == 0:
        return 55.0
    ratio = len(headlines) / total_scanned
    if ratio <= 0.05:
        return 65.0
    if ratio <= 0.15:
        return 52.0
    if ratio <= 0.30:
        return 38.0
    return 25.0


def _identify_sector_exposure(
    headlines: List[GeoHeadline],
    sector_map: Dict[str, List[str]],
) -> Dict[str, int]:
    """Count geo-keyword hits per sector."""
    exposure: Dict[str, int] = {}
    for sector, keywords in sector_map.items():
        count = 0
        for h in headlines:
            for kw in h.matched_keywords:
                if kw in keywords:
                    count += 1
        if count > 0:
            exposure[sector] = count
    return exposure


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


def evaluate_geopolitics(
    snapshot: GeopoliticsSnapshot,
    settings: GeopoliticsSettings,
    llm_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deterministic geopolitical risk scoring + optional LLM classification.

    Keyword pre-filter is deterministic. LLM result (if provided) adjusts
    the final score within a bounded range — never overrides structure.
    """
    subscores: Dict[str, float] = {}
    weights: List[Tuple[str, float]] = []

    density_score = _score_keyword_density(snapshot.headlines)
    subscores["keyword_density"] = density_score
    weights.append(("keyword_density", 0.45))

    concentration_score = _score_headline_concentration(snapshot.headlines, snapshot.total_scanned)
    subscores["headline_concentration"] = concentration_score
    weights.append(("headline_concentration", 0.30))

    # LLM classification (post-score overlay, bounded +-10 pts)
    llm_adjustment = 0.0
    llm_sentiment = None
    if llm_result and llm_result.get("sentiment"):
        llm_sentiment = llm_result["sentiment"]
        if llm_sentiment == "negative":
            llm_adjustment = -8.0
        elif llm_sentiment == "positive":
            llm_adjustment = 5.0
        subscores["llm_classification"] = 50.0 + llm_adjustment
        weights.append(("llm_classification", 0.25))
    else:
        subscores["llm_classification"] = 50.0

    total_w = sum(w for _, w in weights)
    score = round(_clamp(sum(subscores[k] * w for k, w in weights) / total_w), 2)
    signal = _signal_from_score(score)
    band = _band_from_score(score)

    sector_exposure = _identify_sector_exposure(snapshot.headlines, dict(settings.sector_exposure))

    data_quality = "good" if snapshot.headlines else ("fair" if snapshot.total_scanned > 0 else "poor")

    bullets_from_llm = []
    if llm_result and llm_result.get("bullets"):
        bullets_from_llm = list(llm_result["bullets"])

    bullets = _build_bullets(snapshot, sector_exposure, signal, bullets_from_llm)

    return {
        "signal": signal,
        "score": score,
        "band": band,
        "confidence": "high" if snapshot.headlines and llm_result else ("medium" if snapshot.headlines else "low"),
        "subscores": subscores,
        "geo_headline_count": len(snapshot.headlines),
        "total_scanned": snapshot.total_scanned,
        "sector_exposure": sector_exposure,
        "llm_sentiment": llm_sentiment,
        "data_quality": data_quality,
        "warnings": list(snapshot.warnings),
        "data_sources": list(snapshot.data_sources),
        "bullets": bullets,
        "abstain": not snapshot.headlines and snapshot.total_scanned == 0,
    }


def _build_bullets(
    snapshot: GeopoliticsSnapshot,
    sector_exposure: Dict[str, int],
    signal: str,
    llm_bullets: List[str],
) -> List[str]:
    bullets: List[str] = []
    if llm_bullets:
        bullets.extend(str(b).lstrip("• ").strip() for b in llm_bullets[:2])
    for headline in snapshot.headlines[:3]:
        title = headline.title.strip()
        if title:
            kws = ", ".join(headline.matched_keywords[:3])
            kw_txt = f" [{kws}]" if kws else ""
            bullets.append(f"\"{title[:120]}\"{kw_txt}")
    if snapshot.headlines:
        top_kws = set()
        for h in snapshot.headlines[:5]:
            top_kws.update(h.matched_keywords)
        if top_kws:
            bullets.append(f"Key themes: {', '.join(sorted(top_kws)[:4])}")
    if sector_exposure:
        top_sector = max(sector_exposure, key=sector_exposure.get)
        bullets.append(f"Most exposed sector: {top_sector} ({sector_exposure[top_sector]} hits)")
    bullets.append(f"Geopolitical signal: {signal} ({len(snapshot.headlines)} geo headlines)")
    return bullets[:6]
