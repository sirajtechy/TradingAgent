"""
volume_analysis.py — Sector-relative volume analysis module.

Compares a stock's volume characteristics against sector peers to identify
anomalous activity that may signal institutional accumulation or distribution.

Features:
    - Sector peer volume ranking (by market cap and average daily volume)
    - Stock volume vs sector median comparison
    - Volume anomaly detection (>2σ above/below sector median)
    - Relative volume ratio (current vs 20-day average)
    - Sector volume trend analysis

This module is called after the main analysis to enrich the evaluation
with sector context.  It is NOT part of the core scoring pipeline — it
provides supplementary intelligence.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ====================================================================== #
# SECTOR PEER DEFINITIONS                                                   #
# ====================================================================== #

# Curated sector → tickers mapping for reliable peer comparison.
# These are high-liquidity, widely-held stocks in each sector.
SECTOR_PEERS: Dict[str, List[str]] = {
    "Technology": [
        "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AVGO", "CRM",
        "ORCL", "AMD", "INTC", "ADBE", "NOW", "ANET",
    ],
    "Energy": [
        "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX",
        "VLO", "OXY", "DVN", "HAL", "BKR",
    ],
    "Financials": [
        "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK",
        "SCHW", "AXP", "USB", "PNC", "TFC",
    ],
    "Healthcare": [
        "UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO",
        "ABT", "BMY", "AMGN", "CI", "HUM", "CVS",
    ],
    "Consumer Staples": [
        "PG", "KO", "PEP", "COST", "WMT", "PM", "MO",
        "CL", "GIS", "KHC", "CLX", "SJM",
    ],
    "Consumer Discretionary": [
        "AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW",
        "TJX", "BKNG", "CMG",
    ],
    "Industrials": [
        "CAT", "DE", "HON", "UNP", "RTX", "LMT", "GE",
        "BA", "MMM", "UPS", "FDX",
    ],
    "Utilities": [
        "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE",
        "XEL", "WEC", "ES",
    ],
    "Real Estate": [
        "AMT", "PLD", "CCI", "EQIX", "SPG", "PSA", "O",
        "WELL", "DLR", "AVB",
    ],
    "Materials": [
        "LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE",
        "DD", "DOW", "PPG",
    ],
    "Communication Services": [
        "GOOGL", "META", "DIS", "NFLX", "CMCSA", "T", "VZ",
        "TMUS", "CHTR", "EA",
    ],
}


def get_sector_peers(sector: str, ticker: str) -> List[str]:
    """
    Get peer tickers for a given sector, excluding the target ticker.

    Args:
        sector:  The stock's sector (e.g. "Technology").
        ticker:  The stock being analyzed (will be excluded from peers).

    Returns:
        List of peer ticker symbols.  Empty if sector is unknown.
    """
    peers = SECTOR_PEERS.get(sector, [])
    return [p for p in peers if p.upper() != ticker.upper()]


# ====================================================================== #
# VOLUME METRICS                                                            #
# ====================================================================== #

def compute_volume_metrics(
    volumes: List[float],
    window: int = 20,
) -> Dict[str, Optional[float]]:
    """
    Compute volume statistics for a single stock.

    Args:
        volumes: Daily volume series (oldest-first).
        window:  Rolling window for average (default 20 trading days).

    Returns:
        Dict with avg_volume_20d, latest_volume, relative_volume_ratio,
        volume_trend (rising/falling/flat), volume_std_20d.
    """
    if not volumes or len(volumes) < window:
        return {
            "avg_volume_20d": None,
            "latest_volume": volumes[-1] if volumes else None,
            "relative_volume_ratio": None,
            "volume_trend": None,
            "volume_std_20d": None,
        }

    recent = volumes[-window:]
    avg_vol = sum(recent) / len(recent)
    latest = volumes[-1]

    # Standard deviation
    variance = sum((v - avg_vol) ** 2 for v in recent) / len(recent)
    std_vol = variance ** 0.5

    # Relative volume ratio: current vs 20-day average
    rvol = latest / avg_vol if avg_vol > 0 else None

    # Volume trend: compare first half vs second half of window
    half = window // 2
    first_half_avg = sum(recent[:half]) / half if half > 0 else 0
    second_half_avg = sum(recent[half:]) / (window - half) if (window - half) > 0 else 0

    if first_half_avg > 0:
        trend_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        if trend_pct > 10:
            vol_trend = "rising"
        elif trend_pct < -10:
            vol_trend = "falling"
        else:
            vol_trend = "flat"
    else:
        vol_trend = None

    return {
        "avg_volume_20d": round(avg_vol, 0),
        "latest_volume": round(latest, 0),
        "relative_volume_ratio": round(rvol, 2) if rvol is not None else None,
        "volume_trend": vol_trend,
        "volume_std_20d": round(std_vol, 0),
    }


def analyze_sector_relative_volume(
    ticker_volumes: Dict[str, Optional[float]],
    target_ticker: str,
) -> Dict[str, Any]:
    """
    Compare a stock's average volume against sector peers.

    Args:
        ticker_volumes: Dict of ticker → average 20-day volume.
                        None values indicate data unavailable.
        target_ticker:  The stock being analyzed.

    Returns:
        Dict with sector_median_volume, percentile_rank,
        is_anomalous, anomaly_direction, z_score, warnings.
    """
    target_vol = ticker_volumes.get(target_ticker.upper())
    peer_vols = [
        v for t, v in ticker_volumes.items()
        if t.upper() != target_ticker.upper() and v is not None and v > 0
    ]

    warnings: List[str] = []

    if target_vol is None:
        return {
            "sector_median_volume": None,
            "percentile_rank": None,
            "is_anomalous": False,
            "anomaly_direction": None,
            "z_score": None,
            "warnings": ["Volume data unavailable for target ticker."],
        }

    if len(peer_vols) < 3:
        warnings.append(
            f"Only {len(peer_vols)} peers with volume data — sector "
            "comparison may not be reliable."
        )

    if not peer_vols:
        return {
            "sector_median_volume": None,
            "percentile_rank": None,
            "is_anomalous": False,
            "anomaly_direction": None,
            "z_score": None,
            "warnings": ["No peer volume data available for comparison."],
        }

    # Sector statistics
    sorted_vols = sorted(peer_vols)
    n = len(sorted_vols)
    median_vol = sorted_vols[n // 2] if n % 2 == 1 else (
        (sorted_vols[n // 2 - 1] + sorted_vols[n // 2]) / 2.0
    )
    mean_vol = sum(sorted_vols) / n
    variance = sum((v - mean_vol) ** 2 for v in sorted_vols) / n
    std_vol = variance ** 0.5

    # Percentile rank
    below = sum(1 for v in sorted_vols if v < target_vol)
    percentile = (below / n) * 100.0

    # Z-score anomaly detection
    z_score = (target_vol - mean_vol) / std_vol if std_vol > 0 else 0.0
    is_anomalous = abs(z_score) > 2.0
    anomaly_direction = None
    if z_score > 2.0:
        anomaly_direction = "above"
        warnings.append(
            f"Volume is {z_score:.1f}σ above sector mean — "
            "unusually high activity detected."
        )
    elif z_score < -2.0:
        anomaly_direction = "below"
        warnings.append(
            f"Volume is {abs(z_score):.1f}σ below sector mean — "
            "unusually low liquidity."
        )

    return {
        "sector_median_volume": round(median_vol, 0),
        "sector_mean_volume": round(mean_vol, 0),
        "percentile_rank": round(percentile, 1),
        "is_anomalous": is_anomalous,
        "anomaly_direction": anomaly_direction,
        "z_score": round(z_score, 2),
        "peer_count": n,
        "warnings": warnings,
    }


def build_volume_analysis_report(
    ticker: str,
    stock_metrics: Dict[str, Optional[float]],
    sector_analysis: Dict[str, Any],
    sector: str,
) -> Dict[str, Any]:
    """
    Combine stock-level and sector-level volume analysis into a report.

    Args:
        ticker:          Stock symbol.
        stock_metrics:   Output of ``compute_volume_metrics()``.
        sector_analysis: Output of ``analyze_sector_relative_volume()``.
        sector:          Sector name.

    Returns:
        Complete volume analysis dict for inclusion in the evaluation.
    """
    return {
        "ticker": ticker.upper(),
        "sector": sector,
        "stock_volume": stock_metrics,
        "sector_comparison": sector_analysis,
        "summary": _build_volume_summary(stock_metrics, sector_analysis),
    }


def _build_volume_summary(
    stock_metrics: Dict[str, Optional[float]],
    sector_analysis: Dict[str, Any],
) -> str:
    """Generate a one-line human-readable volume summary."""
    parts = []

    rvol = stock_metrics.get("relative_volume_ratio")
    if rvol is not None:
        if rvol > 2.0:
            parts.append(f"Relative volume {rvol:.1f}x (very high)")
        elif rvol > 1.5:
            parts.append(f"Relative volume {rvol:.1f}x (elevated)")
        elif rvol < 0.5:
            parts.append(f"Relative volume {rvol:.1f}x (very low)")
        else:
            parts.append(f"Relative volume {rvol:.1f}x (normal)")

    pct = sector_analysis.get("percentile_rank")
    if pct is not None:
        parts.append(f"Sector volume percentile: {pct:.0f}th")

    if sector_analysis.get("is_anomalous"):
        direction = sector_analysis.get("anomaly_direction", "unusual")
        parts.append(f"ANOMALY: volume {direction} sector norm")

    return "; ".join(parts) if parts else "Volume analysis data insufficient."
