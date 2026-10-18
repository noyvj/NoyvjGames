"""Tests for earth_scene() in missions_base.py."""

import missions_base


def test_earth_scene_defaults():
    """Default parameters produce the expected structure and values."""
    scene = missions_base.earth_scene()
    assert scene["central"] == "earth"
    assert scene["children"] == ["moon"]
    assert scene["dt"] == 360.0
    assert scene["steps"] == 3600
    assert scene["stride"] == 6
    assert scene["unit"] == "h"
    assert scene["view"] == 470000.0
    assert scene["start"]["orbit"]["r"] == 42164.0
    assert scene["phases"]["moon"] == 40.0


def test_earth_scene_custom_parameters():
    """Custom parameters override the defaults correctly."""
    scene = missions_base.earth_scene(r0=50000.0, moon_phase=90.0, steps=1800, stride=3)
    assert scene["start"]["orbit"]["r"] == 50000.0
    assert scene["phases"]["moon"] == 90.0
    assert scene["steps"] == 1800
    assert scene["stride"] == 3


def test_earth_scene_edge_case_zero_radius():
    """Starting at the center (r0=0) is handled without error."""
    scene = missions_base.earth_scene(r0=0.0)
    assert scene["start"]["orbit"]["r"] == 0.0
    assert scene["central"] == "earth"
