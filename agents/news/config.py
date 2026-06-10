from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

from .exceptions import NewsConfigurationError


@dataclass(frozen=True)
class NewsSettings:
    api_key: str
    base_url: str = "https://financialmodelingprep.com/stable"
    timeout_seconds: int = 20
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    news_limit: int = 30
    grades_limit: int = 20
    headline_lookback_days: int = 30
    priority_firms: List[str] = field(
        default_factory=lambda: [
            "Goldman Sachs",
            "Morgan Stanley",
        ]
    )


def load_settings(api_key: Optional[str] = None) -> NewsSettings:
    resolved = api_key or os.getenv("FMP_API_KEY")
    if not resolved:
        raise NewsConfigurationError("FMP_API_KEY is required for the news agent")
    return NewsSettings(api_key=resolved)
