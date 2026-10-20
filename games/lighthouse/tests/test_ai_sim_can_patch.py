"""Tests for sim.can_patch(). Verifies that can_patch correctly checks supplies against NIGHT_PATCH costs."""

import sim


def _mock_keep(supplies):
    """Return a minimal object with a .supplies attribute matching what can_patch expects."""
    class MockKeep:
        pass
    MockKeep.supplies = supplies
    return MockKeep()


def test_can_patch_returns_true_when_supplies_are_sufficient():
    costs = sim.NIGHT_PATCH["tower"]
    keep = _mock_keep({k: v * 2 for k, v in costs.items()})
    assert sim.can_patch(keep, "tower") is True


def test_can_patch_returns_false_when_supplies_are_insufficient():
    costs = sim.NIGHT_PATCH["tower"]
    keep = _mock_keep({k: max(0, v - 1) for k, v in costs.items()})
    assert sim.can_patch(keep, "tower") is False


def test_can_patch_returns_true_when_supplies_exactly_match_costs():
    costs = sim.NIGHT_PATCH["tower"]
    keep = _mock_keep(costs.copy())
    assert sim.can_patch(keep, "tower") is True
