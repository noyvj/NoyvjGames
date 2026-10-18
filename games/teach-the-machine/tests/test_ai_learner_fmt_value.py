"""Tests for learner.fmt_value."""


import learner


def YES_NO(fid):
    return {"id": fid, "label": fid.title(), "kind": "yes_no"}


def NUM(fid, lo, hi):
    return {"id": fid, "label": fid.title(), "kind": "number", "lo": lo, "hi": hi, "unit": ""}


def test_yes_no_returns_yes_for_truthy():
    assert learner.fmt_value(YES_NO("x"), 1) == "yes"


def test_yes_no_returns_no_for_falsy():
    assert learner.fmt_value(YES_NO("x"), 0) == "no"


def test_number_with_unit_includes_space_and_unit():
    f = NUM("w", 0, 20)
    f["unit"] = "kg"
    assert learner.fmt_value(f, 5) == "5 kg"


def test_number_without_unit_omits_trailing_space():
    f = NUM("w", 0, 20)
    assert learner.fmt_value(f, 5) == "5"


def test_kind_returns_string_of_value():
    f = {"id": "k", "label": "Kind", "kind": "kind", "values": ["round", "long"]}
    assert learner.fmt_value(f, "round") == "round"
