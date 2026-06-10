from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .exceptions import MacroConfigurationError


@dataclass(frozen=True)
class MacroSettings:
    api_key: str
    base_url: str = "https://api.stlouisfed.org/fred"
    timeout_seconds: int = 20
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    series_fed_funds: str = "DFF"
    series_cpi: str = "CPIAUCSL"
    series_unemployment: str = "UNRATE"
    series_yield_spread: str = "T10Y2Y"


def load_settings(api_key: Optional[str] = None) -> MacroSettings:
    resolved = api_key or os.getenv("FRED_API_KEY")
    if not resolved:
        raise MacroConfigurationError(
            "FRED_API_KEY not set — macro agent will use yfinance proxy fallback if enabled"
        )
    return MacroSettings(api_key=resolved)
