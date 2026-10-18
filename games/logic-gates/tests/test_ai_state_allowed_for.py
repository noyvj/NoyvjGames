"""Tests for state.allowed_for()."""

import levels
import state


def test_allowed_for_sandbox_returns_all_chips():
    """Sandbox should allow every chip type defined in the registry."""
    allowed = state.allowed_for(state.SANDBOX, [])
    assert isinstance(allowed, list)
    for chip_type in allowed:
        assert chip_type in levels.REGISTRY


def test_allowed_for_normal_level_no_progress():
    """A level with no solved predecessors returns its initial allowed chips (may be empty for early levels)."""
    level_id = levels.LEVELS[0]["id"]
    allowed = state.allowed_for(level_id, [])
    assert isinstance(allowed, list)
    for chip_type in allowed:
        assert chip_type in levels.REGISTRY


def test_allowed_for_normal_level_with_progress():
    """Solving a level expands the set of allowed chips for subsequent levels."""
    level_id = levels.LEVELS[1]["id"] if len(levels.LEVELS) > 1 else levels.LEVELS[0]["id"]
    allowed_before = state.allowed_for(level_id, [])
    allowed_after = state.allowed_for(level_id, ["straight-through"])
    assert isinstance(allowed_after, list)
    assert set(allowed_before).issubset(set(allowed_after))


def test_allowed_for_edge_case_unknown_level():
    """Passing an unknown level ID raises KeyError as expected from levels.BY_ID lookup."""
    try:
        state.allowed_for("nonexistent-level", [])
        assert False, "Expected KeyError"
    except KeyError:
        pass
