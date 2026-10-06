from pulse import PULSE, say_door, say_lamps
from scenes import PULSE_SCRIPT, pulse_scenes
from world import Station, describe, react


def test_lamps_set_to_the_number_and_leave_the_door_alone():
    r = react(say_lamps(4), Station(0, "open"), PULSE)
    assert r.understood and r.station == Station(4, "open")
    assert "4 lamps are lit" in r.text and "door is open" in r.text


def test_the_door_changes_and_leaves_the_lamps_alone():
    r = react(say_door("open"), Station(3, "shut"), PULSE)
    assert r.station == Station(3, "open")


def test_zero_and_one_read_naturally():
    assert "no lamps are lit" in describe(Station(0, "shut"))
    assert "1 lamp is lit" in describe(Station(1, "shut"))


def test_a_signal_that_cannot_be_read_changes_nothing_and_says_why():
    start = Station(2, "open")
    r = react("1000" + "1010" + "1111", start, PULSE)
    assert not r.understood and r.station == start and r.reason == "lamp_needs_number"
    assert r.text


def test_world_is_deterministic():
    a = react(say_lamps(6), Station(1, "shut"), PULSE)
    b = react(say_lamps(6), Station(1, "shut"), PULSE)
    assert a == b


def test_scenes_follow_each_other_and_come_from_the_real_world():
    scenes = pulse_scenes()
    assert [s.id for s in scenes] == [sid for sid, _ in PULSE_SCRIPT]
    for previous, current in zip(scenes, scenes[1:]):
        assert current.before == previous.after
    for scene in scenes:
        assert react(scene.marks, scene.before, PULSE).station == scene.after


def test_scene_dicts_are_plain_data():
    data = pulse_scenes()[0].to_dict()
    assert set(data) == {"id", "marks", "before", "after"}
    assert data["after"] == {"lamps": 1, "door": "shut"}
