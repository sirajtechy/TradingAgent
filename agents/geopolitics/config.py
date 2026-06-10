from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .exceptions import GeopoliticsConfigurationError


@dataclass(frozen=True)
class GeopoliticsSettings:
    api_key: str
    base_url: str = "https://financialmodelingprep.com/stable"
    timeout_seconds: int = 20
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    news_limit: int = 50
    lookback_days: int = 7
    geo_keywords: Tuple[str, ...] = (
        "sanctions", "tariff", "trade war", "embargo",
        "conflict", "war", "invasion", "military",
        "geopolitical", "diplomacy", "treaty", "nato",
        "opec", "oil embargo", "energy crisis",
        "chip ban", "semiconductor restriction", "export control",
        "currency crisis", "central bank", "sovereign debt",
    )
    sector_exposure: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "Energy": ["oil", "opec", "energy crisis", "embargo", "sanctions"],
            "Information Technology": ["chip ban", "semiconductor", "export control", "tech war"],
            "Industrials": ["tariff", "trade war", "supply chain"],
            "Financials": ["sanctions", "currency crisis", "sovereign debt", "central bank"],
            "Materials": ["tariff", "rare earth", "trade war"],
        }
    )


def load_settings(api_key: Optional[str] = None) -> GeopoliticsSettings:
    resolved = api_key or os.getenv("FMP_API_KEY")
    if not resolved:
        raise GeopoliticsConfigurationError("FMP_API_KEY is required for the geopolitics agent")
    return GeopoliticsSettings(api_key=resolved)
