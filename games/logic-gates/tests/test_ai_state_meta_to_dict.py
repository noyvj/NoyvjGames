"""Tests for state.meta_to_dict()."""

import state


def test_empty_meta_returns_empty_dict():
    """A fresh meta has only default values, so meta_to_dict should return {}."""
    assert state.meta_to_dict(state.new_meta()) == {}


def test_meta_to_dict_includes_non_default_values_and_omits_defaults():
    """When meta contains non-default data, it appears in the output; defaults are omitted."""
    meta = state.new_meta()
    meta["levels"]["straight-through"] = {"solved": True, "chips": 2, "par": True, "hints": 1, "answer": False}
    meta["stats"]["wires"] = 10
    meta["current"] = "invert"

    result = state.meta_to_dict(meta)

    assert "levels" in result
    assert result["levels"]["straight-through"] == {"solved": True, "chips": 2, "par": True, "hints": 1}
    assert "stats" in result
    assert result["stats"] == {"wires": 10}
    assert "current" in result
    assert result["current"] == "invert"

    # Defaults should be omitted
    assert "found" not in result
    assert "work" not in result
    assert "backup" not in result
    assert "tiers" not in result


def test_meta_to_dict_omits_empty_tiers_and_work():
    """Edge case: tiers and work/backup with empty or default records should not appear."""
    meta = state.new_meta()
    # Add a tier record that has no chips and par=False (default)
    meta["tiers"]["easy"]["straight-through"] = {"chips": None, "par": False}
    # Add work with empty circuit
    meta["work"]["straight-through"] = {"chips": [], "wires": {}}

    result = state.meta_to_dict(meta)

    assert "tiers" not in result
    assert "work" not in result
