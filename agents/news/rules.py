from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import NewsSettings
from .models import AnalystGrade, Headline, NewsSnapshot, PriceTarget


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _score_headline_volume(headlines: List[Headline]) -> float:
    """More headlines = more attention. Moderate volume is neutral; spike is notable."""
    n = len(headlines)
    if n == 0:
        return 50.0
    if n <= 3:
        return 50.0
    if n <= 8:
        return 55.0
    if n <= 15:
        return 60.0
    return 65.0


def _score_analyst_grades(
    grades: List[AnalystGrade],
    priority_firms: List[str],
) -> Tuple[float, List[Dict[str, Any]]]:
    """Score upgrade/downgrade activity. Filter for GS/MS as priority."""
    if not grades:
        return 50.0, []

    upgrades = 0
    downgrades = 0
    maintains = 0
    priority_actions: List[Dict[str, Any]] = []

    for g in grades:
        action = g.action.lower()
        if action in ("upgrade", "buy", "outperform"):
            upgrades += 1
        elif action in ("downgrade", "sell", "underperform"):
            downgrades += 1
        else:
            maintains += 1

        if any(firm.lower() in g.grading_company.lower() for firm in priority_firms):
            priority_actions.append({
                "firm": g.grading_company,
                "action": g.action,
                "grade": g.grade,
                "previous_grade": g.previous_grade,
                "date": g.published_date.isoformat(),
            })

    total = upgrades + downgrades + maintains
    if total == 0:
        return 50.0, priority_actions

    net = upgrades - downgrades
    if net >= 3:
        score = 75.0
    elif net >= 1:
        score = 62.0
    elif net == 0:
        score = 50.0
    elif net >= -2:
        score = 38.0
    else:
        score = 25.0

    if priority_actions:
        last_priority = priority_actions[0]
        if last_priority["action"] in ("upgrade", "buy", "outperform"):
            score = min(score + 8.0, 100.0)
        elif last_priority["action"] in ("downgrade", "sell", "underperform"):
            score = max(score - 10.0, 0.0)

    return _clamp(score), priority_actions


def _score_price_target_direction(price_targets: List[PriceTarget], current_close: Optional[float]) -> float:
    if not price_targets:
        return 50.0
    avg_pt = sum(pt.price_target for pt in price_targets) / len(price_targets)
    if current_close is None or current_close <= 0:
        return 55.0 if avg_pt > 0 else 50.0
    upside = ((avg_pt - current_close) / current_close) * 100.0
    if upside >= 20.0:
        return 72.0
    if upside >= 10.0:
        return 63.0
    if upside >= 0.0:
        return 52.0
    if upside >= -10.0:
        return 40.0
    return 28.0


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


def evaluate_news(
    snapshot: NewsSnapshot,
    settings: NewsSettings,
    current_close: Optional[float] = None,
) -> Dict[str, Any]:
    """Deterministic scoring of news + analyst activity for a ticker."""
    subscores: Dict[str, float] = {}
    weights: List[Tuple[str, float]] = []

    headline_score = _score_headline_volume(snapshot.headlines)
    subscores["headline_volume"] = headline_score
    weights.append(("headline_volume", 0.20))

    grade_score, priority_actions = _score_analyst_grades(snapshot.grades, settings.priority_firms)
    subscores["analyst_grades"] = grade_score
    weights.append(("analyst_grades", 0.45))

    pt_score = _score_price_target_direction(snapshot.price_targets, current_close)
    subscores["price_target"] = pt_score
    weights.append(("price_target", 0.35))

    total_w = sum(w for _, w in weights)
    score = round(_clamp(sum(subscores[k] * w for k, w in weights) / total_w), 2)
    signal = _signal_from_score(score)
    band = _band_from_score(score)

    upgrades = sum(1 for g in snapshot.grades if g.action.lower() in ("upgrade", "buy", "outperform"))
    downgrades = sum(1 for g in snapshot.grades if g.action.lower() in ("downgrade", "sell", "underperform"))
    data_quality = "good" if snapshot.headlines or snapshot.grades else "poor"

    bullets = _build_bullets(snapshot, upgrades, downgrades, priority_actions, signal)

    return {
        "signal": signal,
        "score": score,
        "band": band,
        "confidence": "high" if (snapshot.grades and snapshot.headlines) else "medium",
        "subscores": subscores,
        "headline_count": len(snapshot.headlines),
        "upgrades": upgrades,
        "downgrades": downgrades,
        "priority_actions": priority_actions,
        "data_quality": data_quality,
        "warnings": list(snapshot.warnings),
        "data_sources": list(snapshot.data_sources),
        "bullets": bullets,
        "abstain": not snapshot.headlines and not snapshot.grades,
    }


def _build_bullets(
    snapshot: NewsSnapshot,
    upgrades: int,
    downgrades: int,
    priority_actions: List[Dict[str, Any]],
    signal: str,
) -> List[str]:
    bullets: List[str] = []
    if priority_actions:
        pa = priority_actions[0]
        bullets.append(f"{pa['firm']} {pa['action']} → {pa['grade']} ({pa['date']})")
    if upgrades or downgrades:
        bullets.append(f"Analyst activity: {upgrades} upgrade(s), {downgrades} downgrade(s)")
    for headline in snapshot.headlines[:3]:
        title = headline.title.strip()
        if title:
            src = f" — {headline.source}" if headline.source else ""
            bullets.append(f"\"{title[:120]}\"{src} ({headline.published_date})")
    if snapshot.headlines and len(snapshot.headlines) > 3:
        bullets.append(f"{len(snapshot.headlines)} headlines in last 30d")
    bullets.append(f"News/analyst signal: {signal}")
    return bullets[:6]
