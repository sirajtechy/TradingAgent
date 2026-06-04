"""
DEPRECATED: backtests/common.py — Now a re-export shim.

Canonical location is core.universe. Import from there instead:

    from core.universe import HALAL_SECTORS, MONTHS, empty_matrix

This file remains for backward compatibility with existing scripts.
"""

from core.universe import (
    MONTHS,
    SECTORS,
    ALL_TICKERS,
    HALAL_SECTORS,
    HALAL_ALL_TICKERS,
    load_sector_tickers,
    load_all_tickers,
    empty_matrix,
    update_matrix,
    matrix_metrics,
    print_matrix,
)

__all__ = [
    "MONTHS",
    "SECTORS",
    "ALL_TICKERS",
    "HALAL_SECTORS",
    "HALAL_ALL_TICKERS",
    "load_sector_tickers",
    "load_all_tickers",
    "empty_matrix",
    "update_matrix",
    "matrix_metrics",
    "print_matrix",
]
