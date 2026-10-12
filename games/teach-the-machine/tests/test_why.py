"""The Why panel: every wrong answer is in exactly one category by an explicit rule, and the explanation is the learner's own path."""

import pytest

import learner
import lessonkit
import lessons
import subsets
import why


def wrong_cases(lesson, on):
    tree = lessonkit.fit(lesson, set(on))
    return tree, [c for c in lesson["test_cases"] if learner.predict(tree, c) != c["label"]]


def test_five_categories_with_unique_names():
    assert len(why.CATEGORIES) == 5 and len({c["id"] for c in why.CATEGORIES}) == 5
    assert set(why.CATEGORY_IDS) == {"missing", "too_few", "distracting", "shortcut", "mislabelled"}
    for c in why.CATEGORIES:
        assert c["name"] and c["about"] and c["example"]


def test_every_wrong_answer_of_every_set_of_switches_has_exactly_one_category():
    seen = {}
    total = 0
    for lesson in lessons.ALL:
        for on in subsets.all_scores(lesson):
            if not on:
                continue
            tree, wrong = wrong_cases(lesson, on)
            for c in wrong:
                total += 1
                hits = [cid for cid, hit in why.checks(lesson, on, c) if hit]
                category = why.categorise(lesson, on, c)
                assert category in why.CATEGORY_IDS
                assert category == (hits[0] if hits else "too_few")            # the first rule that holds, otherwise the fallback
                seen.setdefault(category, set()).add(lesson["shelf"])
    assert total > 500


def test_each_rule_means_what_it_says():
    for lesson in lessons.ALL:
        needs, fids = set(lesson["needs"]), set(lesson["fids"])
        for on in subsets.all_scores(lesson):
            if not on:
                continue
            on = set(on)
            tree, wrong = wrong_cases(lesson, on)
            for c in wrong:
                category = why.categorise(lesson, on, c)
                if category == "missing":
                    assert needs - on                                           # a needed feature is off ...
                    assert learner.predict(lessonkit.fit(lesson, on | needs), c) == c["label"]     # ... and switching it on fixes THIS case
                elif category == "distracting":
                    assert on - needs and on & needs
                    assert learner.predict(lessonkit.fit(lesson, on & needs), c) == c["label"]
                elif category == "too_few":
                    # none of the other rules applies: either nothing is missing or switching the needed ones on does not help
                    assert not any(hit for _, hit in why.checks(lesson, on, c))
                else:
                    pytest.fail("shelves 1 to 3 have no shortcut or mislabelled lessons: %s" % category)


def test_shelves_one_to_three_can_show_missing_distracting_and_too_few_and_nothing_else():
    found = set()
    for lesson in lessons.ALL:
        for on in subsets.all_scores(lesson):
            if on:
                found |= {why.categorise(lesson, on, c) for c in wrong_cases(lesson, on)[1]}
    assert found == {"missing", "distracting", "too_few"}


def test_the_best_set_leaves_only_too_few_examples_mistakes():
    """With exactly the right features nothing is missing or distracting: whatever is still wrong is the gap in the training table."""
    for lesson in lessons.ALL:
        tree, wrong = wrong_cases(lesson, set(lesson["best"]))
        for c in wrong:
            assert why.categorise(lesson, set(lesson["best"]), c) == "too_few"


def test_the_explanation_replays_the_learners_walk():
    for lesson in lessons.ALL:
        for on in (set(lesson["start"]), set(lesson["fids"]), set(lesson["best"])):
            tree, wrong = wrong_cases(lesson, on)
            for c in wrong:
                e = why.explain(lesson, on, tree, c)
                assert e["pip"] == lesson["bins"][learner.predict(tree, c)] and e["truth"] == lesson["bins"][c["label"]] and e["pip"] != e["truth"]
                node = tree
                for step in e["steps"]:
                    holds = learner.holds(node["test"], c["v"][node["test"]["f"]])
                    assert step["answer"] == ("yes" if holds else "no")
                    assert step["question"] == learner.question(lesson["by_id"][node["test"]["f"]], node["test"])
                    node = node["yes" if holds else "no"]
                assert node["leaf"] and lesson["bins"][node["label"]] == e["pip"]
                assert e["group"]["n"] == node["n"] and sum(g["n"] for g in e["group"]["counts"]) == node["n"]
                if e["steps"]:
                    assert e["decisive"]["question"] == e["steps"][-1]["question"]
                else:
                    assert e["decisive"] is None
                assert len(e["neighbours"]) <= why.MAX_NEIGHBOURS and e["category"] in why.CATEGORY_IDS and e["because"]


def test_the_neighbours_are_training_cases_that_ended_in_the_same_group():
    lesson = lessons.BY_ID["friendly-signals"]
    on = set(lesson["start"])
    tree, wrong = wrong_cases(lesson, on)
    by_id = lesson["by_id"]
    for c in wrong:
        e = why.explain(lesson, on, tree, c)
        key = learner.leaf_key(learner.trace(tree, by_id, c)[0])
        names = {t["name"]: t for t in lesson["train_cases"]}
        for n in e["neighbours"]:
            assert learner.leaf_key(learner.trace(tree, by_id, names[n["name"]])[0]) == key
        assert e["neighbours"]


def test_the_explanation_is_the_same_every_time():
    lesson = lessons.BY_ID["crowded-doors"]
    on = set(lesson["fids"])
    tree, wrong = wrong_cases(lesson, on)
    assert wrong
    assert [why.explain(lesson, on, tree, c) for c in wrong] == [why.explain(lesson, on, tree, c) for c in wrong]


# ---- shortcut and mislabelled: no shipped lesson has them yet (shelves 4 and 5), so prove the rules on small made-up lessons ----------
def made_up(train, test, shortcuts=(), mislabelled=(), needs=("x",)):
    feats = [{"id": "s", "label": "Habit", "kind": "yes_no", "about": ""}, {"id": "x", "label": "Level", "kind": "number", "lo": 0, "hi": 9, "unit": "", "about": ""}]
    raw = {"id": "made-up", "kind": "basic", "title": "Made up", "task": "", "noun": "Thing", "bins": ["A", "B"], "features": feats,
           "train": [["T%d" % i, list(v), lab] for i, (v, lab) in enumerate(train)], "test": [["U%d" % i, list(v), lab] for i, (v, lab) in enumerate(test)],
           "target": 90, "start": ["s", "x"], "gentle": False, "needs": list(needs), "shortcuts": list(shortcuts), "mislabelled": list(mislabelled),
           "learned": "", "best": list(needs)}
    return lessonkit.prepare(raw, 0, 1)


def test_a_shortcut_is_a_habit_feature_that_only_matched_in_training():
    train = [((1, x), 0) for x in (6, 7, 8, 9)] + [((0, x), 1) for x in (0, 1, 2, 3)]       # the habit matches the answer perfectly, and so does the level
    test = [((0, 8), 0), ((1, 1), 1), ((1, 7), 0), ((0, 2), 1)]
    lesson = made_up(train, test, shortcuts=["s"])
    on = {"s", "x"}
    tree = lessonkit.fit(lesson, on)
    assert tree["test"]["f"] == "s"                                         # the tie goes to the first feature: Pip takes the shortcut
    wrong = [c for c in lesson["test_cases"] if learner.predict(tree, c) != c["label"]]
    assert {c["name"] for c in wrong} == {"U0", "U1"}
    for c in wrong:
        assert why.categorise(lesson, on, c) == "shortcut"
    lesson["shortcuts"] = []
    assert all(why.categorise(lesson, on, c) != "shortcut" for c in wrong)    # without the flag the same mistake is a plain distraction


def test_a_mislabelled_example_is_found_by_training_without_it():
    train = [((0, x), 1) for x in (0, 1, 2, 3)] + [((0, x), 0) for x in (4, 5, 6, 7)] + [((0, 8), 1), ((0, 9), 1)]
    # the last two training cases (levels 8 and 9) carry the wrong label B; everything from 4 up should be A
    test = [((0, 8), 0), ((0, 9), 0), ((0, 2), 1), ((0, 5), 0)]
    lesson = made_up(train, test, mislabelled=[8, 9])
    on = {"x"}
    tree, wrong = wrong_cases(lesson, on)
    assert {c["name"] for c in wrong} == {"U0", "U1"}
    for c in wrong:
        assert why.categorise(lesson, on, c) == "mislabelled"
    clean = made_up(train, test)
    assert all(why.categorise(clean, on, c) != "mislabelled" for c in wrong_cases(clean, on)[1])


def test_the_order_of_the_rules_puts_mislabelled_first_and_missing_before_distracting():
    train = [((0, x), 1) for x in (0, 1, 2, 3)] + [((0, x), 0) for x in (4, 5, 6, 7)] + [((0, 8), 1), ((0, 9), 1)]
    test = [((0, 8), 0)]
    lesson = made_up(train, test, mislabelled=[8, 9])
    c = lesson["test_cases"][0]
    assert why.categorise(lesson, {"x"}, c) == "mislabelled"
    assert [cid for cid, _ in why.checks(lesson, {"x"}, c)] == ["mislabelled", "missing", "shortcut", "distracting"]
