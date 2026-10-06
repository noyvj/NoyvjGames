"""The fairness guarantee: the scenes shown must settle how the language works."""

import pytest

from deduce import (Hypothesis, all_hypotheses, consistent_hypotheses, determinate, disagreements, evaluate)
from lang import NUMBER_RULES
from pulse import PULSE, say_door, say_lamps
from scenes import pulse_scenes
from world import Station, react

SCENES = pulse_scenes()


def _true_hypothesis():
    meanings = (("1000", "LAMPS"), ("1001", "DOOR"), ("1010", "OPEN"), ("1011", "SHUT"), ("1111", "IGNORE"))
    return Hypothesis("binary_msb", meanings)


def test_the_true_reading_is_among_the_hypotheses_and_agrees_with_the_real_world():
    assert _true_hypothesis() in set(all_hypotheses(PULSE))
    for n in range(8):
        for start in (Station(0, "shut"), Station(5, "open")):
            assert evaluate(_true_hypothesis(), say_lamps(n), start, PULSE) == react(say_lamps(n), start, PULSE).station
    for state in ("open", "shut"):
        assert evaluate(_true_hypothesis(), say_door(state), Station(2, "shut"), PULSE) == Station(2, state)


def test_the_true_reading_is_consistent_with_every_scene():
    assert _true_hypothesis() in consistent_hypotheses(SCENES)


def test_one_scene_does_not_settle_the_language():
    assert not determinate(SCENES[:1])
    assert disagreements(SCENES[:1])


def test_the_whole_curriculum_settles_the_language_completely():
    assert determinate(SCENES), disagreements(SCENES)[:3]


def test_once_settled_more_scenes_never_unsettle_it():
    seen = False
    for k in range(1, len(SCENES) + 1):
        now = determinate(SCENES[:k])
        assert now or not seen, f"prefix {k} lost determinacy"
        seen = seen or now


def test_every_wrong_number_rule_is_ruled_out_before_the_player_must_rely_on_numbers():
    for k in range(1, len(SCENES) + 1):
        rules = {h.rule for h in consistent_hypotheses(SCENES[:k])}
        if "binary_msb" in rules and len(rules) == 1:
            first_unique = k
            break
    else:
        pytest.fail("the scenes never single out the binary rule")
    assert first_unique <= 3          # settled by the third scene, before the unseen number five is asked of the player


def test_an_unseen_number_is_predictable_from_the_scenes_alone():
    # After the first three scenes the readings that still fit all agree on a number never shown: seven.
    hyps = consistent_hypotheses(SCENES[:3])
    predictions = {evaluate(h, say_lamps(7), Station(0, "shut"), PULSE).lamps for h in hyps}
    assert predictions == {7}


def test_a_contradicting_scene_leaves_no_reading_at_all():
    from scenes import Scene
    bad = Scene("bad", say_lamps(3), Station(0, "shut"), Station(1, "shut"))   # 0011 cannot light one lamp under any rule here
    assert consistent_hypotheses(SCENES[:2] + (bad,)) == []
    assert not determinate(SCENES[:2] + (bad,))


def test_number_rules_listed_match_the_hypothesis_space():
    assert {h.rule for h in all_hypotheses(PULSE)} == set(NUMBER_RULES)
