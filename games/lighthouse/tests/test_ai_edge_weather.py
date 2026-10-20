"""Edge-case tests for weather.py."""

import clock
import weather


def test_severity_first_and_festival_nights_are_calm():
    """First and festival nights always return severity 0."""
    assert weather.severity(1, 1) == 0
    assert weather.severity(42, 1) == 0
    assert weather.severity(1, 20) == 0
    assert weather.severity(99, 20) == 0


def test_severity_returns_valid_range():
    """Severity never falls outside the allowed 0..3 range."""
    for seed in (1, 12345, 99999):
        for night in range(1, 41):
            sev = weather.severity(seed, night)
            assert 0 <= sev <= 3


def test_weather_handles_smallest_and_largest_nights():
    """Weather returns correct lengths and clamped values for boundary nights."""
    for night in (1, 40):
        nw = weather.weather(1, night)
        assert len(nw.cond) == clock.night_len(night)
        assert len(nw.wind) == clock.night_len(night)
        assert all(0 <= c <= 4 for c in nw.cond)
        assert all(0 <= w <= 4 for w in nw.wind)


def test_weather_worst_returns_max_cond():
    """worst() returns the maximum condition value across the night."""
    nw = weather.weather(1, 31)
    assert nw.worst() == max(nw.cond)


def test_forecast_bands_are_valid_and_clamped():
    """Forecast bands are ordered and clamped to the valid 0..3 severity range."""
    for seed in (1, 12345, 99999):
        for night in range(1, 41):
            lo, hi = weather.forecast(seed, night)
            assert lo <= hi
            assert 0 <= lo and hi <= 3


def test_forecast_vane_night_can_be_exact():
    """Vane forecasts can return an exact band when the meter is sure."""
    exact_count = 0
    for night in range(1, 41):
        lo, hi = weather.forecast(1, night, vane=True)
        if lo == hi:
            exact_count += 1
    assert exact_count > 0
