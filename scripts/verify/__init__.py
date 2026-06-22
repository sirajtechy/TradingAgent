"""
Isolated backtest output verification — audit-only, not used by live backtests.

Re-fetches Polygon bars independently and compares price/outcome fields
against finished backtest artifacts (master_pilot.json, pilot_results.json, etc.).
"""

from .models import CheckResult, VerifyReport, VerifyRow
from .artifact_loader import load_verify_rows
from .runner import run_verification

__all__ = [
    "VerifyRow",
    "VerifyReport",
    "CheckResult",
    "load_verify_rows",
    "run_verification",
]
