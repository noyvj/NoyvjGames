"""Tests for mars_scene() in missions_base.py."""

import missions_base


def test_mars_scene_default_view():
    """When view is omitted, it should default to 30000.0."""
    scene = missions_base.mars_scene(r0=35000.0, phobos_phase=10.0, deimos_phase=20.0, steps=1000)
    assert scene["view"] == 30000.0


def test_mars_scene_custom_values():
    """Custom parameters should be correctly placed in the returned dictionary."""
    scene = missions_base.mars_scene(r0=40000.0, phobos_phase=45.0, deimos_phase=90.0, steps=2000, view=50000.0)
    assert scene["start"]["orbit"]["r"] == 40000.0
    assert scene["phases"]["phobos"] == 45.0
    assert scene["phases"]["deimos"] == 90.0
    assert scene["steps"] == 2000
    assert scene["view"] == 50000.0


def test_mars_scene_fixed_keys():
    """Fixed keys should always have their expected values."""
    scene = missions_base.mars_scene(r0=30000.0, phobos_phase=0.0, deimos_phase=0.0, steps=500)
    assert scene["central"] == "mars"
    assert scene["children"] == ["phobos", "deimos"]
    assert scene["dt"] == 60.0
    assert scene["stride"] == 4
    assert scene["unit"] == "min"
    assert scene["rendezvous"] == ["phobos", "deimos"]


def test_mars_scene_edge_case_zero_steps():
    """Passing zero steps should still produce a valid structure without errors."""
    scene = missions_base.mars_scene(r0=35000.0, phobos_phase=10.0, deimos_phase=20.0, steps=0)
    assert scene["steps"] == 0
    assert isinstance(scene, dict)
