"""Walk-forward window helpers for threshold tuning (Phase T5)."""

from __future__ import annotations

from datetime import date
from typing import List, Sequence, Tuple


def split_walk_forward_windows(
    months: Sequence[Tuple[date, date]],
    *,
    train_size: int = 6,
    test_size: int = 1,
) -> List[Tuple[List[Tuple[date, date]], List[Tuple[date, date]]]]:
    """
    Rolling walk-forward splits over monthly (signal, result) pairs.

    Returns list of (train_months, test_months) tuples.
    """
    pairs = list(months)
    if train_size < 1 or test_size < 1 or len(pairs) < train_size + test_size:
        return []
    out: List[Tuple[List[Tuple[date, date]], List[Tuple[date, date]]]] = []
    i = 0
    while i + train_size + test_size <= len(pairs):
        train = pairs[i : i + train_size]
        test = pairs[i + train_size : i + train_size + test_size]
        out.append((train, test))
        i += test_size
    return out
