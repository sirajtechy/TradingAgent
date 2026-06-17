from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .models import MarketDataSnapshot, TickerPerformance


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _score_vix(vix: Optional[float], vix_regime: str) -> float:
    if vix is None:
        return 50.0
    if vix_regime == "low":
        return 70.0
    if vix_regime == "normal":
        return 58.0
    if vix_regime == "fear":
        return 40.0
    if vix_regime == "extreme":
        return 25.0
    return 50.0


def _score_spy_trend(spy: Optional[TickerPerformance]) -> float:
    if spy is None or spy.change_20d_pct is None:
        return 50.0
    ch = spy.change_20d_pct
    if ch >= 3.0:
        return 72.0
    if ch >= 0.5:
        return 60.0
    if ch >= -2.0:
        return 48.0
    return 32.0


def _score_sector_breadth(sectors: List[TickerPerformance]) -> float:
    if not sectors:
        return 50.0
    valid = [s for s in sectors if s.vs_spy_20d_pct is not None]
    if not valid:
        return 50.0
    leaders = sum(1 for s in valid if s.vs_spy_20d_pct > 0)
    ratio = leaders / len(valid)
    return _clamp(35.0 + ratio * 50.0)


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


def _top_sectors(sectors: List[TickerPerformance], n: int = 3) -> List[Dict[str, Any]]:
    ranked = sorted(
        [s for s in sectors if s.vs_spy_20d_pct is not None],
        key=lambda s: s.vs_spy_20d_pct or 0.0,
        reverse=True,
    )
    return [
        {
            "ticker": s.ticker,
            "label": s.label,
            "vs_spy_20d_pct": s.vs_spy_20d_pct,
            "change_20d_pct": s.change_20d_pct,
        }
        for s in ranked[:n]
    ]


def _bottom_sectors(sectors: List[TickerPerformance], n: int = 3) -> List[Dict[str, Any]]:
    ranked = sorted(
        [s for s in sectors if s.vs_spy_20d_pct is not None],
        key=lambda s: s.vs_spy_20d_pct or 0.0,
    )
    return [
        {
            "ticker": s.ticker,
            "label": s.label,
            "vs_spy_20d_pct": s.vs_spy_20d_pct,
            "change_20d_pct": s.change_20d_pct,
        }
        for s in ranked[:n]
    ]


def evaluate_market_summary(
    *,
    market_snapshot: MarketDataSnapshot,
    macro_eval: Dict[str, Any],
) -> Dict[str, Any]:
    """Combine Polygon market data with macro envelope (read-only)."""
    subscores = {
        "vix": _score_vix(market_snapshot.vix, market_snapshot.vix_regime),
        "spy_trend": _score_spy_trend(market_snapshot.spy),
        "sector_breadth": _score_sector_breadth(market_snapshot.sectors),
        "macro": float(macro_eval.get("score") or 50.0),
    }
    weights = {
        "vix": 0.25,
        "spy_trend": 0.25,
        "sector_breadth": 0.20,
        "macro": 0.30,
    }
    score = round(
        sum(subscores[k] * weights[k] for k in weights),
        2,
    )
    score = _clamp(score)
    signal = _signal_from_score(score)
    band = _band_from_score(score)

    market_wide_signal = signal
    if market_snapshot.vix_regime == "extreme" and score > 45:
        market_wide_signal = "neutral"
        score = min(score, 45.0)
        signal = "neutral"

    leaders = _top_sectors(market_snapshot.sectors)
    laggards = _bottom_sectors(market_snapshot.sectors)

    data_sources = list(dict.fromkeys(
        (market_snapshot.data_sources or []) + (macro_eval.get("data_sources") or [])
    ))
    warnings = list(market_snapshot.warnings or []) + list(macro_eval.get("warnings") or [])

    data_quality = macro_eval.get("data_quality") or "unknown"
    if market_snapshot.spy is None or market_snapshot.vix is None:
        data_quality = "fair" if data_quality == "good" else data_quality
    if market_snapshot.spy is None and market_snapshot.vix is None:
        data_quality = "poor"

    bullets = _build_bullets(market_snapshot, macro_eval, market_wide_signal)

    return {
        "signal": signal,
        "score": score,
        "band": band,
        "confidence": macro_eval.get("confidence") or "medium",
        "subscores": subscores,
        "market_wide_signal": market_wide_signal,
        "vix": market_snapshot.vix,
        "vix_regime": market_snapshot.vix_regime,
        "spy_change_5d_pct": market_snapshot.spy.change_5d_pct if market_snapshot.spy else None,
        "spy_change_20d_pct": market_snapshot.spy.change_20d_pct if market_snapshot.spy else None,
        "sector_leaders": leaders,
        "sector_laggards": laggards,
        "macro": {
            "signal": macro_eval.get("signal"),
            "score": macro_eval.get("score"),
            "metrics": macro_eval.get("metrics"),
        },
        "data_quality": data_quality,
        "warnings": warnings,
        "data_sources": data_sources,
        "bullets": bullets,
        "abstain": bool(macro_eval.get("abstain")) and market_snapshot.spy is None,
    }


def _build_bullets(
    market_snapshot: MarketDataSnapshot,
    macro_eval: Dict[str, Any],
    market_wide_signal: str,
) -> List[str]:
    bullets: List[str] = []
    if market_snapshot.vix is not None:
        bullets.append(
            f"VIX {market_snapshot.vix:.2f} ({market_snapshot.vix_regime})"
        )
    if market_snapshot.spy and market_snapshot.spy.change_20d_pct is not None:
        bullets.append(f"SPY 20d {market_snapshot.spy.change_20d_pct:+.2f}%")
    macro_metrics = macro_eval.get("metrics") or {}
    if macro_metrics.get("cpi_yoy_pct") is not None:
        bullets.append(f"CPI YoY {macro_metrics['cpi_yoy_pct']:.1f}%")
    if macro_metrics.get("fed_funds") is not None:
        bullets.append(f"Fed funds {macro_metrics['fed_funds']:.2f}%")
    if macro_metrics.get("yield_spread_10y2y") is not None:
        spread = macro_metrics["yield_spread_10y2y"]
        curve = "inverted" if spread < 0 else "positive"
        bullets.append(f"10Y-2Y spread {spread:.2f}% ({curve} curve)")
    leaders = _top_sectors(market_snapshot.sectors, n=2)
    for row in leaders:
        bullets.append(
            f"Leading sector: {row['label']} ({row['ticker']}) {row['vs_spy_20d_pct']:+.2f}% vs SPY"
        )
    bullets.append(f"Market-wide signal: {market_wide_signal}")
    return bullets[:6]
