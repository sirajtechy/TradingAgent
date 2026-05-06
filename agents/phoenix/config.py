"""
config.py — PhoenixSettings: all tunable thresholds for the Phoenix Agent.

Every numeric threshold lives here so that backtests can sweep parameters
without touching business logic.  The dataclass is frozen (immutable) so
settings instances can be safely shared across LangGraph nodes.

Design notes:
  - Volume breakout multiple is 2.0× (Phoenix spec is strict — 1.5× is
    the Technical Agent; Phoenix requires the higher bar).
  - No RSI, MACD, Bollinger or Stochastics — explicitly rejected by the
    Phoenix Trader philosophy.
  - MA periods are all SMA (not EMA).
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class PhoenixSettings:
    """All tunable thresholds for the Phoenix trading agent."""

    # ── Volume ────────────────────────────────────────────────────────────
    volume_breakout_multiple: float = 2.0
    """Phoenix requires 2× average volume for a valid breakout (strict)."""

    volume_dryup_threshold: float = 0.75
    """Base volume < 75% of average = volume drying up (accumulation signal)."""

    volume_lookback_bars: int = 20
    """Number of bars used to compute the rolling average volume."""

    # ── MA periods (SMA only — no EMA in Phoenix) ─────────────────────────
    ma_short: int = 10
    ma_mid: int = 20
    ma_long: int = 50
    ma_trend: int = 200
    ma_40w: int = 200
    """40 weeks ≈ 200 trading days (used as macro trend context)."""

    # ── Hard pre-filters ──────────────────────────────────────────────────
    above_200dma_required: bool = True
    """Price must be above the 200-day SMA; fail-fast if not."""

    above_52w_low_pct: float = 0.50
    """Price must be at least 50% above the 52-week low."""

    # ── Stage gate ────────────────────────────────────────────────────────
    stage2_only: bool = True
    """Skip Stage 1, 3, and 4; only trade Stage 2 momentum stocks."""

    # ── Stage 2 slope sensitivity ─────────────────────────────────────────
    ma_slope_threshold_pct: float = 0.3
    """SMA20 must be rising by at least 0.3% vs prior bar to qualify as rising."""

    # ── Flat Base thresholds ──────────────────────────────────────────────
    flat_base_max_range_pct: float = 0.15
    """Maximum high-to-low range inside the base (<15% — tighter than Technical Agent's 25%)."""

    flat_base_min_bars: int = 20
    """Minimum bars in a flat base (~4 weeks)."""

    flat_base_max_bars: int = 120
    """Maximum bars in a flat base (~6 months)."""

    # ── VCP thresholds ────────────────────────────────────────────────────
    vcp_max_contractions: int = 3
    """Maximum number of VCP contraction cycles to look for."""

    vcp_min_depth_pct: float = 0.10
    """Each contraction must be at least 10% deep."""

    vcp_contraction_ratio: float = 0.50
    """Each successive contraction must be < 50% of the prior one (tightening)."""

    vcp_lookback_bars: int = 120
    """Bars to scan backward when searching for the VCP base peak."""

    # ── Tight Flag / Bull Flag thresholds ─────────────────────────────────
    flag_pole_min_gain_pct: float = 8.0
    """Flagpole must represent at least 8% gain from base to pole top."""

    flag_pole_max_bars: int = 15
    """Flagpole must form within 15 bars."""

    flag_max_retrace_pct: float = 0.50
    """Flag consolidation may retrace at most 50% of the flagpole."""

    flag_max_bars: int = 20
    """Maximum bars for the flag body before it's no longer a flag."""

    # ── Shakeout detection ────────────────────────────────────────────────
    shakeout_max_bars_below: int = 3
    """Dip below support must resolve within 3 bars (shakeout ≠ breakdown)."""

    shakeout_lookback_bars: int = 10
    """How many recent bars to scan for the initial dip below support."""

    # ── Pullback to MA entry ──────────────────────────────────────────────
    pullback_proximity_pct: float = 0.02
    """Price must be within 2% of MA10 or MA20 to qualify as a pullback entry."""

    pullback_prior_breakout_bars: int = 20
    """Look back this many bars for a prior breakout confirming we're in a trend."""

    # ── Scoring weights (must sum to 1.0) ─────────────────────────────────
    weight_volume: float = 0.40
    weight_structure: float = 0.30
    weight_pattern: float = 0.20
    weight_stage: float = 0.10

    # ── Signal thresholds ─────────────────────────────────────────────────
    buy_threshold: float = 70.0
    """Score >= 70 → BUY signal."""

    watch_threshold: float = 50.0
    """Score >= 50 → WATCH; score < 50 → AVOID."""

    # ── Risk management ───────────────────────────────────────────────────
    stop_buffer_pct: float = 0.001
    """0.1% below the Low Of breakout Candle (LOC) for the hard stop."""

    target_multiplier_1: float = 1.0
    """First price target = entry + 1× measured base height."""

    target_multiplier_2: float = 1.5
    """Second price target = entry + 1.5× measured base height."""

    capital_risk_pct: float = 0.01
    """1% of account size at risk per trade for position sizing."""

    def __post_init__(self) -> None:
        total = self.weight_volume + self.weight_structure + self.weight_pattern + self.weight_stage
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"PhoenixSettings: scoring weights must sum to 1.0, got {total:.4f}"
            )
