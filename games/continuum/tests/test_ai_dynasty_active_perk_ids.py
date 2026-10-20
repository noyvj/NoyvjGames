"""Tests for dynasty.active_perk_ids()."""


import dynasty


def test_active_perk_ids_returns_owned_when_on():
    ui = {dynasty.KEY: {"earned": 10, "owned": ["heirloom_granary", "steady_hands"]}}
    assert dynasty.active_perk_ids(ui) == ["heirloom_granary", "steady_hands"]


def test_active_perk_ids_returns_empty_when_off():
    ui = {dynasty.KEY: {"earned": 10, "owned": ["heirloom_granary"], "off": True}}
    assert dynasty.active_perk_ids(ui) == []


def test_active_perk_ids_returns_empty_when_resting():
    ui = {dynasty.KEY: {"earned": 10, "owned": ["heirloom_granary"]}}
    assert dynasty.active_perk_ids(ui, resting=True) == []
