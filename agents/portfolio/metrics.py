"""Portfolio backtest performance metrics."""

from __future__ import annotations

import math
from datetime import date
from typing import Any, Dict, List, Optional, Tuple


def max_drawdown(equity_curve: List[Dict[str, Any]]) -> float:
    peak = 0.0
    max_dd = 0.0
    for pt in equity_curve:
        v = float(pt.get("total_value", 0))
        peak = max(peak, v)
        if peak > 0:
            dd = (peak - v) / peak * 100.0
            max_dd = max(max_dd, dd)
    return round(max_dd, 2)


def cagr(initial: float, final: float, start: date, end: date) -> Optional[float]:
    if initial <= 0 or final <= 0 or end <= start:
        return None
    years = (end - start).days / 365.25
    if years <= 0:
        return None
    return round(((final / initial) ** (1.0 / years) - 1.0) * 100.0, 2)


def monthly_returns_from_curve(equity_curve: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not equity_curve:
        return []
    by_month: Dict[str, float] = {}
    order: List[str] = []
    for pt in equity_curve:
        d = pt.get("as_of")
        if isinstance(d, date):
            key = d.strftime("%Y-%m")
        else:
            key = str(d)[:7]
        if key not in by_month:
            order.append(key)
        by_month[key] = float(pt.get("total_value", 0))

    out: List[Dict[str, Any]] = []
    prev: Optional[float] = None
    for key in order:
        val = by_month[key]
        if prev is None or prev <= 0:
            ret = None
        else:
            ret = round((val - prev) / prev * 100.0, 2)
        out.append({"month": key, "portfolio_value": round(val, 2), "return_pct": ret})
        prev = val
    return out


def sharpe_from_monthly(monthly: List[Dict[str, Any]], risk_free_pct: float = 0.0) -> Optional[float]:
    rets = [m["return_pct"] for m in monthly if m.get("return_pct") is not None]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std <= 0:
        return None
    monthly_rf = risk_free_pct / 12.0
    return round((mean - monthly_rf) / std * math.sqrt(12), 2)


def build_summary(
    *,
    initial: float,
    final: float,
    start: date,
    end: date,
    equity_curve: List[Dict[str, Any]],
    trade_count: int,
    regime_cash_months: int,
) -> Dict[str, Any]:
    monthly = monthly_returns_from_curve(equity_curve)
    return {
        "initial_budget": round(initial, 2),
        "final_value": round(final, 2),
        "total_return_pct": round((final - initial) / initial * 100.0, 2) if initial > 0 else None,
        "cagr_pct": cagr(initial, final, start, end),
        "max_drawdown_pct": max_drawdown(equity_curve),
        "sharpe_ratio": sharpe_from_monthly(monthly),
        "trade_count": trade_count,
        "regime_cash_rebalances": regime_cash_months,
        "months": len(monthly),
    }
