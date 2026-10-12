"""Teach the Machine -- the lesson kit: turns a lesson's stored tables into cases and scores a set of switched-on features.

No frozen data is imported here, so the dev tools (tools/build_lessons.py, tools/subsets.py) can use it to prove a lesson before it is frozen.
"""

import learner


def need_for(lesson):
    """Whole cases Pip must get right on the unseen table to clear the lesson (the target percent, rounded up)."""
    return -((-lesson["target"] * len(lesson["test"])) // 100)


def _cases(rows, fids, prefix):
    return [{"id": "%s%d" % (prefix, i + 1), "name": name, "v": dict(zip(fids, values)), "label": label}
            for i, (name, values, label) in enumerate(rows)]


def prepare(raw, shelf, number):
    """A lesson dict with its cases built, ready to train on."""
    lesson = dict(raw)
    fids = [f["id"] for f in lesson["features"]]
    lesson["shelf"] = shelf
    lesson["number"] = number
    lesson["fids"] = fids
    lesson["by_id"] = {f["id"]: f for f in lesson["features"]}
    lesson["train_cases"] = _cases(lesson["train"], fids, "T")
    lesson["test_cases"] = _cases(lesson["test"], fids, "U")
    lesson["need"] = need_for(lesson)
    lesson.setdefault("mislabelled", [])
    lesson.setdefault("shortcuts", [])
    return lesson


def order_set(lesson, ids):
    """The ids as a list in the lesson's feature order, unknown ids dropped."""
    wanted = set(ids)
    return [f for f in lesson["fids"] if f in wanted]


def fit(lesson, on, drop_flagged=False):
    """Pip's tree for these switched-on features, trained on the lesson's training table (optionally without the mislabelled examples)."""
    cases = lesson["train_cases"]
    if drop_flagged:
        flagged = set(lesson["mislabelled"])
        cases = [c for i, c in enumerate(cases) if i not in flagged]
    return learner.train(lesson["features"], set(on), cases, len(lesson["bins"]))


def score(lesson, on, tree=None):
    """(right answers on the unseen table, size of the table, the tree)."""
    tree = tree if tree is not None else fit(lesson, on)
    right = sum(1 for c in lesson["test_cases"] if learner.predict(tree, c) == c["label"])
    return right, len(lesson["test_cases"]), tree


def train_score(lesson, tree):
    right = sum(1 for c in lesson["train_cases"] if learner.predict(tree, c) == c["label"])
    return right, len(lesson["train_cases"])
