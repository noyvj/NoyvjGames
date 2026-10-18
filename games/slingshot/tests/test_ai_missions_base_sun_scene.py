"""Tests for sun_scene() in missions_base.py."""

from pathlib import Path

import missions_base

GAME_DIR = Path(__file__).resolve().parent.parent


def test_sun_scene_returns_correct_structure_and_defaults():
    """Normal case with default steps and view_au."""
    epoch = (2026, 11, 18)
    children = ["earth", "venus"]
    scene = missions_base.sun_scene(epoch, children)

    assert scene["central"] == "sun"
    assert scene["children"] == list(children)
    assert scene["dt"] == 21600.0
    assert scene["steps"] == 2400
    assert scene["stride"] == 8
    assert scene["unit"] == "d"
    assert abs(scene["view"] - 1.75 * 149597870.7) < 1e-3
    assert scene["start"] == {"comove": "earth"}
    assert scene["epoch"] == tuple(epoch)


def test_sun_scene_applies_custom_steps_and_view():
    """Normal case with custom steps and view_au."""
    epoch = (2026, 11, 18)
    children = ["mars"]
    custom_steps = 3000
    custom_view_au = 2.5
    scene = missions_base.sun_scene(epoch, children, steps=custom_steps, view_au=custom_view_au)

    assert scene["steps"] == custom_steps
    assert abs(scene["view"] - custom_view_au * 149597870.7) < 1e-3


def test_sun_scene_handles_single_child_and_tuple_epoch():
    """Edge case: single child and tuple epoch (should behave identically to list)."""
    epoch = (2026, 11, 18)
    children = ["venus"]
    scene = missions_base.sun_scene(epoch, children)

    assert len(scene["children"]) == 1
    assert scene["children"][0] == "venus"
    assert isinstance(scene["epoch"], tuple)
