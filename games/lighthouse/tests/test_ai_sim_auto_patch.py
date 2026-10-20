"""Tests for sim.auto_patch()."""

import sim
from state import Keep
from data import NIGHT_PATCH, PARTS, AUTO_PATCH_HEAL


def make_keep(**overrides):
    k = Keep(1)
    # Ensure supplies are sufficient for any patch we might test
    for part in PARTS:
        for supply, amount in NIGHT_PATCH[part].items():
            if supply not in k.supplies or k.supplies[supply] < amount:
                k.supplies[supply] = max(k.supplies.get(supply, 0), amount + 10)
    for key, val in overrides.items():
        setattr(k, key, val)
    return k


def test_auto_patches_the_lowest_structure_part_when_focus_is_not_set():
    """When focus is not set or invalid, auto_patch picks the part with the lowest structure value."""
    k = make_keep(structure={"tower": 50, "lantern": 40, "rail": 60, "dock": 70, "cistern": 80}, focus=None)
    result = sim.auto_patch(k)
    assert result is True
    # Should have patched lantern (lowest at 40)
    assert k.structure["lantern"] == 40 + AUTO_PATCH_HEAL
    assert k.energy < 100  # energy decreased by 3


def test_auto_patches_the_focus_part_when_it_is_valid():
    """When focus is set to a valid part, auto_patch attempts that part first."""
    k = make_keep(structure={"tower": 50, "lantern": 90, "rail": 90, "dock": 90, "cistern": 90}, focus="lantern")
    result = sim.auto_patch(k)
    assert result is True
    assert k.structure["lantern"] == 90 + AUTO_PATCH_HEAL


def test_auto_patch_returns_false_when_all_parts_are_at_max():
    """If all parts are at 100, auto_patch does nothing and returns False."""
    k = make_keep(structure={p: 100 for p in PARTS})
    result = sim.auto_patch(k)
    assert result is False
