"""The learner: small, deterministic, and exactly what the About page says it is."""

import itertools

import pytest

import learner
import lessonkit
import lessons

YES_NO = lambda fid: {"id": fid, "label": fid.title(), "kind": "yes_no"}
NUM = lambda fid, lo, hi: {"id": fid, "label": fid.title(), "kind": "number", "lo": lo, "hi": hi, "unit": ""}


def case(i, label, **v):
    return {"id": "c%d" % i, "name": "Case %d" % i, "v": v, "label": label}


def test_entropy_values():
    assert learner.entropy([1, 1]) == pytest.approx(1.0)
    assert learner.entropy([4, 0]) == 0.0
    assert learner.entropy([1, 3]) == pytest.approx(0.8112781, abs=1e-6)
    assert learner.entropy([0, 0]) == 0.0
    assert learner.entropy([2, 2, 2, 2]) == pytest.approx(2.0)


def test_a_clean_number_split_sits_between_the_two_neighbouring_values():
    feats = [NUM("x", 0, 20)]
    cases = [case(i, 0 if x < 5 else 1, x=x) for i, x in enumerate([1, 2, 3, 10, 11, 12])]
    cases[2]["label"] = 0
    tree = learner.train(feats, {"x"}, cases, 2)
    assert tree["test"] == {"f": "x", "op": "ge", "arg": 7}          # (3 + 10 + 1) // 2
    assert tree["yes"]["leaf"] and tree["yes"]["label"] == 1 and tree["no"]["label"] == 0
    assert tree["gain"] == pytest.approx(1.0)


def test_thresholds_for_neighbours_one_apart_are_the_upper_value():
    feats = [NUM("x", 0, 9)]
    cases = [case(0, 0, x=4), case(1, 1, x=5)]
    assert learner.train(feats, {"x"}, cases, 2)["test"]["arg"] == 5


def test_ties_go_to_the_feature_that_comes_first():
    cases = [case(0, 0, a=1, b=1), case(1, 0, a=1, b=1), case(2, 1, a=0, b=0), case(3, 1, a=0, b=0)]
    both = [YES_NO("a"), YES_NO("b")]
    assert learner.train(both, {"a", "b"}, cases, 2)["test"]["f"] == "a"
    assert learner.train(list(reversed(both)), {"a", "b"}, cases, 2)["test"]["f"] == "b"
    assert learner.train(both, {"b"}, cases, 2)["test"]["f"] == "b"


def test_a_switched_off_feature_is_never_asked_about():
    cases = [case(0, 0, a=1, b=0), case(1, 1, a=0, b=1)]
    tree = learner.train([YES_NO("a"), YES_NO("b")], {"b"}, cases, 2)
    assert learner.used_features(tree) == {"b"}


def test_a_greedy_tree_cannot_learn_xor_and_says_the_majority():
    feats = [YES_NO("a"), YES_NO("b")]
    cases = [case(0, 0, a=0, b=0), case(1, 1, a=0, b=1), case(2, 1, a=1, b=0), case(3, 0, a=1, b=1)]
    tree = learner.train(feats, {"a", "b"}, cases, 2)
    assert tree["leaf"] == 1 and tree["label"] == 0 and tree["counts"] == [2, 2]       # no gain anywhere: a tie goes to the lowest bin


def test_a_pure_group_is_a_leaf_and_no_features_is_a_leaf():
    cases = [case(0, 1, a=0), case(1, 1, a=1)]
    assert learner.train([YES_NO("a")], {"a"}, cases, 2)["leaf"] == 1
    mixed = [case(0, 0, a=0), case(1, 1, a=1), case(2, 1, a=1)]
    leaf = learner.train([YES_NO("a")], set(), mixed, 2)
    assert leaf["leaf"] == 1 and leaf["label"] == 1 and leaf["counts"] == [1, 2]


def test_word_features_ask_one_word_at_a_time_in_the_listed_order():
    f = {"id": "k", "label": "Kind", "kind": "kind", "values": ["round", "long", "flat"]}
    cases = [case(0, 0, k="long"), case(1, 0, k="long"), case(2, 1, k="round"), case(3, 1, k="flat")]
    assert [t["arg"] for t in learner.candidates(f, cases)] == ["round", "long", "flat"]
    tree = learner.train([f], {"k"}, cases, 2)
    assert tree["test"] == {"f": "k", "op": "eq", "arg": "long"}


def test_three_bins_work():
    feats = [NUM("x", 0, 30)]
    cases = [case(i, 0 if x < 10 else 1 if x < 20 else 2, x=x) for i, x in enumerate([2, 5, 8, 12, 15, 18, 22, 25, 28])]
    tree = learner.train(feats, {"x"}, cases, 3)
    assert learner.tree_depth(tree) == 2 and all(learner.predict(tree, c) == c["label"] for c in cases)


def test_a_tree_is_never_deeper_than_three_questions():
    feats = [YES_NO("a"), YES_NO("b"), YES_NO("c"), YES_NO("d")]
    rows = list(itertools.product([0, 1], repeat=4))
    cases = [case(i, 1 if sum(r) >= 3 or (r[0] and r[3]) else 0, a=r[0], b=r[1], c=r[2], d=r[3]) for i, r in enumerate(rows)]
    assert learner.tree_depth(learner.train(feats, {"a", "b", "c", "d"}, cases, 2)) <= learner.MAX_DEPTH


def test_training_is_the_same_every_time():
    lesson = lessons.BY_ID["lab-samples"]
    first = lessonkit.fit(lesson, set(lesson["fids"]))
    for _ in range(3):
        assert lessonkit.fit(lesson, set(lesson["fids"])) == first


def test_the_input_order_of_the_on_set_does_not_matter():
    lesson = lessons.BY_ID["lab-samples"]
    assert lessonkit.fit(lesson, {"fizz", "temp", "tray"}) == lessonkit.fit(lesson, ["tray", "temp", "fizz"])


def test_predict_and_trace_always_agree_and_the_path_replays():
    """The Why panel's path is the learner's own walk: replay it question by question and it ends at the same leaf and the same answer."""
    for lesson in lessons.ALL:
        by_id = lesson["by_id"]
        for on in (set(lesson["fids"]), set(lesson["best"]), set(lesson["start"])):
            tree = lessonkit.fit(lesson, on)
            for c in lesson["train_cases"] + lesson["test_cases"]:
                steps, leaf = learner.trace(tree, by_id, c)
                assert leaf["label"] == learner.predict(tree, c)
                node = tree
                for step in steps:
                    assert node["test"] == step["test"]
                    assert (step["answer"] == "yes") == learner.holds(step["test"], c["v"][step["test"]["f"]])
                    node = node[step["answer"]]
                assert node is leaf


def test_the_words_of_a_tree_name_every_question_and_every_bin():
    lesson = lessons.BY_ID["night-crates"]
    tree = lessonkit.fit(lesson, set(lesson["best"]))
    text = " ".join(line["text"] for line in learner.tree_lines(tree, lesson["by_id"], lesson["bins"]))
    for f in learner.used_features(tree):
        assert lesson["by_id"][f]["label"] in text
    assert "Ripe" in text and "Not yet" in text


def test_a_question_reads_naturally():
    f = {"id": "w", "label": "Weight", "kind": "number", "lo": 1, "hi": 20, "unit": "kg"}
    assert learner.question(f, {"f": "w", "op": "ge", "arg": 7}) == "Weight 7 kg or more?"
    assert learner.question(YES_NO("stripes"), {"f": "stripes", "op": "yes"}) == "Stripes: yes?"
    assert learner.question({"id": "k", "label": "Handle", "kind": "kind", "values": []}, {"f": "k", "op": "eq", "arg": "bar"}) == "Handle is bar?"
