"""Tests for bodies.period_seconds()."""


import bodies


def test_earth_period_seconds_matches_one_year():
    """Earth's orbital period should be approximately one year in seconds."""
    earth = bodies.planet("earth")
    period = bodies.period_seconds(earth)
    expected = 365.25 * 86400.0
    assert abs(period - expected) < 1000.0, f"Earth period {period} != {expected}"


def test_moon_period_seconds_matches_lunar_month():
    """Moon's orbital period should be approximately one lunar month in seconds."""
    moon = bodies.moon("moon")
    period = bodies.period_seconds(moon)
    expected = 27.3 * 86400.0
    assert abs(period - expected) < 5000.0, f"Moon period {period} != {expected}"


def test_period_seconds_raises_for_zero_n():
    """Passing a body with n=0 should raise ZeroDivisionError."""
    sun = bodies.sun()
    try:
        bodies.period_seconds(sun)
        assert False, "Expected ZeroDivisionError for n=0"
    except ZeroDivisionError:
        pass
