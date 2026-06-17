"""Price-based momentum and conviction scoring."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from agents.portfolio.config import PortfolioRules
from agents.portfolio.models import TickerScore
from agents.strategies.common.features import compute_rs_rank

from agents.phoenix.models import OHLCVBar


def _bars_from_df(df: pd.DataFrame) -> List[OHLCVBar]:
    bars: List[OHLCVBar] = []
    for idx, row in df.iterrows():
        bar_date = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
        bars.append(
            OHLCVBar(
                bar_date=bar_date,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row.get("Volume", 0)),
            )
        )
    return bars


def period_return(closes: pd.Series, days: int) -> Optional[float]:
    if len(closes) < days + 1:
        return None
    c0 = float(closes.iloc[-days - 1])
    c1 = float(closes.iloc[-1])
    if c0 <= 0:
        return None
    return (c1 - c0) / c0 * 100.0


def period_volatility(closes: pd.Series, days: int) -> Optional[float]:
    if len(closes) < days + 1:
        return None
    rets = closes.pct_change().dropna().iloc[-days:]
    if rets.empty:
        return None
    return float(rets.std() * 100.0)


def avg_dollar_volume(df: pd.DataFrame, days: int = 20) -> Optional[float]:
    if df is None or df.empty or len(df) < days:
        return None
    window = df.iloc[-days:]
    adv = (window["Close"] * window["Volume"]).mean()
    return float(adv) if adv > 0 else None


def compute_momentum_score(
    df: pd.DataFrame,
    rules: PortfolioRules,
) -> Tuple[Optional[float], Dict[str, float]]:
    """Video-style: weighted multi-horizon returns divided by 3M volatility."""
    closes = df["Close"]
    lb = rules.momentum_lookbacks or {"1m": 21, "3m": 63, "6m": 126, "9m": 189}
    w = rules.momentum_weights or {"1m": 0.33, "6m": 0.34, "9m": 0.33}

    r1 = period_return(closes, lb.get("1m", 21))
    r6 = period_return(closes, lb.get("6m", 126))
    r9 = period_return(closes, lb.get("9m", 189))
    vol3 = period_volatility(closes, lb.get("3m", 63))

    parts: Dict[str, float] = {}
    weighted_sum = 0.0
    weight_total = 0.0
    for key, ret in (("1m", r1), ("6m", r6), ("9m", r9)):
        if ret is None:
            continue
        wt = float(w.get(key, 0.0))
        parts[f"return_{key}"] = round(ret, 3)
        weighted_sum += ret * wt
        weight_total += wt

    if weight_total <= 0:
        return None, parts

    raw = weighted_sum / weight_total
    if vol3 and vol3 > 0:
        score = raw / vol3
        parts["volatility_3m"] = round(vol3, 3)
    else:
        score = raw
    parts["momentum_raw"] = round(raw, 3)
    return round(score, 4), parts


def compute_conviction_score(
    *,
    momentum_score: float,
    rs_rank: Optional[float],
    agent_scores: Optional[Dict[str, float]] = None,
    rules: PortfolioRules,
) -> Tuple[float, Dict[str, float]]:
    """Blend momentum with optional agent subscores (0–100 scale)."""
    w = rules.conviction_weights or {}
    agent_scores = agent_scores or {}

    components: Dict[str, float] = {
        "cross_sectional_momentum": momentum_score,
        "relative_strength_vs_spy": rs_rank or 50.0,
        "phoenix_fusion_score": agent_scores.get("phoenix_fusion_score", 50.0),
        "strategy_blend_score": agent_scores.get("strategy_blend_score", 50.0),
        "intelligence_consensus": agent_scores.get("intelligence_consensus", 50.0),
        "smoothness": agent_scores.get("smoothness", 50.0),
    }

    total_w = 0.0
    blended = 0.0
    for key, val in components.items():
        wt = float(w.get(key, 0.0))
        if wt <= 0:
            continue
        # Normalize momentum to 0-100 heuristic
        norm_val = val
        if key == "cross_sectional_momentum":
            norm_val = max(0.0, min(100.0, 50.0 + val * 5.0))
        total_w += wt
        blended += norm_val * wt

    if total_w <= 0:
        return momentum_score, components

    return round(blended / total_w, 2), components


def rank_universe(
    *,
    price_data: Dict[str, pd.DataFrame],
    spy_df: Optional[pd.DataFrame],
    ticker_to_sector: Dict[str, str],
    rules: PortfolioRules,
    agent_enrichment: Optional[Dict[str, Dict[str, float]]] = None,
    as_of: date,
) -> List[TickerScore]:
    """Score and rank all tickers with available price history."""
    spy_bars = _bars_from_df(spy_df) if spy_df is not None and not spy_df.empty else []
    scored: List[TickerScore] = []

    for ticker, df in price_data.items():
        if df is None or df.empty:
            continue
        adv = avg_dollar_volume(df)
        if adv is not None and adv < rules.min_avg_dollar_volume:
            continue

        mom, mom_parts = compute_momentum_score(df, rules)
        if mom is None:
            continue

        bars = _bars_from_df(df)
        rs = compute_rs_rank(bars, spy_bars, period=63) if spy_bars else None
        enrich = (agent_enrichment or {}).get(ticker.upper())
        conviction, components = compute_conviction_score(
            momentum_score=mom,
            rs_rank=rs,
            agent_scores=enrich,
            rules=rules,
        )

        scored.append(
            TickerScore(
                ticker=ticker.upper(),
                sector=ticker_to_sector.get(ticker.upper(), "Unknown"),
                rank=0,
                conviction_score=conviction,
                momentum_score=mom,
                components={**mom_parts, **{f"conv_{k}": v for k, v in components.items()}},
                attribution={"as_of": as_of.isoformat(), "rs_rank": rs},
            )
        )

    scored.sort(key=lambda x: x.conviction_score, reverse=True)
    for i, row in enumerate(scored, start=1):
        row.rank = i
    return scored
