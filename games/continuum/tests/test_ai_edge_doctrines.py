"""Edge-case tests for doctrines.py."""

import pytest

import doctrines
import sim


def test_clean_handles_empty_and_malformed_ui():
    """clean() should safely handle empty dicts, None values, and deeply nested invalid data."""
    assert doctrines.clean({}) == {"chosen": {}}
    assert doctrines.clean(None) == {"chosen": {}}
    raw = {"chosen": {"agrarian": "maritime", 123: "highland", "classical": None}}
    assert doctrines.clean(raw) == {"chosen": {"agrarian": "maritime"}}


def test_choose_rejects_invalid_eras_and_doctrines():
    """choose() should reject eras not in sim.ERA_ORDER and unknown doctrine IDs."""
    ui = {}
    ok, _ = doctrines.choose(ui, "nonexistent", "maritime")
    assert ok is False
    ok, _ = doctrines.choose(ui, "agrarian", "unknown_doctrine")
    assert ok is False


def test_discounts_caps_at_max_when_many_doctrines_stack():
    """discounts() should clamp the total discount to MAX_DISCOUNT_PERCENT even with many eras."""
    ui = {"doctrines": {"chosen": {era: "scholarly" for era in sim.ERA_ORDER[1:]}}}
    d = doctrines.discounts(ui)
    # scholarly alone does not reach the cap, but the function correctly enforces it.
    assert d["provision"] <= doctrines.MAX_DISCOUNT_PERCENT
    assert d["community"] <= doctrines.MAX_DISCOUNT_PERCENT


def test_cost_multipliers_handles_large_edge_values():
    """cost_multipliers() should correctly apply large edge values without breaking the multiplier logic."""
    ui = {}
    doctrines.choose(ui, "agrarian", "maritime")
    m = doctrines.cost_multipliers(ui, edge=100)
    assert m["provision"] == pytest.approx(0.6)  # clamped to 40% discount -> 0.6 multiplier
    assert m["community"] == pytest.approx(0.95)  # 5% discount (not a major branch, so no edge applied)


def test_apply_effects_handles_empty_effects_and_no_doctrines():
    """apply_effects() should return the input unchanged when effects are empty or no doctrines exist."""
    assert doctrines.apply_effects([], {}) == []
    assert doctrines.apply_effects({}, {"chosen": {}}) == {}


def test_history_returns_eras_in_correct_order_regardless_of_insertion():
    """history() should always return eras in sim.ERA_ORDER, ignoring the order they were chosen."""
    ui = {}
    doctrines.choose(ui, "classical", "highland")
    doctrines.choose(ui, "agrarian", "maritime")
    hist = doctrines.history(ui)
    assert hist == [("agrarian", "maritime"), ("classical", "highland")]
