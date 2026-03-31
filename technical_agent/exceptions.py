"""
exceptions.py — Exception hierarchy for the technical analysis agent.

All exceptions inherit from TechnicalAgentError so callers can catch a
single type at the top level while still distinguishing specific failures.
"""


class TechnicalAgentError(Exception):
    """Base exception for the technical agent."""


class DataUnavailableError(TechnicalAgentError):
    """Raised when required price/volume data cannot be fetched from any source."""


class ConfigurationError(TechnicalAgentError):
    """Raised when required settings or environment values are missing."""


class InsufficientDataError(TechnicalAgentError):
    """Raised when downloaded data has too few bars for indicator computation."""
