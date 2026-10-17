"""Tests for state.level_view()."""

import state
import levels


def test_level_view_returns_sandbox_dict():
    expected = {
        "id": "sandbox",
        "name": "Sandbox",
        "ins": ["A", "B", "C"],
        "outs": ["X", "Y"],
        "cap": 40,
        "loops": True,
        "kind": "free"
    }
    assert state.level_view("sandbox") == expected


def test_level_view_returns_real_level_from_registry():
    lid = levels.LEVELS[0]["id"]
    result = state.level_view(lid)
    assert result is not None
    assert result["id"] == lid
    assert "name" in result
    assert "ins" in result
    assert "outs" in result


def test_level_view_returns_none_for_unknown_id():
    assert state.level_view("does_not_exist") is None
