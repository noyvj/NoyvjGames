"""Tests for clock.clock_minutes."""

import clock
import data


def test_clock_minutes_advances_by_tick_size():
    """Normal case: each tick adds TICK_MINUTES to the clock."""
    night = 1
    t0 = clock.clock_minutes(night, 0)
    t1 = clock.clock_minutes(night, 1)
    assert t1 - t0 == data.TICK_MINUTES


def test_clock_minutes_respects_season_start_times():
    """Normal case: different seasons start at different clock times."""
    night_spring = 1
    night_winter = 31
    start_spring = data.NIGHT_START_MIN[clock.season_of(night_spring)]
    start_winter = data.NIGHT_START_MIN[clock.season_of(night_winter)]

    assert clock.clock_minutes(night_spring, 0) == start_spring
    assert clock.clock_minutes(night_winter, 0) == start_winter


def test_clock_minutes_wraps_past_midnight():
    """Edge case: when accumulated minutes exceed 1440, it wraps modulo 1440."""
    night = 1
    start = data.NIGHT_START_MIN[clock.season_of(night)]
    # Calculate the first tick that crosses midnight
    ticks_to_midnight = (1440 - start + data.TICK_MINUTES - 1) // data.TICK_MINUTES
    before = clock.clock_minutes(night, ticks_to_midnight - 1)
    after = clock.clock_minutes(night, ticks_to_midnight)

    assert before > 1200
    assert after < 300
    assert (before + data.TICK_MINUTES) % 1440 == after
