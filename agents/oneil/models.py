"""
models.py — Data containers for the O'Neil Technical Analysis Agent.

Follows William O'Neil's CAN SLIM methodology:
  - Weekly bars as the primary chart view
  - Daily bars for secondary entry-precision analysis
  - Base pattern detection (Cup w/Handle, Double Bottom, Flat Base, Ascending Base)
  - Weinstein 4-stage market cycle classification
  - Structured output consumed directly by the Orchestrator Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Request
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ONeilRequest:
    """What the caller wants analysed."""

    ticker: str
    as_of_date: date
    exchange: str = "US"  # "US" (NASDAQ/NYSE) or "NSE" (India)


# ─────────────────────────────────────────────────────────────────────────────
# OHLCV bars
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WeeklyBar:
    """A single weekly OHLCV bar."""

    bar_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class DailyBar:
    """A single daily OHLCV bar (used for 200-day EMA + entry precision)."""

    bar_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


# ─────────────────────────────────────────────────────────────────────────────
# Base pattern
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BasePattern:
    """
    A detected O'Neil base pattern on weekly bars.

    All O'Neil base patterns are bullish consolidation setups.  The pivot
    is the optimal buy point — the exact price level where O'Neil says to
    purchase (typically the high of the base's right side or handle).
    """

    name: str                     # "Cup with Handle" | "Double Bottom" | "Flat Base" | "Ascending Base"
    direction: str                # always "bullish" for O'Neil bases
    confidence: float             # 0.0–1.0 composite quality score
    start_date: date              # First week of the base formation
    end_date: date                # Most recent week of the base / pivot bar
    base_duration_weeks: int      # Total weeks the base has been building
    pivot_level: float            # Optimal buy point (breakout level)
    base_depth_pct: float         # % decline from peak to trough of base
    base_number: int              # How many consecutive bases from the prior low (1=early, 3+=late)
    is_late_stage: bool           # base_number >= 3 → higher risk, lower success rate
    has_volume_dry_up: bool       # Volume contracting near base lows (bullish)
    description: str              # "Cup with Handle — 14-week base, 22% depth"


# ─────────────────────────────────────────────────────────────────────────────
# Stage analysis
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StageResult:
    """
    Weinstein 4-stage market cycle classification using the 30-week SMA.

    Stage 1 — Basing / Accumulation : consolidating below flat/declining 30wMA
    Stage 2 — Uptrend               : price above rising 30wMA → BUY ZONE
    Stage 3 — Distribution / Top    : consolidating near highs, 30wMA flattening
    Stage 4 — Downtrend             : price below declining 30wMA → AVOID
    """

    stage: int                    # 1, 2, 3, or 4
    description: str              # Human-readable label
    sma_30w: Optional[float]      # Current 30-week SMA value
    ma_slope: str                 # "rising" | "falling" | "flat"
    price_vs_ma: str              # "above" | "below"


# ─────────────────────────────────────────────────────────────────────────────
# Final signal (output to Orchestrator)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ONeilSignal:
    """
    Complete structured output of the O'Neil Technical Analysis Agent.

    Passed to the Orchestrator Engine alongside the Fundamental Agent's output.
    Call ``.to_dict()`` for JSON-serialisable orchestrator consumption.
    """

    # Identity
    ticker: str
    as_of_date: date

    # ── Signal ────────────────────────────────────────────────────────────
    direction: str                # "BULLISH" | "BEARISH" | "NEUTRAL"
    signal_strength: float        # 0.0–1.0 (composite quality)

    # ── Pattern ───────────────────────────────────────────────────────────
    pattern_detected: Optional[str]    # Pattern name + context string or None
    pattern_confidence: float          # 0.0–1.0
    is_late_stage: bool
    volume_dry_up: bool                # Volume dry-up at base lows (bullish)

    # ── Stage (Weinstein) ─────────────────────────────────────────────────
    market_stage: int             # 1–4
    stage_description: str

    # ── Trade Parameters ──────────────────────────────────────────────────
    last_close: float
    entry_price: Optional[float]       # Pivot / breakout level
    stop_loss: Optional[float]         # 7–8% below entry (O'Neil rule)
    target_price: Optional[float]      # Measured-move projected target
    risk_reward_ratio: Optional[float] # (target − entry) / (entry − stop)

    # ── Weekly Indicators ─────────────────────────────────────────────────
    rsi_14w: Optional[float]
    macd_line: Optional[float]
    macd_signal_line: Optional[float]
    macd_histogram: Optional[float]
    ema_10w: Optional[float]
    ema_21w: Optional[float]
    ema_50w: Optional[float]
    ema_200d: Optional[float]          # Daily 200 EMA (secondary timeframe)
    sma_30w: Optional[float]           # Weinstein stage moving average
    volume_ratio_10w: Optional[float]  # Current vol / 10-week avg vol

    # ── Confluence (0–4) ──────────────────────────────────────────────────
    # Counts how many of RSI, MACD, EMA-stack, Volume align with the signal
    confluence_score: int
    confluence_detail: Dict[str, bool]  # {"RSI": True, "MACD": False, ...}

    # ── Meta ──────────────────────────────────────────────────────────────
    summary: str
    warnings: List[str] = field(default_factory=list)

    # ─────────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict suitable for JSON / orchestrator consumption."""

        def _r(v: Optional[float], n: int = 4) -> Optional[float]:
            return round(v, n) if v is not None else None

        return {
            "ticker":             self.ticker,
            "as_of_date":         str(self.as_of_date),
            # Signal
            "direction":          self.direction,
            "signal_strength":    _r(self.signal_strength, 4),
            # Pattern
            "pattern_detected":   self.pattern_detected,
            "pattern_confidence": _r(self.pattern_confidence, 4),
            "is_late_stage":      self.is_late_stage,
            "volume_dry_up":      self.volume_dry_up,
            # Stage
            "market_stage":       self.market_stage,
            "stage_description":  self.stage_description,
            # Trade parameters
            "last_close":         self.last_close,
            "entry_price":        _r(self.entry_price, 4),
            "stop_loss":          _r(self.stop_loss, 4),
            "target_price":       _r(self.target_price, 4),
            "risk_reward_ratio":  _r(self.risk_reward_ratio, 2),
            # Indicators
            "rsi_14w":            _r(self.rsi_14w, 2),
            "macd_line":          _r(self.macd_line, 4),
            "macd_signal_line":   _r(self.macd_signal_line, 4),
            "macd_histogram":     _r(self.macd_histogram, 4),
            "ema_10w":            _r(self.ema_10w, 4),
            "ema_21w":            _r(self.ema_21w, 4),
            "ema_50w":            _r(self.ema_50w, 4),
            "ema_200d":           _r(self.ema_200d, 4),
            "sma_30w":            _r(self.sma_30w, 4),
            "volume_ratio_10w":   _r(self.volume_ratio_10w, 2),
            # Confluence
            "confluence_score":   self.confluence_score,
            "confluence_detail":  self.confluence_detail,
            # Meta
            "summary":            self.summary,
            "warnings":           self.warnings,
        }
