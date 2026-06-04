"""
orchestrator — Confidence-Weighted Asymmetric Fusion (CWAF) of Phoenix + Fundamental.

Legacy TA+FA LangGraph path lives in ``archive/agents/orchestrator-ta-fa/``.
"""

from .fusion_phoenix import fuse_signals_phoenix  # noqa: F401
from .modes import FusionMode, fuse_by_mode  # noqa: F401

__all__ = ["fuse_signals_phoenix", "FusionMode", "fuse_by_mode"]
