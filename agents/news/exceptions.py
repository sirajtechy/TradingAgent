class NewsConfigurationError(RuntimeError):
    """Raised when news agent configuration is invalid."""


class NewsDataError(RuntimeError):
    """Raised when FMP news/grades endpoints fail after retries."""
