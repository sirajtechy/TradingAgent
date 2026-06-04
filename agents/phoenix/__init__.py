"""
agents/phoenix — Phoenix Trader strategy agent.

Session 1 (Foundation):
  PhoenixDataClient   — fetch Polygon OHLCV + compute SMAs/volume/52w stats
  apply_hard_filters  — 200DMA + 52w-low hard pre-filters
  PhoenixSettings     — all tunable thresholds
  PhoenixSnapshot     — primary data carrier

Session 2 (Stage + Patterns):
  classify_stage      — Stage 1/2/3/4 daily-bar classifier
  detect_all_patterns — VCP / Flat Base / Tight Flag / Shakeout / Pullback

Session 3 (Entry + Risk + Scoring):
  evaluate_entry      — map pattern → 4 Phoenix entry types + entry price
  compute_risk        — LOC stop, targets, R/R, position sizing
  build_score         — Phoenix composite score 0–100 (no RSI/MACD/BB)

Session 4 (Graph + Service + Reporting + Backtest):
  build_text_report   — human-readable terminal report from PhoenixSignal
  build_graph         — compiled LangGraph 8-node pipeline
  analyze_ticker      — one-call public API (ticker, date → dict)
  run_monthly_backtest— monthly backtest engine
"""

from .config import PhoenixSettings
from .data_client import PhoenixDataClient
from .exceptions import (
    HardFilterRejected,
    InsufficientDataError,
    PhoenixAgentError,
    StageFilterRejected,
)
from .filters import FilterResult, apply_hard_filters
from .models import (
    EntrySetup,
    OHLCVBar,
    PatternMatch,
    PhoenixRequest,
    PhoenixSignal,
    PhoenixSnapshot,
    RiskLevels,
    SMABundle,
    StageResult,
)
from .backtest import build_backtest_months, run_monthly_backtest
from .entry import evaluate_entry
from .graph import build_graph
from .patterns import detect_all_patterns
from .reporting import build_text_report
from .risk import compute_risk
from .scoring import build_score
from .service import analyze_ticker
from .stage_classifier import classify_stage

__all__ = [
    # Config
    "PhoenixSettings",
    # Data
    "PhoenixDataClient",
    # Exceptions
    "PhoenixAgentError",
    "HardFilterRejected",
    "StageFilterRejected",
    "InsufficientDataError",
    # Filters
    "apply_hard_filters",
    "FilterResult",
    # Stage
    "classify_stage",
    # Patterns
    "detect_all_patterns",
    # Entry / Risk / Score
    "evaluate_entry",
    "compute_risk",
    "build_score",
    # Session 4
    "build_text_report",
    "build_graph",
    "analyze_ticker",
    "run_monthly_backtest",
    "build_backtest_months",
    # Models
    "PhoenixRequest",
    "OHLCVBar",
    "SMABundle",
    "PhoenixSnapshot",
    "StageResult",
    "PatternMatch",
    "EntrySetup",
    "RiskLevels",
    "PhoenixSignal",
]
