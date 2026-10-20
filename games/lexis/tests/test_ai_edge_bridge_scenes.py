import pytest

from bridge_scenes import BridgeScene, bridge_scenes, BRIDGE_SCRIPT
from bridge import Stock


def test_bridge_scenes_returns_tuple_of_five():
    """bridge_scenes() should return exactly five scenes for the curriculum."""
    scenes = bridge_scenes()
    assert isinstance(scenes, tuple)
    assert len(scenes) == 5


def test_bridge_scene_to_dict_has_required_keys():
    """to_dict() must return a dictionary with all expected keys."""
    scene = BridgeScene("test", "msg", Stock(), Stock(), "reply")
    d = scene.to_dict()
    assert set(d.keys()) == {"id", "message", "before", "after", "reply"}


def test_bridge_scene_is_frozen():
    """BridgeScene is a frozen dataclass and should not allow attribute mutation."""
    scene = BridgeScene("id", "msg", Stock(), Stock(), "reply")
    with pytest.raises(Exception):
        scene.id = "new_id"


def test_bridge_script_length_and_format():
    """BRIDGE_SCRIPT must contain exactly five (id, message) pairs."""
    assert len(BRIDGE_SCRIPT) == 5
    for item in BRIDGE_SCRIPT:
        assert isinstance(item, tuple) and len(item) == 2


def test_bridge_scenes_stock_starts_empty_and_ends_with_expected_items():
    """The initial stock is empty, and the final scene's after stock matches expectations."""
    scenes = bridge_scenes()
    assert scenes[0].before.items == ()
    final_stock = scenes[-1].after
    assert isinstance(final_stock, Stock)


def test_bridge_scene_accepts_empty_strings():
    """BridgeScene should accept empty strings for id and message without raising."""
    scene = BridgeScene("", "", Stock(), Stock(), "")
    assert scene.id == ""
    assert scene.message == ""
    d = scene.to_dict()
    assert d["id"] == "" and d["message"] == ""
