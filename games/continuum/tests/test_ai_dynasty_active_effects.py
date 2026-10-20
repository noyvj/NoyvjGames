"""Tests for dynasty.active_effects()."""


import dynasty


def test_active_effects_returns_owned_perk_effects_when_on():
    ui = {dynasty.KEY: {"earned": 10, "owned": ["heirloom_granary", "steady_hands"], "off": False}}
    effects = dynasty.active_effects(ui)
    assert effects == {"start_food", "standing_food"}


def test_active_effects_returns_empty_set_when_resting():
    ui = {dynasty.KEY: {"earned": 10, "owned": ["heirloom_granary"], "off": False}}
    assert dynasty.active_effects(ui, resting=True) == set()


def test_active_effects_handles_missing_or_invalid_ui_record():
    ui = {}
    assert dynasty.active_effects(ui) == set()
    ui = {"dynasty": "not a dict"}
    assert dynasty.active_effects(ui) == set()
