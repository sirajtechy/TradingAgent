"""Backtest evaluation helpers — confusion matrices, walk-forward splits."""

from .confusion import (
    AGENT_SIGNAL_SPECS,
    build_confusion_payload,
    confusion_from_rows,
    mcc,
)
from .walk_forward import split_walk_forward_windows

__all__ = [
    "AGENT_SIGNAL_SPECS",
    "build_confusion_payload",
    "confusion_from_rows",
    "mcc",
    "split_walk_forward_windows",
]
