"""Tests for dynasty.owned_effects()."""


import dynasty


def test_empty_owned_returns_empty_set():
    ui = {dynasty.KEY: {"earned": 0, "owned": []}}
    assert dynasty.owned_effects(ui) == set()


def test_single_perk_returns_its_effect():
    ui = {dynasty.KEY: {"earned": 10, "owned": ["heirloom_granary"]}}
    assert dynasty.owned_effects(ui) == {"start_food"}


def test_multiple_perks_returns_all_effects():
    ui = {dynasty.KEY: {"earned": 20, "owned": ["heirloom_granary", "steady_hands"]}}
    assert dynasty.owned_effects(ui) == {"start_food", "standing_food"}


def test_missing_dynasty_key_falls_back_to_empty():
    ui = {}
    assert dynasty.owned_effects(ui) == set()
