"""Chronicle -- edge-case tests for myth or record mechanics."""

import pytest

import myth as mq


def test_main_rounds_returns_zero_for_missing_chapter(sample):
    """main_rounds should return 0 when the chapter does not exist."""
    assert mq.main_rounds(sample, "nonexistent-chapter") == 0


def test_make_myth_puzzle_rejects_negative_round(sample):
    """make_myth_puzzle must reject negative round numbers."""
    with pytest.raises(ValueError, match="round must be a non-negative integer"):
        mq.make_myth_puzzle(sample, "m1", -1)


def test_make_myth_puzzle_rejects_boolean_round(sample):
    """make_myth_puzzle must reject booleans for round_no."""
    with pytest.raises(ValueError, match="round must be a non-negative integer"):
        mq.make_myth_puzzle(sample, "m1", True)


def test_make_myth_puzzle_rejects_float_round(sample):
    """make_myth_puzzle must reject floats for round_no."""
    with pytest.raises(ValueError, match="round must be a non-negative integer"):
        mq.make_myth_puzzle(sample, "m1", 1.5)


def test_make_myth_puzzle_handles_very_large_round_value(sample):
    """make_myth_puzzle should handle arbitrarily large round numbers without error."""
    puz = mq.make_myth_puzzle(sample, "m1", 10**9)
    assert isinstance(puz.tray, list) and len(puz.tray) > 0


def test_make_myth_puzzle_rejects_missing_chapter(sample):
    """make_myth_puzzle must raise ValueError for unknown chapter IDs."""
    with pytest.raises(ValueError, match="unknown myth chapter"):
        mq.make_myth_puzzle(sample, "zzz", 0)


def test_grade_with_empty_bins_returns_all_empty_status(sample):
    """grade should mark every claim as 'empty' when bins is empty."""
    puz = mq.make_myth_puzzle(sample, "m1", 0)
    g = mq.grade(puz, {})
    assert g["placed"] == 0 and all(c["status"] == "empty" for c in g["claims"])


def test_grade_with_extra_keys_in_bins_ignores_them(sample):
    """grade should only evaluate claims present in the puzzle's tray."""
    puz = mq.make_myth_puzzle(sample, "m1", 0)
    bins = {c: puz.answer[c] for c in puz.tray}
    bins["nonexistent-claim"] = "documented"
    g = mq.grade(puz, bins)
    assert g["right"] == len(puz.tray) and g["all_right"] is True


def test_myth_puzzle_code_property_format(sample):
    """MythPuzzle.code should return 'set/chapter/round' format."""
    puz = mq.make_myth_puzzle(sample, "m1", 0)
    assert puz.code == "presidents-sample/m1/0"


def test_myth_puzzle_to_dict_returns_correct_structure(sample):
    """MythPuzzle.to_dict should return a dict with expected keys and types."""
    puz = mq.make_myth_puzzle(sample, "m1", 0)
    d = puz.to_dict()
    assert set(d.keys()) == {"id", "set", "chapter", "round", "size", "tray", "answer"}
    assert isinstance(d["tray"], list) and isinstance(d["answer"], dict)
