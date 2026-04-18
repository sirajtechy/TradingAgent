"""
trade_filter.py — External trade-quality gate for the CWAF orchestrator.

Evaluates candidate BUY setups against market-structure requirements
before a bullish signal is allowed to generate a trade recommendation.

Architecture note:
    This filter runs AFTER fusion (post-CWAF), acting as a final
    admission gate.  It does NOT change the orchestrator's directional
    signal — it only attaches a ``trade_quality`` block to the result
    and can veto the trade by setting ``trade_allowed=False``.

Checks (all derived from OHLCV data — no external data dependencies):
    1. Base tightness     — max daily H/L range ≤ 3% over last 10 bars.
                           Tight bases indicate consolidation, not volatile chop.
    2. Volume contraction — average volume in the last 5 bars < average volume
                           in bars 6-15.  Healthy bases form on drying-up volume.
    3. Liquidity floor    — average daily dollar volume (close × volume) over
                           last 20 bars ≥ MIN_DOLLAR_VOL_M million USD.
                           Prevents entering illiquid names with wide spreads.
    4. Relative strength  — ticker's 63-bar return > SPY's 63-bar return.
                           Leading stocks should be outperforming the market.
                           (Optional: only runs when spy_closes is supplied.)
    5. Trend alignment    — price is above its 50-bar MA and slope of the
                           50-bar MA is positive (rising trend, not dead-cat).

Each check returns True (pass) or False (fail).  The overall result is
``trade_allowed = all checks pass`` for BUY signals.  SELL/neutral
signals are passed through unchanged with trade_allowed=True.

All functions are pure and accept plain Python lists for zero-dependency
use in unit tests.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Liquidity: minimum average daily dollar volume (USD)
MIN_DOLLAR_VOL_USD: float = 5_000_000.0   # $5M/day

# Tightness: max allowed mean daily range pct over last N bars
TIGHTNESS_LOOKBACK: int = 10
TIGHTNESS_MAX_RANGE_PCT: float = 3.0      # 3% H/L range

# Volume contraction
VOL_CONTRACTION_RECENT: int = 5           # bars
VOL_CONTRACTION_PRIOR: int = 10           # bars (prior window)

# Trend alignment
TREND_MA_PERIOD: int = 50


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def check_base_tightness(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    lookback: int = TIGHTNESS_LOOKBACK,
    max_range_pct: float = TIGHTNESS_MAX_RANGE_PCT,
) -> Dict[str, Any]:
    """
    Verify base tightness: mean daily H/L range ≤ max_range_pct% over
    the last *lookback* bars.

    Returns:
        {"passed": bool, "mean_range_pct": float, "threshold_pct": float}
    """
    n = min(lookback, len(highs), len(lows), len(closes))
    if n < 3:
        return {"passed": True, "mean_range_pct": None, "threshold_pct": max_range_pct,
                "note": "Insufficient bars for tightness check"}

    ranges_pct: List[float] = []
    for i in range(len(highs) - n, len(highs)):
        mid = closes[i] if closes[i] > 0 else (highs[i] + lows[i]) / 2
        if mid > 0:
            ranges_pct.append((highs[i] - lows[i]) / mid * 100.0)

    mean_range = _mean(ranges_pct) if ranges_pct else 0.0
    passed = mean_range <= max_range_pct
    return {
        "passed": passed,
        "mean_range_pct": round(mean_range, 3),
        "threshold_pct": max_range_pct,
    }


def check_volume_contraction(
    volumes: List[float],
    recent_bars: int = VOL_CONTRACTION_RECENT,
    prior_bars: int = VOL_CONTRACTION_PRIOR,
) -> Dict[str, Any]:
    """
    Verify volume is contracting: recent mean volume < prior mean volume.

    Returns:
        {"passed": bool, "recent_avg": float, "prior_avg": float, "ratio": float}
    """
    if len(volumes) < recent_bars + prior_bars:
        return {"passed": True, "recent_avg": None, "prior_avg": None, "ratio": None,
                "note": "Insufficient bars for volume contraction check"}

    recent = volumes[-recent_bars:]
    prior  = volumes[-(recent_bars + prior_bars): -recent_bars]

    recent_avg = _mean(recent)
    prior_avg  = _mean(prior)
    ratio = recent_avg / prior_avg if prior_avg > 0 else 1.0
    passed = ratio < 1.0   # recent < prior = contracting

    return {
        "passed": passed,
        "recent_avg": round(recent_avg, 0),
        "prior_avg":  round(prior_avg, 0),
        "ratio":      round(ratio, 3),
    }


def check_liquidity(
    closes: List[float],
    volumes: List[float],
    lookback: int = 20,
    min_dollar_vol: float = MIN_DOLLAR_VOL_USD,
) -> Dict[str, Any]:
    """
    Verify average daily dollar volume ≥ min_dollar_vol over last *lookback* bars.

    Returns:
        {"passed": bool, "avg_dollar_vol": float, "min_dollar_vol": float}
    """
    n = min(lookback, len(closes), len(volumes))
    if n < 5:
        return {"passed": True, "avg_dollar_vol": None, "min_dollar_vol": min_dollar_vol,
                "note": "Insufficient bars for liquidity check"}

    dollar_vols = [
        closes[i] * volumes[i]
        for i in range(len(closes) - n, len(closes))
        if closes[i] > 0 and volumes[i] > 0
    ]
    avg_dv = _mean(dollar_vols) if dollar_vols else 0.0
    passed = avg_dv >= min_dollar_vol

    return {
        "passed": passed,
        "avg_dollar_vol_m": round(avg_dv / 1_000_000, 2),
        "min_dollar_vol_m": round(min_dollar_vol / 1_000_000, 2),
    }


def check_relative_strength(
    ticker_closes: List[float],
    spy_closes: List[float],
    lookback: int = 63,
) -> Dict[str, Any]:
    """
    Verify ticker is outperforming SPY over the last *lookback* bars.

    Returns:
        {"passed": bool, "ticker_return_pct": float, "spy_return_pct": float}

    Returns passed=True with note when spy_closes is shorter than required
    (data not available).
    """
    n = lookback
    if len(ticker_closes) < n + 1 or len(spy_closes) < n + 1:
        return {"passed": True, "ticker_return_pct": None, "spy_return_pct": None,
                "note": "Insufficient SPY or ticker history for RS check"}

    def _return(prices: List[float]) -> float:
        start = prices[-n - 1]
        end   = prices[-1]
        return (end - start) / start * 100.0 if start > 0 else 0.0

    ticker_ret = _return(ticker_closes)
    spy_ret    = _return(spy_closes)
    passed = ticker_ret > spy_ret

    return {
        "passed": passed,
        "ticker_return_pct": round(ticker_ret, 2),
        "spy_return_pct":    round(spy_ret, 2),
        "rs_spread_pct":     round(ticker_ret - spy_ret, 2),
    }


def check_trend_alignment(
    closes: List[float],
    ma_period: int = TREND_MA_PERIOD,
) -> Dict[str, Any]:
    """
    Verify price is above its *ma_period* MA and the MA slope is positive (rising).

    Returns:
        {"passed": bool, "price_above_ma": bool, "ma_slope_positive": bool,
         "price": float, "ma": float}
    """
    if len(closes) < ma_period + 5:
        return {"passed": True, "price_above_ma": None, "ma_slope_positive": None,
                "note": f"Insufficient bars for {ma_period}-bar MA check"}

    ma_now  = _mean(closes[-ma_period:])
    ma_prev = _mean(closes[-(ma_period + 5): -5])
    price   = closes[-1]

    above_ma     = price > ma_now
    slope_pos    = ma_now > ma_prev
    passed       = above_ma and slope_pos

    return {
        "passed": passed,
        "price_above_ma":      above_ma,
        "ma_slope_positive":   slope_pos,
        "price":               round(price, 4),
        "ma":                  round(ma_now, 4),
    }


# ---------------------------------------------------------------------------
# Main gate function
# ---------------------------------------------------------------------------

def evaluate_trade_quality(
    signal: str,
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
    spy_closes: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Evaluate trade quality for a proposed direction.

    For BUY signals: runs all 5 checks.  Sets trade_allowed=False if any
    checks fail.
    For SELL / neutral: passes through unchanged (trade_allowed=True, no
    checks run — short-selling is out of scope for this system).

    Args:
        signal:      "bullish" | "bearish" | "neutral"
        closes:      Daily close prices, oldest-first.
        highs:       Daily high prices.
        lows:        Daily low prices.
        volumes:     Daily volumes.
        spy_closes:  SPY close prices for relative-strength check.
                     If None, RS check is skipped (passes by default).

    Returns:
        {
            "trade_allowed": bool,
            "checks": {
                "tightness":          {...},
                "volume_contraction": {...},
                "liquidity":          {...},
                "relative_strength":  {...},
                "trend_alignment":    {...},
            },
            "failed_checks": [str],   # check names that failed
            "veto_reason": str,       # human-readable reason or None
        }
    """
    # Non-BUY signals — no trade filtering needed
    if signal != "bullish":
        return {
            "trade_allowed": True,
            "checks": {},
            "failed_checks": [],
            "veto_reason": None,
        }

    checks = {
        "tightness":          check_base_tightness(highs, lows, closes),
        "volume_contraction": check_volume_contraction(volumes),
        "liquidity":          check_liquidity(closes, volumes),
        "relative_strength":  check_relative_strength(closes, spy_closes)
                              if spy_closes is not None
                              else {"passed": True, "note": "SPY data not provided"},
        "trend_alignment":    check_trend_alignment(closes),
    }

    failed = [name for name, result in checks.items() if not result.get("passed", True)]
    trade_allowed = len(failed) == 0

    veto_reason: Optional[str] = None
    if not trade_allowed:
        details = []
        for name in failed:
            c = checks[name]
            if name == "tightness":
                details.append(
                    f"base too wide ({c.get('mean_range_pct', '?'):.1f}% > "
                    f"{c.get('threshold_pct', '?'):.1f}%)"
                )
            elif name == "volume_contraction":
                details.append(
                    f"volume not contracting (ratio={c.get('ratio', '?'):.2f})"
                )
            elif name == "liquidity":
                details.append(
                    f"liquidity below floor (${c.get('avg_dollar_vol_m', '?'):.1f}M "
                    f"< ${c.get('min_dollar_vol_m', '?'):.1f}M)"
                )
            elif name == "relative_strength":
                details.append(
                    f"underperforming SPY (spread={c.get('rs_spread_pct', '?'):.1f}%)"
                )
            elif name == "trend_alignment":
                details.append(
                    f"trend not aligned (above_ma={c.get('price_above_ma')}, "
                    f"slope_pos={c.get('ma_slope_positive')})"
                )
        veto_reason = "Trade vetoed: " + "; ".join(details)

    return {
        "trade_allowed": trade_allowed,
        "checks": checks,
        "failed_checks": failed,
        "veto_reason": veto_reason,
    }
