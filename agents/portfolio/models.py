"""Data models for portfolio engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class TickerScore:
    ticker: str
    sector: str
    rank: int
    conviction_score: float
    momentum_score: float
    components: Dict[str, float] = field(default_factory=dict)
    attribution: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Holding:
    ticker: str
    sector: str
    shares: float
    entry_date: date
    entry_price: float
    cost_basis: float
    rank_at_entry: int
    conviction_at_entry: float


@dataclass
class TradeRecord:
    date: date
    action: str
    ticker: str
    sector: str
    shares: float
    price: float
    proceeds: float
    rank: Optional[int]
    conviction: Optional[float]
    reason: str
    attribution: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioSnapshot:
    as_of: date
    cash: float
    equity_value: float
    total_value: float
    holdings: List[Dict[str, Any]]
    regime: str


@dataclass
class BacktestResult:
    run_id: str
    start_date: date
    end_date: date
    initial_budget: float
    final_value: float
    total_return_pct: float
    cagr_pct: Optional[float]
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]
    monthly_returns: List[Dict[str, Any]]
    equity_curve: List[Dict[str, Any]]
    trades: List[TradeRecord]
    snapshots: List[PortfolioSnapshot]
    summary: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
