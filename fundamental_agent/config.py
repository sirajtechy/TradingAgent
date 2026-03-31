from dataclasses import dataclass
import os
from typing import Optional

from .exceptions import ConfigurationError


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str = "https://financialmodelingprep.com/stable"
    timeout_seconds: int = 20
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0


def load_settings(api_key: Optional[str] = None) -> Settings:
    resolved_api_key = api_key or os.getenv("FMP_API_KEY")
    if not resolved_api_key:
        raise ConfigurationError("FMP_API_KEY is required")
    return Settings(api_key=resolved_api_key)
