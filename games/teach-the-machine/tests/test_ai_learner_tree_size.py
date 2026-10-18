"""Tests for learner.tree_size()."""


import learner


def yes_no(fid):
    return {"id": fid, "label": fid.title(), "kind": "yes_no"}


def case(i, label, **v):
    return {"id": "c%d" % i, "name": "Case %d" % i, "v": v, "label": label}


def test_leaf_node_has_size_one():
    """Edge case: a pure leaf counts as exactly one node."""
    leaf = {"leaf": 1, "label": 0, "counts": [2, 0], "n": 2}
    assert learner.tree_size(leaf) == 1


def test_single_split_tree_has_three_nodes():
    """Normal case: a root with two pure children has three nodes total."""
    feats = [yes_no("a")]
    cases = [case(0, 0, a=0), case(1, 1, a=1)]
    tree = learner.train(feats, {"a"}, cases, 2)
    assert learner.tree_size(tree) == 3


def test_deeper_tree_has_five_nodes():
    """Normal case: a root splitting into one pure branch and one mixed branch that splits again yields five nodes."""
    feats = [yes_no("a"), yes_no("b")]
    cases = [
        case(0, 0, a=0, b=0), case(1, 0, a=0, b=1),
        case(2, 0, a=1, b=0), case(3, 1, a=1, b=1),
    ]
    tree = learner.train(feats, {"a", "b"}, cases, 2)
    assert learner.tree_size(tree) == 5
