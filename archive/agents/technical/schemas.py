"""
schemas.py — Pydantic typed contracts for the Technical Agent public API.

These models define the shape of inputs and outputs for ``predict_trade()``
and ``analyze_ticker()``.  All downstream callers (API layer, orchestrator,
backtest engine) should use these models instead of raw dicts.

Usage:
    from agents.technical.schemas import TechnicalRequest, TechnicalResponse

    req = TechnicalRequest(ticker="AAPL", cutoff_date=date.today())
    resp = TechnicalResponse(**result_dict)
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class TechnicalRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol, e.g. 'AAPL'.")
    cutoff_date: date = Field(..., description="Analysis date. All data is on/before this date.")
    target_days: int = Field(default=10, ge=2, le=30,
                             description="Maximum trade simulation window in trading days.")


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------

class PatternResult(BaseModel):
    name: str
    direction: Literal["bullish", "bearish"]
    confidence: float = Field(ge=0.0, le=1.0)
    formation_start: Optional[date] = None
    formation_end: Optional[date] = None
    breakout_confirmed: bool
    volume_confirmation: bool
    breakout_price: Optional[float] = None
    breakout_date: Optional[date] = None
    pattern_target: Optional[float] = None
    description: str = ""


# ---------------------------------------------------------------------------
# Trade setup (populated when a valid LONG trade is found)
# ---------------------------------------------------------------------------

class TradeSetup(BaseModel):
    entry_date: date
    entry_price: float
    entry_source: str = Field(
        description="e.g. 'pattern:Ascending Triangle' — identifies structural basis")
    exit_date: date
    exit_price: float
    exit_outcome: Literal["HIT_TARGET", "HIT_STOP", "EXPIRED", "OPEN"]
    holding_days: int
    bars_simulated: int
    stop_loss: float
    target_price: float
    gross_profit_pct: float
    net_profit_pct: float
    risk_pct: float
    reward_risk_ratio: Optional[float] = None
    atr_at_entry: Optional[float] = None
    adx_at_entry: Optional[float] = None
    rsi_at_entry: Optional[float] = None
    true_breakout_date: Optional[date] = None
    days_since_breakout: Optional[int] = None
    friction_pct: float = 0.20


# ---------------------------------------------------------------------------
# Full response
# ---------------------------------------------------------------------------

class TechnicalResponse(BaseModel):
    ticker: str
    cutoff_date: date
    target_days_requested: int
    sentiment: Literal["bullish", "neutral", "bearish"]
    confidence_score: float
    confidence_pct: float
    tech_score: float
    fund_score: float
    fusion_weights: Dict[str, Any] = Field(default_factory=dict)
    conflict_detected: bool = False
    conflict_resolution: Optional[str] = None

    # None when no valid LONG trade
    trade: Optional[TradeSetup] = None
    no_trade_reason: Optional[str] = None

    patterns: List[PatternResult] = Field(default_factory=list)
    signal_alignment: Dict[str, Any] = Field(default_factory=dict)
    orchestrator_score: float
    orchestrator_confidence: float
