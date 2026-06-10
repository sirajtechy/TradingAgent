"""
config.py — Orchestrator settings and tuning constants.

All magic numbers from ORCHESTRATOR_DESIGN.md §2–4 live here so they
can be overridden in tests without monkey-patching.
"""

from __future__ import annotations

import dataclasses
from typing import Dict, List


@dataclasses.dataclass(frozen=True)
class FusionWeights:
    """Weight pairs (tech, fund) for CWAF scenarios.

    Mirrors ORCHESTRATOR_DESIGN.md and unit tests — agreement /
    neutral / single-agent use asymmetric FA tilt where documented.
    """

    agreement: tuple = (0.45, 0.55)
    agreement_neutral: tuple = (0.50, 0.50)
    tech_only: tuple = (0.85, 0.15)
    fund_only: tuple = (0.15, 0.85)
    # Conflict: blend toward the resolved direction (see fusion._conflict)
    conflict_fund_wins: tuple = (0.10, 0.90)
    conflict_tech_wins: tuple = (0.70, 0.30)
    conflict_abstain: tuple = (0.50, 0.50)


# Phoenix + Fundamental fusion — Phoenix-dominant blend (configurable later).
# Tuple is always (phoenix_slot, fund) i.e. ("tech" weight in FusionResult, fund weight).
PHOENIX_FUND_FUSION_WEIGHTS = FusionWeights(
    agreement=(0.90, 0.10),
    agreement_neutral=(0.90, 0.10),
    tech_only=(0.90, 0.10),
    fund_only=(0.10, 0.90),
    conflict_fund_wins=(0.10, 0.90),
    conflict_tech_wins=(0.90, 0.10),
    conflict_abstain=(0.90, 0.10),
)


@dataclasses.dataclass(frozen=True)
class OrchestratorSettings:
    """Central configuration for the CWAF fusion engine."""

    # Band boundary thresholds (used by agent_confidence)
    tech_thresholds: List[float] = dataclasses.field(
        default_factory=lambda: [35.0, 50.0, 60.0, 75.0]
    )
    fund_thresholds: List[float] = dataclasses.field(
        default_factory=lambda: [40.0, 62.0, 70.0, 85.0]
    )

    # Max possible distance for confidence normalisation
    confidence_max_distance: float = 25.0

    # Agreement multipliers
    bullish_agreement_bonus: float = 1.15
    bearish_agreement_bonus: float = 1.20

    # Discount factors
    tech_only_discount: float = 0.85
    fund_only_discount: float = 0.90
    poor_data_quality_discount: float = 0.90

    # Conflict resolution
    conflict_confidence_gap: float = 0.15
    conflict_winner_discount_fa: float = 0.75
    conflict_winner_discount_ta: float = 0.70
    conflict_abstain_confidence: float = 0.30
    agreement_neutral_confidence: float = 0.70

    # Anti-bullish guardrails — orchestrator band thresholds
    bullish_threshold: float = 62.0   # score ≥ 62 → bullish
    bearish_threshold: float = 38.0   # score < 38 → bearish
    # 38–62 → neutral

    # Bullish Confirmation Requirement:
    # If tech band is "mixed_positive" (weakest bullish) and fund is bearish,
    # downgrade to neutral.
    require_bullish_confirmation: bool = True

    # Weight tables
    weights: FusionWeights = dataclasses.field(default_factory=FusionWeights)

    # FusionWeights used only by fuse_signals_phoenix (Phoenix + FA). Defaults to 90/10 Phoenix/Fund.
    phoenix_fund_weights: FusionWeights = dataclasses.field(
        default_factory=lambda: PHOENIX_FUND_FUSION_WEIGHTS
    )

    # Fundamental agent data_source — "yfinance" (free, no API key) or "fmp" (paid)
    fund_data_source: str = "yfinance"

    # Full-context fusion slot weights (sum to 1.0). market_summary is regime overlay only.
    full_context_weights: Dict[str, float] = dataclasses.field(
        default_factory=lambda: {
            "phoenix": 0.55,
            "fundamental": 0.10,
            "macro": 0.10,
            "news": 0.10,
            "insider": 0.08,
            "geopolitics": 0.07,
        }
    )

    strong_buy_min_score: float = 65.0
    regime_vix_cap_score: float = 62.0
