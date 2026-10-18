"""Tests for learner.distance(): how different two cases look to Pip over switched-on features."""

import pytest

import learner


def case(i, label, **v):
    return {"id": "c%d" % i, "name": "Case %d" % i, "v": v, "label": label}


def YES_NO(fid):
    return {"id": fid, "label": fid.title(), "kind": "yes_no"}


def NUM(fid, lo, hi):
    return {"id": fid, "label": fid.title(), "kind": "number", "lo": lo, "hi": hi, "unit": ""}


def test_identical_cases_have_zero_distance():
    """Two cases with the same values on all switched-on features yield 0.0."""
    feats = [YES_NO("a"), NUM("b", 0, 10)]
    a = case(0, 0, a=1, b=5)
    b = case(1, 0, a=1, b=5)
    assert learner.distance(feats, {"a", "b"}, a, b) == 0.0


def test_number_feature_distance_scales_by_span():
    """A number feature contributes abs(diff) / span to the total distance."""
    feats = [NUM("x", 0, 10)]
    a = case(0, 0, x=2)
    b = case(1, 0, x=8)
    assert learner.distance(feats, {"x"}, a, b) == pytest.approx(0.6)


def test_empty_switched_on_set_returns_zero():
    """Edge case: when no features are switched on, distance is always 0.0."""
    feats = [YES_NO("a"), NUM("b", 0, 10)]
    a = case(0, 0, a=1, b=5)
    b = case(1, 0, a=0, b=0)
    assert learner.distance(feats, set(), a, b) == 0.0
