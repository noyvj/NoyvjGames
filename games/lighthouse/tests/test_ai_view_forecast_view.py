"""Tests for forecast_view() in view.py."""

import weather
import data
import sim
from state import Keep


def keep_at(night=1, seed=3):
    k = Keep(seed)
    k.night = night
    sim.to_evening(k)
    return k


def test_forecast_view_structure_and_labels():
    from view import forecast_view
    k = keep_at(7)
    v = forecast_view(k, 7)
    assert v["night"] == 7
    lo, hi = weather.forecast(k.seed, 7, False)
    assert v["lo"] == lo and v["hi"] == hi
    assert v["lo_label"] == data.SEVERITY_LABELS[lo]
    assert v["hi_label"] == data.SEVERITY_LABELS[hi]
    assert v["narrow"] == (lo == hi)
    assert v["vane"] is False


def test_forecast_view_narrow_flag_matches_lo_hi():
    from view import forecast_view
    for night in range(1, 41):
        k = keep_at(night)
        v = forecast_view(k, night)
        expected_narrow = (v["lo"] == v["hi"])
        assert v["narrow"] is expected_narrow, f"narrow mismatch at night {night}"


def test_forecast_view_vane_flag_passes_through():
    from view import forecast_view
    k = keep_at(1)
    k.upgrades = ["vane"]
    v = forecast_view(k, 1)
    assert v["vane"] is True
    k.upgrades = []
    v2 = forecast_view(k, 1)
    assert v2["vane"] is False
