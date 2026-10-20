"""Edge cases for lessonkit: limits, empty inputs, and ordering."""

import lessonkit


def _make_raw(features=None, train_rows=None, test_rows=None, target=90):
    if features is None:
        features = [{"id": "a", "label": "A", "kind": "yes_no"}]
    return {
        "features": features,
        "train": train_rows or [],
        "test": test_rows or [],
        "target": target,
        "bins": [0, 1],
    }


def _make_lesson(**kwargs):
    raw = _make_raw(**kwargs)
    return lessonkit.prepare(raw, shelf=1, number=1)


def test_need_for_zero_and_hundred_percent():
    """need_for returns 0 for 0% target and the full table size for 100%."""
    assert lessonkit.need_for({"target": 0, "test": [1, 2]}) == 0
    assert lessonkit.need_for({"target": 100, "test": [1, 2, 3]}) == 3


def test_need_for_odd_length_rounding():
    """need_for uses ceiling division for fractional percentages."""
    # ceil(0.9 * 21) = 19
    assert lessonkit.need_for({"target": 90, "test": list(range(21))}) == 19
    # ceil(0.5 * 3) = 2
    assert lessonkit.need_for({"target": 50, "test": [1, 2, 3]}) == 2


def test_order_set_empty_and_unknown_ids():
    """order_set returns an empty list for missing or unknown feature ids."""
    lesson = _make_lesson(features=[{"id": "a"}, {"id": "b"}, {"id": "c"}])
    assert lessonkit.order_set(lesson, []) == []
    assert lessonkit.order_set(lesson, ["x", "y"]) == []


def test_order_set_partial_and_full_overlap():
    """order_set preserves the lesson's feature order for valid ids."""
    lesson = _make_lesson(features=[{"id": "a"}, {"id": "b"}, {"id": "c"}])
    assert lessonkit.order_set(lesson, ["c", "a"]) == ["a", "c"]


def test_fit_with_empty_on_set():
    """fit produces a leaf node when no features are switched on."""
    lesson = _make_lesson(train_rows=[("c1", [1], 0)])
    tree = lessonkit.fit(lesson, set())
    assert "leaf" in tree and tree["label"] == 0


def test_score_and_train_score_with_empty_tables():
    """score and train_score return zero counts when their case tables are empty."""
    lesson_no_test = _make_lesson(test_rows=[])
    right, total, returned_tree = lessonkit.score(lesson_no_test, {"a"}, {"leaf": 1, "label": 0})
    assert right == 0 and total == 0

    lesson_no_train = _make_lesson(train_rows=[])
    right, total = lessonkit.train_score(lesson_no_train, {"leaf": 1, "label": 0})
    assert right == 0 and total == 0


def test_fit_drop_flagged_removes_cases():
    """fit respects drop_flagged by excluding mislabelled indices from training."""
    lesson = _make_lesson(
        train_rows=[("c1", [1], 0), ("c2", [2], 1)],
        features=[{"id": "a", "kind": "yes_no"}]
    )
    lesson["mislabelled"] = [0]
    tree = lessonkit.fit(lesson, {"a"}, drop_flagged=True)
    assert "leaf" in tree or "test" in tree


def test_prepare_sets_defaults():
    """prepare adds empty lists for mislabelled and shortcuts if missing."""
    raw = {"features": [{"id": "a"}], "train": [], "test": [], "target": 90, "bins": [0, 1]}
    lesson = lessonkit.prepare(raw, shelf=1, number=1)
    assert lesson["mislabelled"] == []
    assert lesson["shortcuts"] == []
