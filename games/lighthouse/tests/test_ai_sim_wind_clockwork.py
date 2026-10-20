"""Tests for wind_clockwork() in sim.py."""

import json
from data import CLOCK_BASE, ENERGY_WIND, TIRED
import game
import sim
from state import Keep


def req(**kw):
    return json.loads(game.handle(json.dumps(kw)))


def test_normal_wind_restores_full_clock_and_deducts_energy():
    k = Keep(1)
    sim.to_evening(k)
    k.log = []
    k.energy = 50.0
    initial_energy = k.energy
    initial_wound = k.night_stats.get("wound", 0)

    sim.wind_clockwork(k, auto=False)

    assert k.clock_left == float(CLOCK_BASE)
    assert k.energy == initial_energy - ENERGY_WIND
    assert k.night_stats.get("wound", 0) == initial_wound + 1
    assert len(k.log) == 1
    assert "You wind the clockwork." in str(k.log[-1])


def test_tired_wind_reduces_clock_to_seventy_percent():
    k = Keep(1)
    sim.to_evening(k)
    k.log = []
    k.energy = TIRED - 1
    initial_energy = k.energy
    initial_wound = k.night_stats.get("wound", 0)

    sim.wind_clockwork(k, auto=False)

    assert k.clock_left == float(CLOCK_BASE) * 0.7
    assert k.energy == initial_energy - ENERGY_WIND
    assert k.night_stats.get("wound", 0) == initial_wound + 1


def test_stopped_wind_logs_beam_sweeps_message():
    k = Keep(1)
    sim.to_evening(k)
    k.log = []
    k.energy = 50.0
    k.night_stats["stopped"] = True
    initial_log_len = len(k.log)

    sim.wind_clockwork(k, auto=False)

    assert len(k.log) == initial_log_len + 1
    assert "You wind the clockwork and the beam sweeps again." in str(k.log[-1])
