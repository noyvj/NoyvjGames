import pytest
from dataclasses import FrozenInstanceError

from compound import Tray
from compound_scenes import COMPOUND_SCRIPT, compound_scenes


def test_compound_scenes_returns_four_scenes():
    """compound_scenes() should produce exactly four scenes for the curriculum."""
    scenes = compound_scenes()
    assert len(scenes) == 4


def test_compound_scenes_order_matches_script():
    """The generated scenes must follow the order defined in COMPOUND_SCRIPT."""
    scenes = compound_scenes()
    for (expected_id, expected_glyph), scene in zip(COMPOUND_SCRIPT, scenes):
        assert scene.id == expected_id
        assert scene.glyph == expected_glyph


def test_compound_scene_to_dict_contains_expected_keys():
    """to_dict() on a CompoundScene must return a dictionary with the correct keys."""
    scenes = compound_scenes()
    for scene in scenes:
        d = scene.to_dict()
        assert set(d.keys()) == {"id", "glyph", "before", "after"}


def test_compound_scene_is_frozen_dataclass():
    """CompoundScene should be immutable; attempting to modify fields must raise."""
    scenes = compound_scenes()
    scene = scenes[0]
    with pytest.raises(FrozenInstanceError):
        scene.id = "modified"


def test_compound_script_contains_valid_glyph_strings():
    """COMPOUND_SCRIPT should only contain tuples of two non-empty strings."""
    for item in COMPOUND_SCRIPT:
        assert isinstance(item, tuple) and len(item) == 2
        assert all(isinstance(part, str) and part for part in item)


def test_compound_scenes_tray_states_are_valid():
    """Each scene's before and after trays must be valid Tray instances with tuple items."""
    scenes = compound_scenes()
    for scene in scenes:
        assert isinstance(scene.before, Tray)
        assert isinstance(scene.after, Tray)
        assert isinstance(scene.before.items, tuple)
        assert isinstance(scene.after.items, tuple)
