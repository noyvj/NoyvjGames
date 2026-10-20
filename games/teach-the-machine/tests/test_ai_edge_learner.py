"""Edge cases for Pip's learner: empty inputs, boundaries, and single-element trees."""


import learner


def YES_NO(fid):
    return {"id": fid, "label": fid.title(), "kind": "yes_no"}


def NUM(fid, lo, hi):
    return {"id": fid, "label": fid.title(), "kind": "number", "lo": lo, "hi": hi, "unit": ""}


def case(i, label, **v):
    return {"id": "c%d" % i, "name": "Case %d" % i, "v": v, "label": label}


def test_entropy_handles_empty_and_zero_counts():
    """Entropy should return 0.0 for no data or all-zero bins."""
    assert learner.entropy([]) == 0.0
    assert learner.entropy([0]) == 0.0
    assert learner.entropy([0, 0, 0]) == 0.0


def test_train_returns_a_leaf_for_empty_cases():
    """Training on zero cases cannot split; it must return a leaf with label 0."""
    feats = [YES_NO("a")]
    tree = learner.train(feats, {"a"}, [], 2)
    assert tree["leaf"] == 1
    assert tree["label"] == 0
    assert tree["n"] == 0


def test_predict_on_a_leaf_tree_returns_the_label_without_walking():
    """A leaf tree has no questions; predict should just return the stored label."""
    leaf = {"leaf": 1, "label": 1, "counts": [0, 5], "n": 5}
    c = case(0, 1, a=1)
    assert learner.predict(leaf, c) == 1


def test_distance_returns_zero_for_identical_cases_or_empty_features():
    """Distance is 0 when cases match exactly or no features are switched on."""
    f = NUM("x", 0, 10)
    a = case(0, 0, x=5)
    b = case(1, 0, x=5)
    assert learner.distance([f], {"x"}, a, b) == 0.0
    assert learner.distance([], {"x"}, a, b) == 0.0


def test_distance_maxes_out_for_number_features():
    """Distance should reach 1.0 when a number feature spans its full range."""
    f = NUM("x", 0, 10)
    a = case(0, 0, x=0)
    b = case(1, 0, x=10)
    assert learner.distance([f], {"x"}, a, b) == 1.0


def test_holds_boundary_values_for_ge_and_eq():
    """holds should correctly evaluate exact boundaries for 'ge' and 'eq'."""
    assert learner.holds({"op": "ge", "arg": 5}, 5) is True
    assert learner.holds({"op": "ge", "arg": 5}, 4) is False
    assert learner.holds({"op": "eq", "arg": "x"}, "x") is True
    assert learner.holds({"op": "eq", "arg": "x"}, "y") is False
