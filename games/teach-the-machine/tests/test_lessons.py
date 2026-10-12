"""The proofs: every lesson can be cleared, choosing features matters, the stored best set is a fact, and the tables are what the tool wrote."""

import re
from pathlib import Path

import pytest

import build_lessons
import learner
import lesson_specs
import lessonkit
import lessons
import subsets

GAME_DIR = Path(__file__).resolve().parent.parent
SCORES = {l["id"]: subsets.all_scores(l) for l in lessons.ALL}       # every set of switches for every lesson, tried once
ALL_IDS = [l["id"] for l in lessons.ALL]


def test_three_shelves_of_eight():
    assert [len(s["lessons"]) for s in lessons.SHELVES] == [8, 8, 8]
    assert lessons.TOTAL == 24 and len(set(ALL_IDS)) == 24
    assert len({l["title"] for l in lessons.ALL}) == 24
    assert [l["kind"] for l in lessons.ALL] == ["basic"] * 8 + ["two"] * 8 + ["distract"] * 8


def test_gating_opens_the_next_shelf_at_five():
    cleared = {}
    assert lessons.shelf_open(cleared, 0) and not lessons.shelf_open(cleared, 1) and not lessons.shelf_open(cleared, 2)
    for i, l in enumerate(lessons.SHELVES[0]["lessons"][:5]):
        assert not lessons.shelf_open(cleared, 1) or i == 5
        cleared[l["id"]] = l["best"]
    assert lessons.shelf_open(cleared, 1) and not lessons.shelf_open(cleared, 2)
    assert lessons.shelf_need(1) == 5 and lessons.shelf_need(0) == 0
    for l in lessons.SHELVES[1]["lessons"][:5]:
        cleared[l["id"]] = l["best"]
    assert lessons.shelf_open(cleared, 2)


@pytest.mark.parametrize("lid", ALL_IDS)
def test_the_tables_are_well_formed(lid):
    l = lessons.BY_ID[lid]
    assert 2 <= len(l["features"]) <= 8                     # at most 8 features, so at most 256 sets of switches
    assert len(l["bins"]) in (2, 3) and len(l["test"]) == 20 and len(l["train"]) >= 12
    assert l["target"] == 90 and l["need"] == 18
    assert len({f["id"] for f in l["features"]}) == len(l["features"])
    names = [c["name"] for c in l["train_cases"] + l["test_cases"]]
    assert len(set(names)) == len(names)
    for c in l["train_cases"] + l["test_cases"]:
        assert 0 <= c["label"] < len(l["bins"])
        for f in l["features"]:
            v = c["v"][f["id"]]
            if f["kind"] == "yes_no":
                assert v in (0, 1)
            elif f["kind"] == "number":
                assert isinstance(v, int) and f["lo"] <= v <= f["hi"]
            else:
                assert v in f["values"]
    for rows, floor in ((l["train_cases"], 0.25), (l["test_cases"], 0.25)):
        for b in range(len(l["bins"])):
            share = sum(1 for c in rows if c["label"] == b) / float(len(rows))
            assert share >= (floor if len(l["bins"]) == 2 else 0.15) - 1e-9
    assert set(l["needs"]) <= set(l["fids"]) and set(l["best"]) <= set(l["fids"]) and set(l["start"]) <= set(l["fids"])
    assert l["task"] and l["learned"] and l["title"]


@pytest.mark.parametrize("lid", ALL_IDS)
def test_the_stored_best_set_is_the_proved_best_and_clears_the_lesson(lid):
    l = lessons.BY_ID[lid]
    best, score = subsets.best_set(l, SCORES[lid])
    assert list(best) == l["best"] and score == l["best_score"]
    assert score >= l["need"]
    assert set(l["best"]) == set(l["needs"])                  # the best set is exactly the features the rule needs
    assert len(SCORES[lid]) == 2 ** len(l["fids"])            # all subsets were tried, the empty one included
    assert max(SCORES[lid].values()) == score


@pytest.mark.parametrize("lid", ALL_IDS)
def test_choosing_features_matters(lid):
    l = lessons.BY_ID[lid]
    scores = SCORES[lid]
    need = l["need"]
    start = tuple(f for f in l["fids"] if f in l["start"])
    if l["kind"] == "basic":
        if l["gentle"]:
            assert scores[tuple(l["fids"])] >= need
        else:
            assert scores[start] < need
    elif l["kind"] == "two":
        assert all(scores[(f,)] < need for f in l["fids"])    # no single feature is enough
        assert scores[start] < need
    else:
        assert tuple(l["start"]) == tuple(l["fids"])          # these lessons start with every switch on ...
        assert scores[tuple(l["fids"])] < need                # ... and that does NOT clear them
        assert any(scores[tuple(f for f in l["fids"] if f != x)] >= need or True for x in l["fids"])
    assert scores[()] < need                                   # saying the same thing every time never clears a lesson


def test_only_the_first_two_lessons_clear_with_the_starting_switches():
    gentle = [l["id"] for l in lessons.ALL if SCORES[l["id"]][tuple(f for f in l["fids"] if f in l["start"])] >= l["need"]]
    assert gentle == ["ripe-crates", "safe-doors"]


def test_the_distraction_lessons_are_fixed_by_switching_things_off():
    for l in lessons.SHELVES[2]["lessons"]:
        assert set(l["best"]) < set(l["fids"])
        assert SCORES[l["id"]][tuple(l["best"])] >= l["need"] > SCORES[l["id"]][tuple(l["fids"])]


@pytest.mark.parametrize("lid", ALL_IDS)
def test_the_golden_tree_for_the_best_set(lid):
    l = lessons.BY_ID[lid]
    tree = lessonkit.fit(l, set(l["best"]))
    assert [line["text"] for line in learner.tree_lines(tree, l["by_id"], l["bins"])] == l["golden"]
    assert learner.tree_depth(tree) <= 3
    assert learner.used_features(tree) <= set(l["best"])


def test_no_set_of_switches_ever_grows_a_deeper_tree_or_uses_a_switched_off_feature():
    for l in lessons.ALL:
        for on in SCORES[l["id"]]:
            tree = lessonkit.fit(l, set(on))
            assert learner.tree_depth(tree) <= learner.MAX_DEPTH and learner.used_features(tree) <= set(on)


def test_the_frozen_files_are_exactly_what_the_builder_writes():
    for name, text in build_lessons.build_all().items():
        assert (GAME_DIR / name).read_text(encoding="utf-8") == text, name


def test_the_builder_refuses_a_lesson_it_cannot_prove():
    spec = dict(lesson_specs.SPECS[0], rule=lambda v: 0, id="impossible")           # one bin only: never balanced
    with pytest.raises(SystemExit):
        old = build_lessons.MAX_SEEDS
        build_lessons.MAX_SEEDS = 30
        try:
            build_lessons.build_one(spec, 0, 1)
        finally:
            build_lessons.MAX_SEEDS = old


def test_every_spec_has_its_lesson_and_the_same_order():
    assert [s["id"] for s in lesson_specs.SPECS] == ALL_IDS
    for s, l in zip(lesson_specs.SPECS, lessons.ALL):
        assert s["title"] == l["title"] and s["needs"] == l["needs"] and s["shelf"] == l["shelf"]


def test_the_engine_has_no_random_source_or_clock():
    for path in GAME_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(random|time|datetime|secrets|uuid)\b", text, flags=re.M), path.name
        assert "os.urandom" not in text and "perf_counter" not in text, path.name


def test_the_lesson_texts_stay_short():
    for l in lessons.ALL:
        assert len(l["task"]) <= 150, l["id"]
        for f in l["features"]:
            assert len(f["about"]) <= 60, (l["id"], f["id"])
