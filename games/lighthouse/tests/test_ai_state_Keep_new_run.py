"""Tests for Keep.new_run() in state.py."""

from state import Keep, new_night_stats, new_story, MAX_SEED
from data import START_OIL, START_SUPPLIES, START_STRUCTURE, START_ENERGY, DEFAULT_ORDER


def test_new_run_resets_to_defaults_with_valid_seed():
    keep = Keep(1)
    keep.new_run(42)
    assert keep.seed == 42
    assert keep.night == 1
    assert keep.phase == "evening"
    assert keep.tick == 0
    assert keep.mode == "year"
    assert keep.quiet is False
    assert keep.oil == float(START_OIL)
    assert keep.supplies == dict(START_SUPPLIES)
    assert keep.structure == dict(START_STRUCTURE)
    assert keep.energy == float(START_ENERGY)
    assert keep.reputation == 0
    assert keep.comfort == 0
    assert keep.salvage == 0
    assert keep.levels == [1, 1, 1]
    assert keep.tasks == {"wind": True, "watch": False, "repair": False}
    assert keep.ration == 0
    assert keep.focus == "worst"
    assert keep.clock_left == 0.0
    assert keep.override is None
    assert keep.incident is None
    assert keep.progress == {}
    assert keep.mail_tonight is False
    assert keep.boat_due is False
    assert keep.order == dict(DEFAULT_ORDER)
    assert keep.upgrades == []
    assert keep.waiting == []
    assert keep.day_slots == 0
    assert keep.hungry is False
    assert keep.repaired_today == []
    assert keep.combed is False
    assert keep.night_stats == new_night_stats()
    assert keep.season_min_oil == float(START_OIL)
    assert keep.log == []
    assert keep.report is None
    assert keep.delivery is None
    assert keep.story == new_story()


def test_new_run_clamps_seed_to_range():
    keep = Keep(1)
    keep.new_run(-100)
    assert keep.seed == 0

    keep.new_run(MAX_SEED + 1)
    assert keep.seed == MAX_SEED


def test_new_run_falls_back_to_default_seed_for_invalid_input():
    keep = Keep(1)
    keep.new_run("bad")
    assert keep.seed == 1

    keep.new_run(None)
    assert keep.seed == 1
