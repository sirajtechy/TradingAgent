"""
config.py — Orchestrator settings and tuning constants.

All magic numbers from ORCHESTRATOR_DESIGN.md §2–4 live here so they
can be overridden in tests without monkey-patching.
"""

from __future__ import annotations

import dataclasses
from typing import List


@dataclasses.dataclass(frozen=True)
class FusionWeights:
    """Weight pairs (tech, fund) for each fusion scenario.

    Design rationale (v2 — post-FA-accuracy improvement):
    - FA now achieves 59.3% real accuracy vs TA at 54.9%.
    - When both agree, FA's fundamental signal deserves equal or greater
      weight than TA's technical signal.
    - When only FA fires, the score must reflect FA's signal (flip to FA-dominant).
    - When only TA fires, TA still leads but FA adds a meaningful hedge.
    - In conflicts, the winning agent determines direction; the score is
      computed with winner-heavy weights so the orchestrator score lands in
      the correct band (not washed out by the losing agent).
    """

    # Both agents agree on direction — FA slightly leads (better long-term accuracy)
    agreement: tuple = (0.45, 0.55)
    # Both agents neutral — equal weight
    agreement_neutral: tuple = (0.50, 0.50)
    # Only TA is directional — TA leads but FA provides a 15% hedge
    tech_only: tuple = (0.85, 0.15)
    # Only FA is directional — FA leads; TA neutral score (≈50) must not drown FA signal
    fund_only: tuple = (0.15, 0.85)
    # Conflict: tech wins over fund — score blends 70/30 so winner's band is reached
    conflict_ta_wins: tuple = (0.70, 0.30)
    # Conflict: fund wins over tech — score blends 30/70 so winner's band is reached
    conflict_fa_wins: tuple = (0.30, 0.70)
    # Conflict: near-equal confidence — abstain with balanced score
    conflict_equal: tuple = (0.50, 0.50)


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

    # Fundamental agent data_source for backtest
    fund_data_source: str = "yfinance"
