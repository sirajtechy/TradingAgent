from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .exceptions import InsiderConfigurationError


@dataclass(frozen=True)
class InsiderSettings:
    api_key: str
    base_url: str = "https://financialmodelingprep.com/stable"
    timeout_seconds: int = 20
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    lookback_days: int = 90
    trade_limit: int = 100


def load_settings(api_key: Optional[str] = None) -> InsiderSettings:
    resolved = api_key or os.getenv("FMP_API_KEY")
    if not resolved:
        raise InsiderConfigurationError("FMP_API_KEY is required for the insider agent")
    return InsiderSettings(api_key=resolved)
