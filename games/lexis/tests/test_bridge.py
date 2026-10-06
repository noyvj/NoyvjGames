import pytest

from bridge import Stock, react
from bridge_scenes import bridge_scenes
from deduce_bridge import Reading, all_readings, consistent_readings, determinate, disagreements, evaluate

SCENES = bridge_scenes()


def test_nouns_numbers_and_markers_work_as_designed():
    s = react("ku", Stock()).stock
    assert s.count("big water") == 1
    s = react("ku p 0011", s).stock
    assert s.count("big water") == 4
    assert react("ku n", s).stock.count("big water") == 0
    asked = react("ku q", s)
    assert asked.stock == s and asked.reply == "The station shows 4 big water."


def test_counts_are_capped_and_empty_things_vanish():
    s = react("ku p 0111", Stock()).stock
    s = react("ku p 0111", s).stock
    assert s.count("big water") == 7
    assert react("ku n", s).stock.items == ()


@pytest.mark.parametrize("message,reason", [
    ("", "silence"), ("zz", "no_thing"), ("ku x", "unknown_marker"), ("ku p", "plural_needs_count"),
    ("ku p mo", "plural_needs_count"), ("ku n 0011", "extra"), ("ku q ku", "extra"),
])
def test_what_the_language_cannot_say_gets_an_in_world_answer(message, reason):
    r = react(message, Stock())
    assert not r.understood and r.reason == reason and r.text and r.stock == Stock()


def test_scenes_come_from_the_real_world_and_follow_each_other():
    for a, b in zip(SCENES, SCENES[1:]):
        assert b.before == a.after
    assert SCENES[-1].reply == "The station shows 2 small grain."


def test_the_true_reading_is_consistent_with_every_scene():
    true = Reading("noun_first", (("p", "plural"), ("n", "negate"), ("q", "ask")))
    assert true in set(all_readings()) and true in consistent_readings(SCENES)


def test_the_curriculum_settles_the_language_and_fewer_scenes_do_not():
    assert determinate(SCENES), disagreements(SCENES)
    for k in range(1, len(SCENES)):
        assert not determinate(SCENES[:k]), k


def test_marker_first_readings_are_ruled_out_by_the_scenes():
    assert {r.order for r in consistent_readings(SCENES)} == {"noun_first"}


def test_each_new_sign_is_needed():
    # Dropping every scene that shows a marker leaves that marker undetermined (plural is shown twice on
    # purpose: once with each noun, so it is the sign and not the noun that carries the meaning).
    for marker_scenes in ({"ku-p-3", "mo-p-2"}, {"ku-n"}, {"mo-q"}):
        kept = tuple(s for s in SCENES if s.id not in marker_scenes)
        assert not determinate(kept), marker_scenes
    assert determinate(tuple(s for s in SCENES if s.id != "ku-p-3"))     # the second plural scene is enough


def test_a_marker_never_shown_with_a_given_noun_is_still_predicted():
    # "mo n" and "ku q" are never shown, yet every surviving reading agrees on them.
    start = Stock((("big water", 2), ("small grain", 1)))
    readings = consistent_readings(SCENES)
    for message in ("mo n", "ku q", "tu p 0101"):
        assert len({evaluate(r, message, start) for r in readings}) == 1, message


def test_once_settled_more_scenes_never_unsettle():
    seen = False
    for k in range(1, len(SCENES) + 1):
        now = determinate(SCENES[:k])
        assert now or not seen
        seen = seen or now
