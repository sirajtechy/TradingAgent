from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class MarketSummarySettings:
    benchmark_ticker: str = "SPY"
    vix_ticker: str = "I:VIX"
    sector_etfs: Tuple[str, ...] = (
        "XLC",
        "XLY",
        "XLP",
        "XLE",
        "XLF",
        "XLV",
        "XLI",
        "XLB",
        "XLRE",
        "XLK",
        "XLU",
    )
    lookback_days: int = 35
    short_window: int = 5
    long_window: int = 20
    vix_low: float = 15.0
    vix_normal: float = 20.0
    vix_fear: float = 30.0

    sector_labels: Dict[str, str] = field(
        default_factory=lambda: {
            "XLC": "Communication Services",
            "XLY": "Consumer Discretionary",
            "XLP": "Consumer Staples",
            "XLE": "Energy",
            "XLF": "Financials",
            "XLV": "Health Care",
            "XLI": "Industrials",
            "XLB": "Materials",
            "XLRE": "Real Estate",
            "XLK": "Information Technology",
            "XLU": "Utilities",
        }
    )
