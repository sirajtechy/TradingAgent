class MacroConfigurationError(RuntimeError):
    """Raised when macro agent configuration is invalid."""


class MacroDataError(RuntimeError):
    """Raised when FRED or macro inputs cannot be fetched."""
