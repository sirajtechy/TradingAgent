class GeopoliticsConfigurationError(RuntimeError):
    """Raised when geopolitics agent configuration is invalid."""


class GeopoliticsDataError(RuntimeError):
    """Raised when FMP news endpoints fail after retries."""
