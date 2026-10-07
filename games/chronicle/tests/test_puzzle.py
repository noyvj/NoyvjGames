"""The timeline builder's puzzles: reproducible, graded deterministically, fair at every difficulty."""

import json
from pathlib import Path

import pytest

import puzzle as pz
from setdata import event_key, year_of

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "puzzles_v1.json"


def all_codes(sample):
    out = {}
    for sid in sample.section_ids:
        for r in range(2 * len(sample.section_pool(sid))):
            p = pz.make_puzzle(sample, sid, r)
            out[p.code] = {"tray": p.tray, "answer": p.answer}
    return out


def test_puzzles_are_pinned_by_a_fixture(sample):
    """Any change to the generator changes a past puzzle. Bump SEED_VERSION and rerun
    `python3 tests/make_fixture.py` if that is intended."""
    pinned = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert pinned["seed_version"] == pz.SEED_VERSION
    assert pinned["puzzles"] == all_codes(sample)


def test_the_same_inputs_give_the_same_puzzle(sample):
    a, b = pz.make_puzzle(sample, "s2", 3), pz.make_puzzle(sample, "s2", 3)
    assert a.to_dict() == b.to_dict()


def test_the_generator_does_not_depend_on_global_random_state(sample):
    import random
    random.seed(1)
    a = pz.make_puzzle(sample, "s4", 5).to_dict()
    random.seed(999)
    assert pz.make_puzzle(sample, "s4", 5).to_dict() == a


def test_splitmix_and_fnv_are_stable():
    # the values are pinned: a change here would silently reshuffle every puzzle ever generated
    assert pz.fnv1a64("a") == 0xAF63DC4C8601EC8C
    r = pz.Rng("chronicle")
    assert [r.next() for _ in range(3)] == [2303502871580541555, 17142478649128212218, 17162098717344345325]


def test_rng_helpers(sample):
    r = pz.Rng("x")
    assert sorted(r.shuffle([1, 2, 3, 4])) == [1, 2, 3, 4]
    assert len(set(r.sample(list(range(10)), 4))) == 4
    assert all(0 <= r.below(5) < 5 for _ in range(50))
    with pytest.raises(ValueError):
        r.below(0)


@pytest.mark.parametrize("section", ["s1", "s2", "s3", "s4"])
def test_every_puzzle_has_distinct_dates_the_right_size_and_a_correct_answer(sample, section):
    sec = sample.section(section)
    for r in range(len(sample.section_pool(section)) + 3):
        p = pz.make_puzzle(sample, section, r)
        assert p.size == sec["size"] == len(p.tray) == len(p.answer)
        assert sorted(p.tray) == sorted(p.answer)
        keys = [event_key(sample.events[e]) for e in p.answer]
        assert keys == sorted(keys) and len(set(keys)) == len(keys)
        assert p.tray != p.answer                        # never handed over already in order
        assert set(p.answer) <= set(sample.section_pool(section))


@pytest.mark.parametrize("section", ["s1", "s2", "s3"])
def test_the_difficulty_gap_holds_for_every_round(sample, section):
    gap = sample.section(section)["min_gap_years"]
    for r in range(len(sample.section_pool(section))):
        years = sorted(year_of(sample.events[e]) for e in pz.make_puzzle(sample, section, r).answer)
        assert all(b - a >= gap for a, b in zip(years, years[1:])), (section, r, years)


def test_the_last_section_is_allowed_near_ties(sample):
    close = 0
    for r in range(40):
        years = sorted(year_of(sample.events[e]) for e in pz.make_puzzle(sample, "s4", r).answer)
        close += any(b - a <= 2 for a, b in zip(years, years[1:]))
    assert close > 0                      # 1863's two events (and 1801/1803) do appear together


@pytest.mark.parametrize("section", ["s1", "s2", "s3", "s4"])
def test_the_first_n_rounds_visit_every_event_so_100_percent_is_reachable(sample, section):
    pool = sample.section_pool(section)
    seen = set()
    for r in range(len(pool)):
        seen |= set(pz.make_puzzle(sample, section, r).answer)
    assert seen == set(pool)


def test_rounds_beyond_the_main_ones_keep_generating(sample):
    assert pz.make_puzzle(sample, "s1", 500).size == 3
    assert pz.main_rounds(sample, "s1") == 5


def test_bad_inputs_raise_value_error(sample):
    for args in (("nope", 0), ("s1", -1), ("s1", True), ("s1", "0")):
        with pytest.raises(ValueError):
            pz.make_puzzle(sample, *args)


def test_grading_marks_right_cards_and_says_which_way_the_wrong_ones_move(sample):
    p = pz.make_puzzle(sample, "s2", 0)
    a = p.answer
    perfect = pz.grade(p, a)
    assert perfect["all_right"] and perfect["right"] == p.size
    swapped = [a[1], a[0]] + a[2:]
    g = pz.grade(p, swapped)
    assert g["right"] == p.size - 2 and not g["all_right"]
    assert g["slots"][0]["status"] == "wrong" and g["slots"][0]["direction"] == "later"
    assert g["slots"][1]["status"] == "wrong" and g["slots"][1]["direction"] == "earlier"
    partial = pz.grade(p, [a[0], None, None, a[3]])
    assert [s["status"] for s in partial["slots"]] == ["right", "empty", "empty", "right"]
    assert partial["placed"] == 2 and partial["right"] == 2


def test_grading_a_reversed_timeline_marks_every_card_wrong(sample):
    p = pz.make_puzzle(sample, "s3", 0)
    g = pz.grade(p, list(reversed(p.answer)))
    assert g["right"] == 1                 # a middle card of an odd-sized puzzle stays put
    p2 = pz.make_puzzle(sample, "s2", 0)
    assert pz.grade(p2, list(reversed(p2.answer)))["right"] == 0


def test_the_nuance_strip_lists_elsewhere_events_within_the_window_nearest_card_first(sample):
    p = pz.make_puzzle(sample, "s1", 0)       # 1789, 1801, 1814
    n = pz.nuance(sample, p)
    ids = [x["event"] for x in n]
    assert ids == ["c-bastille", "c-waterloo"]
    assert n[0]["near"] == "e-washington-oath" and n[0]["years"] == 0
    assert n[1]["near"] == "e-capitol-burned" and n[1]["years"] == 1
    # an event 40 years from anything is not in the strip
    p3 = pz.make_puzzle(sample, "s3", 1)      # 1901, 1951, 1974
    assert "c-origin" not in [x["event"] for x in pz.nuance(sample, p3)]


def test_every_elsewhere_event_appears_in_some_puzzles_nuance_strip(sample):
    seen = set()
    for sid in sample.section_ids:
        for r in range(len(sample.section_pool(sid))):
            seen |= {x["event"] for x in pz.nuance(sample, pz.make_puzzle(sample, sid, r))}
    assert seen == set(sample.event_ids("context"))
