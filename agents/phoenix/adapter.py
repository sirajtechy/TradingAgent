"""Phoenix agent public adapter — envelope only; analyze via ``service.analyze_ticker``."""

from core.contracts.envelope import envelope_from_phoenix

__all__ = ["envelope_from_phoenix"]
