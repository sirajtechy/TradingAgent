"""
orchestrator_agent — Confidence-Weighted Asymmetric Fusion (CWAF) of
the Technical Analysis Agent (v2) and Fundamental Analysis Agent (v3).
"""

from .service import analyze_ticker  # noqa: F401

__all__ = ["analyze_ticker"]
