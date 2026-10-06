import pytest

from compound import COMPONENTS, ROOTS, SIZES, GlyphError, Item, Tray, all_valid_glyphs, react, read_glyph
from compound_scenes import compound_scenes
from deduce_compound import (Reading, all_readings, consistent_readings, determinate, disagreements, predict)

SCENES = compound_scenes()


def test_every_valid_glyph_reads_as_a_root_and_a_size():
    assert len(all_valid_glyphs()) == len(ROOTS) * len(SIZES) == 6
    assert read_glyph("ku") == Item("water", "big")
    assert read_glyph("mo").label() == "small grain"


@pytest.mark.parametrize("glyph,reason", [
    ("", "silence"), ("zz", "unknown_part"), ("k", "shape"), ("kou", "shape"), ("ok", "order"), ("kk", "order"), ("uu", "order"),
])
def test_a_sign_the_language_cannot_say_gets_an_in_world_answer(glyph, reason):
    with pytest.raises(GlyphError) as err:
        read_glyph(glyph)
    assert err.value.reason == reason and err.value.text


def test_component_codes_give_nothing_away():
    # No letter spells its own meaning, so deduction is the only route.
    for letter, (meaning, _slot) in COMPONENTS.items():
        assert meaning[0] != letter


def test_the_world_adds_to_the_tray_and_caps_it():
    tray = Tray()
    for _ in range(9):
        tray = react("ku", tray).tray
    assert len(tray.items) == 6
    unreadable = react("ok", tray)
    assert not unreadable.understood and unreadable.tray == tray


def test_scenes_follow_each_other_and_come_from_the_real_world():
    for a, b in zip(SCENES, SCENES[1:]):
        assert b.before == a.after
    for s in SCENES:
        assert react(s.glyph, s.before).tray == s.after


def test_the_true_reading_is_consistent_with_every_scene():
    true = Reading("root_first", tuple((letter, meaning) for letter, (meaning, _s) in COMPONENTS.items()))
    assert true in set(all_readings()) and true in consistent_readings(SCENES)


def test_the_curriculum_settles_the_whole_language_though_two_glyphs_are_never_shown():
    shown = {s.glyph for s in SCENES}
    assert shown == {"ko", "mo", "mu", "to"}
    assert set(all_valid_glyphs()) - shown == {"ku", "tu"}
    assert determinate(SCENES), disagreements(SCENES)


def test_fewer_scenes_do_not_settle_it():
    assert not determinate(SCENES[:1])
    assert not determinate(SCENES[:2])
    assert not determinate(SCENES[:3])      # without scene 4 fire is not pinned down


def test_removing_the_contrast_scene_leaves_size_ambiguous():
    # Without "mu" the player never sees the size part change, so "u" cannot be told from other meanings.
    without = tuple(s for s in SCENES if s.glyph != "mu")
    assert not determinate(without)


def test_once_settled_more_scenes_never_unsettle():
    seen = False
    for k in range(1, len(SCENES) + 1):
        now = determinate(SCENES[:k])
        assert now or not seen
        seen = seen or now


def test_the_never_shown_glyphs_are_predicted_by_every_surviving_reading():
    readings = consistent_readings(SCENES)
    for glyph, expected in (("ku", "big water"), ("tu", "big fire")):
        results = {predict(r, glyph, Tray()).items[-1].label() for r in readings}
        assert results == {expected}, glyph


def test_a_contradicting_scene_leaves_no_reading():
    from compound_scenes import CompoundScene
    bad = CompoundScene("bad", "ko", Tray(), Tray((Item("fire", "big"),)))
    # One scene says ko is small water, another says it is big fire: nothing fits both.
    assert consistent_readings((SCENES[0], bad)) == []
