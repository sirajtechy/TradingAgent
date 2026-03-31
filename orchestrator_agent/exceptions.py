"""
exceptions.py — Custom exceptions for the orchestrator agent.
"""


class OrchestratorError(Exception):
    """Base exception for orchestrator failures."""


class BothAgentsFailedError(OrchestratorError):
    """Raised when both sub-agents fail (non-graceful path)."""
