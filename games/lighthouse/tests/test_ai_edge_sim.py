"""Edge-case tests for sim.py functions."""

import json

import game
import sim
from state import Keep


def req(**kw):
    return json.loads(game.handle(json.dumps(kw)))


def test_lamp_level_returns_minus_one_when_oil_is_zero():
    """lamp_level should return -1 (dark) when oil is exactly zero."""
    k = Keep(1)
    sim.to_evening(k)
    sim.begin_night(k)
    k.oil = 0.0
    assert sim.lamp_level(k, 0) == -1


def test_lamp_level_returns_zero_when_ration_is_spent():
    """lamp_level should drop to Dim (0) once the nightly ration is exhausted."""
    k = Keep(1)
    sim.to_evening(k)
    sim.begin_night(k)
    k.ration = 1
    k.night_stats["oil_used"] = 1
    assert sim.lamp_level(k, 0) == 0


def test_effective_reach_clamps_to_zero_for_negative_level():
    """effective_reach must return 0 when the lamp is out (level < 0)."""
    k = Keep(1)
    sim.to_evening(k)
    sim.begin_night(k)
    assert sim.effective_reach(k, -1, 0) == 0


def test_effective_reach_clamps_to_zero_for_high_weather_penalty():
    """effective_reach should clamp to 0 when weather penalty exceeds base reach."""
    k = Keep(1)
    sim.to_evening(k)
    sim.begin_night(k)
    assert sim.effective_reach(k, 0, 4) == 0


def test_set_level_rejects_invalid_levels():
    """set_level should return False for levels outside the allowed range."""
    k = Keep(1)
    sim.to_evening(k)
    sim.begin_night(k)
    for level in (-1, 4, 5):
        assert not sim.set_level(k, level)


def test_set_level_clears_override_when_same_as_plan():
    """set_level should clear the override if the requested level matches the plan."""
    k = Keep(1)
    sim.to_evening(k)
    sim.begin_night(k)
    sim.set_level(k, 3)
    assert k.override is not None
    k.levels[0] = 3  # Match the plan so set_level clears it
    sim.set_level(k, 3)
    assert k.override is None


def test_burn_rate_applies_wick_bonus():
    """burn_rate should multiply the base rate by 0.8 when the wick upgrade is present."""
    k = Keep(1)
    sim.to_evening(k)
    sim.begin_night(k)
    rate_no_wick = sim.burn_rate(k, 2)
    if hasattr(k, "upgrades"):
        k.upgrades.append("wick")
    else:
        k.upgrades = ["wick"]
    rate_with_wick = sim.burn_rate(k, 2)
    assert rate_with_wick == rate_no_wick * 0.8


def test_wind_now_rejects_when_clock_is_full():
    """wind_now should return False when the clockwork is already at maximum capacity."""
    k = Keep(1)
    sim.to_evening(k)
    sim.begin_night(k)
    k.clock_left = float(sim.max_wind(k))
    assert not sim.wind_now(k)


def test_wind_now_rejects_outside_night_phase():
    """wind_now should return False if called during evening or day phases."""
    k = Keep(1)
    sim.to_evening(k)
    assert not sim.wind_now(k)
