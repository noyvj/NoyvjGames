"""Edge-case tests for missions_base.py."""

import missions_base as MB


def test_earth_scene_with_zero_r0():
    """earth_scene should accept r0=0 without crashing and return the expected structure."""
    scene = MB.earth_scene(r0=0)
    assert scene["central"] == "earth"
    assert scene["start"]["orbit"]["r"] == 0


def test_earth_scene_with_large_steps():
    """earth_scene should handle very large step counts correctly."""
    scene = MB.earth_scene(steps=100000)
    assert scene["steps"] == 100000
    assert scene["unit"] == "h"


def test_sun_scene_with_empty_children():
    """sun_scene should handle an empty children list and return a valid scene dict."""
    scene = MB.sun_scene((2026, 10, 1), [])
    assert scene["central"] == "sun"
    assert scene["children"] == []
    assert isinstance(scene["epoch"], tuple)


def test_sun_scene_epoch_as_list():
    """sun_scene should convert a list epoch to a tuple."""
    scene = MB.sun_scene([2026, 10, 1], ["earth"])
    assert scene["epoch"] == (2026, 10, 1)


def test_mars_scene_with_zero_r0():
    """mars_scene should accept r0=0 and preserve it in the start orbit."""
    scene = MB.mars_scene(r0=0, phobos_phase=0.0, deimos_phase=0.0, steps=100)
    assert scene["central"] == "mars"
    assert scene["start"]["orbit"]["r"] == 0


def test_mission_with_empty_strings():
    """mission should correctly store empty strings for all text fields."""
    m = MB.mission("c1m1", 1, 1, "", "", "", "", "", {}, {})
    assert m["id"] == "c1m1"
    assert m["name"] == ""
    assert m["dest"] == ""
    assert m["brief"] == ""
    assert m["goal_text"] == ""
    assert m["note"] == ""


def test_mission_extra_kwargs_applied():
    """mission should allow extra kwargs to override default keys."""
    m = MB.mission("c1m1", 1, 1, "Test", "Dest", "Brief", "Goal", "Note", {}, {}, budget=50)
    assert m["budget"] == 50
    assert m["id"] == "c1m1"
