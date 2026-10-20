"""Tests for sky_for() in view.py."""

from state import Keep
import sim
from view import sky_for


def keep_at(night=1, seed=3):
    k = Keep(seed)
    k.night = night
    sim.to_evening(k)
    return k


def test_sky_for_returns_night_when_phase_is_night():
    k = keep_at(5)
    k.phase = "night"
    assert sky_for(k) == "night"


def test_sky_for_returns_dusk_when_phase_is_evening():
    k = keep_at(5)
    assert sky_for(k) == "dusk"


def test_sky_for_returns_day_as_default():
    k = keep_at(5)
    k.phase = "day"
    assert sky_for(k) == "day"
