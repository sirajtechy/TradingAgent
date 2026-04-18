"""
test_nyse_calendar.py — Tests for NYSE holiday-aware trading calendar.

Validates that:
  - Weekend days are correctly identified as non-trading days.
  - Known NYSE holidays are correctly identified as non-trading days.
  - _next_trading_day() skips holidays and weekends.
  - _count_trading_days_between() produces correct counts.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the calendar helpers from the technical predictor module
from agents.technical.predictor import (
    _is_trading_day,
    _next_trading_day,
    _count_trading_days_between,
)


# ---------------------------------------------------------------------------
# _is_trading_day
# ---------------------------------------------------------------------------

class TestIsTradingDay:

    def test_regular_monday_is_trading_day(self):
        """Monday 2024-01-08 is a regular trading day."""
        assert _is_trading_day(date(2024, 1, 8)) is True

    def test_saturday_is_not_trading_day(self):
        assert _is_trading_day(date(2024, 1, 6)) is False   # Saturday

    def test_sunday_is_not_trading_day(self):
        assert _is_trading_day(date(2024, 1, 7)) is False   # Sunday

    # ── Fixed NYSE holidays ──────────────────────────────────────────────

    def test_new_years_day_2024(self):
        """2024-01-01 is a Monday — NYSE observed on that Monday."""
        assert _is_trading_day(date(2024, 1, 1)) is False

    def test_mlk_day_2024(self):
        """MLK Day 2024: 3rd Monday of January = 2024-01-15."""
        assert _is_trading_day(date(2024, 1, 15)) is False

    def test_presidents_day_2024(self):
        """Presidents' Day 2024: 3rd Monday of February = 2024-02-19."""
        assert _is_trading_day(date(2024, 2, 19)) is False

    def test_good_friday_2024(self):
        """Good Friday 2024: 2024-03-29 (Easter Sunday = 2024-03-31)."""
        assert _is_trading_day(date(2024, 3, 29)) is False

    def test_memorial_day_2024(self):
        """Memorial Day 2024: last Monday of May = 2024-05-27."""
        assert _is_trading_day(date(2024, 5, 27)) is False

    def test_juneteenth_2024(self):
        """Juneteenth 2024: June 19 = Wednesday."""
        assert _is_trading_day(date(2024, 6, 19)) is False

    def test_independence_day_2024(self):
        """Independence Day 2024: July 4 = Thursday."""
        assert _is_trading_day(date(2024, 7, 4)) is False

    def test_labor_day_2024(self):
        """Labor Day 2024: 1st Monday of September = 2024-09-02."""
        assert _is_trading_day(date(2024, 9, 2)) is False

    def test_thanksgiving_2024(self):
        """Thanksgiving 2024: 4th Thursday of November = 2024-11-28."""
        assert _is_trading_day(date(2024, 11, 28)) is False

    def test_christmas_2024(self):
        """Christmas 2024: December 25 = Wednesday."""
        assert _is_trading_day(date(2024, 12, 25)) is False

    # ── Saturday/Sunday observance ───────────────────────────────────────

    def test_christmas_2021_observed_friday(self):
        """Christmas 2021: Dec 25 falls on Saturday → observed Fri Dec 24."""
        # Dec 24, 2021 is a Friday — observed holiday
        assert _is_trading_day(date(2021, 12, 24)) is False

    def test_independence_day_2021_observed_monday(self):
        """July 4, 2021 falls on Sunday → observed Mon July 5."""
        assert _is_trading_day(date(2021, 7, 5)) is False

    def test_new_years_2022_observed_friday(self):
        """Jan 1, 2022 falls on Saturday → observed Fri Dec 31, 2021."""
        assert _is_trading_day(date(2021, 12, 31)) is False

    # ── Days immediately around holidays should be trading days ──────────

    def test_day_after_christmas_2024_is_trading(self):
        """Dec 26, 2024 is a Thursday — regular trading day."""
        assert _is_trading_day(date(2024, 12, 26)) is True

    def test_day_before_mlk_2024_is_trading(self):
        """Jan 12, 2024 (Friday before MLK weekend) is a trading day."""
        assert _is_trading_day(date(2024, 1, 12)) is True


# ---------------------------------------------------------------------------
# _next_trading_day
# ---------------------------------------------------------------------------

class TestNextTradingDay:

    def test_friday_to_monday(self):
        """Next trading day after Friday Jan 5, 2024 is Monday Jan 8."""
        friday = date(2024, 1, 5)
        assert _next_trading_day(friday) == date(2024, 1, 8)

    def test_skip_holiday_mlk_2024(self):
        """Next trading day after Friday Jan 12, 2024 skips MLK (Mon Jan 15) → Tue Jan 16."""
        friday = date(2024, 1, 12)
        assert _next_trading_day(friday) == date(2024, 1, 16)

    def test_from_weekday_next_is_next_weekday(self):
        """Next trading day after Wednesday Jan 3, 2024 is Thursday Jan 4."""
        assert _next_trading_day(date(2024, 1, 3)) == date(2024, 1, 4)


# ---------------------------------------------------------------------------
# _count_trading_days_between
# ---------------------------------------------------------------------------

class TestCountTradingDaysBetween:

    def test_same_week_count(self):
        """_count_trading_days_between is exclusive on both ends.
        Mon Jan 8 → Fri Jan 12: counts Tue(9), Wed(10), Thu(11) = 3.
        """
        start = date(2024, 1, 8)   # Monday
        end   = date(2024, 1, 12)  # Friday
        assert _count_trading_days_between(start, end) == 3

    def test_count_over_weekend(self):
        """Fri Jan 5 → Mon Jan 8: no trading days strictly between them = 0."""
        start = date(2024, 1, 5)   # Friday
        end   = date(2024, 1, 8)   # Monday
        assert _count_trading_days_between(start, end) == 0

    def test_count_excludes_holiday(self):
        """Jan 12 (Fri) to Jan 19 (Fri): encloses Tue(16), Wed(17), Thu(18).
        MLK Mon(15) is excluded (holiday) → 3 days."""
        start = date(2024, 1, 12)  # Friday
        end   = date(2024, 1, 19)  # Friday
        # Between (exclusive): Mon(15)=holiday, Tue(16), Wed(17), Thu(18) = 3
        count = _count_trading_days_between(start, end)
        assert count == 3

    def test_start_equals_end(self):
        """start == end → returns 0 (no days strictly between them)."""
        d = date(2024, 1, 8)
        assert _count_trading_days_between(d, d) == 0

    def test_start_greater_than_end_returns_zero(self):
        """When start > end, returns 0."""
        assert _count_trading_days_between(date(2024, 1, 10), date(2024, 1, 8)) == 0

    def test_full_week_exclusive(self):
        """Mon → next Mon (7 days) = 4 trading days strictly between."""
        start = date(2024, 1, 8)   # Monday
        end   = date(2024, 1, 15)  # Monday MLK — holiday, not counted
        # Tue(9), Wed(10), Thu(11), Fri(12) = 4 days
        assert _count_trading_days_between(start, end) == 4
