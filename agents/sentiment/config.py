from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SentimentSettings:
    """Weights for fusing dimension scores into the composite sentiment score."""
    weight_news: float = 0.30
    weight_analyst: float = 0.25
    weight_insider: float = 0.20
    weight_macro: float = 0.15
    weight_geopolitics: float = 0.10
