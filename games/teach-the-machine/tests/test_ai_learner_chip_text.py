"""Tests for learner.chip_text()."""

import learner


def YES_NO(fid):
    return {"id": fid, "label": fid.title(), "kind": "yes_no"}


def NUM(fid, lo, hi):
    return {"id": fid, "label": fid.title(), "kind": "number", "lo": lo, "hi": hi, "unit": ""}


def test_chip_text_yes_no():
    """A yes_no feature formats its boolean value as 'yes' or 'no'."""
    f = YES_NO("stripes")
    assert learner.chip_text(f, True) == "Stripes: yes"
    assert learner.chip_text(f, False) == "Stripes: no"


def test_chip_text_number_with_unit():
    """A number feature with a unit appends the unit separated by a space."""
    f = NUM("weight", 0, 20)
    f["unit"] = "kg"
    assert learner.chip_text(f, 5) == "Weight: 5 kg"


def test_chip_text_number_without_unit():
    """A number feature without a unit prints just the integer value."""
    f = NUM("temp", 0, 100)
    assert learner.chip_text(f, 0) == "Temp: 0"


def test_chip_text_kind():
    """A kind feature prints the word value as-is."""
    f = {"id": "k", "label": "Kind", "kind": "kind", "values": ["round", "long"]}
    assert learner.chip_text(f, "round") == "Kind: round"
