from dataclasses import FrozenInstanceError

from scenes import pulse_scenes


def test_pulse_scenes_returns_a_tuple():
    """pulse_scenes should return a tuple of Scene objects."""
    result = pulse_scenes()
    assert isinstance(result, tuple)


def test_scene_to_dict_contains_required_keys_and_types():
    """Scene.to_dict must return a dict with id (str), marks (str), before (dict), after (dict)."""
    scene = pulse_scenes()[0]
    d = scene.to_dict()
    assert set(d.keys()) == {"id", "marks", "before", "after"}
    assert isinstance(d["id"], str)
    assert isinstance(d["marks"], str)
    assert isinstance(d["before"], dict)
    assert isinstance(d["after"], dict)


def test_scene_attributes_are_frozen():
    """Scene is a frozen dataclass; its attributes must not be mutable."""
    scene = pulse_scenes()[0]
    try:
        scene.id = "new-id"
        assert False, "Expected FrozenInstanceError"
    except FrozenInstanceError:
        pass


def test_pulse_scenes_marks_are_non_empty_strings():
    """Each scene's marks must be a non-empty string representing the signal."""
    scenes = pulse_scenes()
    for scene in scenes:
        assert isinstance(scene.marks, str)
        assert len(scene.marks) > 0


def test_pulse_scenes_stations_have_valid_lamp_counts():
    """Lamp counts in before/after stations must be integers between 0 and 7."""
    scenes = pulse_scenes()
    for scene in scenes:
        for station in (scene.before, scene.after):
            lamps = station.lamps
            assert isinstance(lamps, int)
            assert 0 <= lamps <= 7
