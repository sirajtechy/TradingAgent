"""
low_volume_validator.py — Low-volume and small-cap stock reliability module.

Identifies thinly-traded stocks where technical indicators may be unreliable,
and applies appropriate confidence adjustments and warnings.

Thresholds (based on market microstructure research):
    - Avg daily volume < 500K shares → "low volume" (wide spreads, noise)
    - Avg daily volume < 100K shares → "very low volume" (illiquid, unreliable)
    - Price < $5 → "penny stock" territory (pattern recognition unreliable)
    - High volatility + low volume → worst-case combination

This module does NOT modify scores — it adds warnings and confidence
adjustments that the reporting layer can surface to the user.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ====================================================================== #
# THRESHOLDS                                                                #
# ====================================================================== #

# Average daily volume thresholds (shares)
VERY_LOW_VOLUME_THRESHOLD = 100_000
LOW_VOLUME_THRESHOLD = 500_000
ADEQUATE_VOLUME_THRESHOLD = 1_000_000

# Price thresholds
PENNY_STOCK_THRESHOLD = 5.0
LOW_PRICE_THRESHOLD = 10.0

# Indicator reliability thresholds (minimum bars with sufficient volume)
MIN_RELIABLE_BARS = 50  # at least 50 bars above threshold for reliable signals


# ====================================================================== #
# VALIDATION                                                                #
# ====================================================================== #

def validate_stock_reliability(
    closes: List[float],
    volumes: List[float],
    ticker: str,
) -> Dict[str, Any]:
    """
    Assess whether a stock's price and volume characteristics support
    reliable technical analysis.

    Args:
        closes:  Daily closing prices (oldest-first).
        volumes: Daily volume figures (oldest-first).
        ticker:  Stock symbol for reporting.

    Returns:
        Dict with reliability_grade, confidence_adjustment, warnings,
        and detailed metrics.
    """
    if not closes or not volumes:
        return {
            "ticker": ticker.upper(),
            "reliability_grade": "insufficient_data",
            "confidence_adjustment": -0.5,
            "warnings": ["No price/volume data available for reliability check."],
            "metrics": {},
        }

    n = len(closes)
    price = closes[-1]
    warnings: List[str] = []

    # --- Volume analysis ---
    avg_volume = sum(volumes[-20:]) / min(20, len(volumes[-20:])) if volumes else 0
    total_avg_volume = sum(volumes) / n if n > 0 else 0

    # Count bars with adequate volume
    adequate_bars = sum(1 for v in volumes if v >= ADEQUATE_VOLUME_THRESHOLD)
    adequate_bar_pct = (adequate_bars / n * 100) if n > 0 else 0

    # Volume consistency: std dev of recent volume
    recent_vols = volumes[-20:] if len(volumes) >= 20 else volumes
    if len(recent_vols) > 1:
        vol_mean = sum(recent_vols) / len(recent_vols)
        vol_var = sum((v - vol_mean) ** 2 for v in recent_vols) / len(recent_vols)
        vol_cv = (vol_var ** 0.5) / vol_mean if vol_mean > 0 else 0  # coefficient of variation
    else:
        vol_cv = 0

    # --- Classify volume level ---
    if avg_volume < VERY_LOW_VOLUME_THRESHOLD:
        volume_class = "very_low"
        volume_adj = -0.4
        warnings.append(
            f"VERY LOW VOLUME: {ticker} averages {avg_volume:,.0f} shares/day "
            f"(threshold: {VERY_LOW_VOLUME_THRESHOLD:,}). Technical signals "
            "are highly unreliable — wide spreads and noise dominate."
        )
    elif avg_volume < LOW_VOLUME_THRESHOLD:
        volume_class = "low"
        volume_adj = -0.2
        warnings.append(
            f"LOW VOLUME: {ticker} averages {avg_volume:,.0f} shares/day "
            f"(threshold: {LOW_VOLUME_THRESHOLD:,}). Pattern recognition "
            "and volume-based indicators may be unreliable."
        )
    elif avg_volume < ADEQUATE_VOLUME_THRESHOLD:
        volume_class = "moderate"
        volume_adj = -0.1
        warnings.append(
            f"MODERATE VOLUME: {ticker} averages {avg_volume:,.0f} shares/day. "
            "Volume-based indicators should be interpreted with caution."
        )
    else:
        volume_class = "adequate"
        volume_adj = 0.0

    # --- Classify price level ---
    if price < PENNY_STOCK_THRESHOLD:
        price_class = "penny"
        price_adj = -0.3
        warnings.append(
            f"PENNY STOCK: {ticker} trades at ${price:.2f} — below "
            f"${PENNY_STOCK_THRESHOLD}. Chart patterns and technical "
            "indicators are statistically unreliable at this price level."
        )
    elif price < LOW_PRICE_THRESHOLD:
        price_class = "low"
        price_adj = -0.1
        warnings.append(
            f"LOW PRICE: {ticker} trades at ${price:.2f}. Some "
            "pattern-based signals may have reduced reliability."
        )
    else:
        price_class = "normal"
        price_adj = 0.0

    # --- Volume consistency check ---
    consistency_adj = 0.0
    if vol_cv > 2.0:
        consistency_adj = -0.1
        warnings.append(
            f"ERRATIC VOLUME: Volume coefficient of variation is {vol_cv:.1f} "
            "(normal < 1.0). Volume-based signals may be misleading."
        )

    # --- Indicator-specific reliability ---
    indicator_warnings: Dict[str, str] = {}

    if volume_class in ("very_low", "low"):
        indicator_warnings["obv"] = (
            "OBV is unreliable with low volume — small trades create "
            "outsized OBV movements."
        )
        indicator_warnings["cmf"] = (
            "Chaikin Money Flow is unreliable with low volume — "
            "accumulation/distribution signals are noisy."
        )
        indicator_warnings["vwap"] = (
            "VWAP is unreliable with low volume — institutional "
            "benchmark interpretation does not apply."
        )

    if price_class == "penny":
        indicator_warnings["bollinger"] = (
            "Bollinger Bands are unreliable for penny stocks — "
            "percentage moves are exaggerated."
        )
        indicator_warnings["patterns"] = (
            "Chart patterns are statistically unreliable below $5 — "
            "noise-to-signal ratio too high."
        )

    # --- Overall reliability grade ---
    total_adj = volume_adj + price_adj + consistency_adj

    if total_adj <= -0.5:
        grade = "unreliable"
    elif total_adj <= -0.2:
        grade = "caution"
    elif total_adj < 0:
        grade = "acceptable"
    else:
        grade = "reliable"

    return {
        "ticker": ticker.upper(),
        "reliability_grade": grade,
        "confidence_adjustment": round(total_adj, 2),
        "warnings": warnings,
        "indicator_warnings": indicator_warnings,
        "metrics": {
            "current_price": round(price, 2),
            "avg_volume_20d": round(avg_volume, 0),
            "avg_volume_total": round(total_avg_volume, 0),
            "volume_class": volume_class,
            "price_class": price_class,
            "adequate_volume_bar_pct": round(adequate_bar_pct, 1),
            "volume_cv": round(vol_cv, 2),
        },
    }


def apply_reliability_adjustments(
    evaluation: Dict[str, Any],
    reliability: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Enrich the evaluation dict with reliability information.

    Does NOT modify scores — only adds warnings and a confidence note.
    The reporting layer can use this to display appropriate caveats.

    Args:
        evaluation:  The full evaluation dict from ``evaluate_snapshot()``.
        reliability: The dict from ``validate_stock_reliability()``.

    Returns:
        The evaluation dict with added ``reliability`` key and expanded
        warnings.
    """
    evaluation["reliability"] = reliability

    # Add reliability warnings to the top-level warnings
    existing_warnings = evaluation.get("warnings", [])
    reliability_warnings = reliability.get("warnings", [])
    evaluation["warnings"] = existing_warnings + reliability_warnings

    # Adjust confidence level in experimental_score if grade is poor
    exp = evaluation.get("experimental_score", {})
    if exp.get("available") and reliability["reliability_grade"] in ("unreliable", "caution"):
        current_confidence = exp.get("confidence", "medium")
        if reliability["reliability_grade"] == "unreliable":
            exp["confidence"] = "low"
            exp["reliability_note"] = (
                "Confidence downgraded to 'low' due to unreliable "
                "volume/price characteristics."
            )
        elif reliability["reliability_grade"] == "caution" and current_confidence == "high":
            exp["confidence"] = "medium"
            exp["reliability_note"] = (
                "Confidence capped at 'medium' due to volume/price concerns."
            )

    return evaluation
