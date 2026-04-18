"""
test_staleness.py — Tests for horizon-aware staleness threshold.

Verifies that the staleness threshold scales dynamically with the
target holding-period horizon, not a hardcoded flat constant.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.technical.predictor import _stale_days_threshold


class TestStaleDaysThreshold:

    def test_minimum_floor_enforced(self):
        """Very short horizons must not produce a threshold below 3."""
        assert _stale_days_threshold(1) >= 3
        assert _stale_days_threshold(5) >= 3
        assert _stale_days_threshold(0) >= 3

    def test_scales_with_horizon(self):
        """Longer horizons produce larger thresholds (1/3 of horizon)."""
        assert _stale_days_threshold(30) == max(3, 30 // 3)   # 10
        assert _stale_days_threshold(60) == max(3, 60 // 3)   # 20
        assert _stale_days_threshold(90) == max(3, 90 // 3)   # 30

    def test_default_30_day_horizon(self):
        """Standard 30-day horizon gives threshold of 10 days."""
        assert _stale_days_threshold(30) == 10

    def test_short_horizon_uses_floor(self):
        """Horizons ≤ 9 days hit the floor of 3."""
        for h in range(0, 10):
            val = _stale_days_threshold(h)
            assert val == 3, f"horizon={h} gave {val}, expected 3"

    def test_returns_int(self):
        """Output must be an integer for use in date comparisons."""
        result = _stale_days_threshold(30)
        assert isinstance(result, int)
