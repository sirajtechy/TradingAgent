class InsiderConfigurationError(RuntimeError):
    """Raised when insider agent configuration is invalid."""


class InsiderDataError(RuntimeError):
    """Raised when FMP insider endpoints fail after retries."""
