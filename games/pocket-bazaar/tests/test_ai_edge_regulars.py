import pytest

import regulars


def test_level_handles_zero_visits():
    """level(0) should return 0, as no bond is formed."""
    assert regulars.level(0) == 0


def test_level_clamps_at_max_bond():
    """level() returns 3 for any visits >= 3, matching the maximum bond level."""
    assert regulars.level(3) == 3
    assert regulars.level(100) == 3


def test_rotation_returns_empty_for_day_one_and_before():
    """rotation(day_number) returns an empty list for day 1 and any earlier day."""
    assert regulars.rotation(1) == []
    assert regulars.rotation(0) == []
    assert regulars.rotation(-5) == []


def test_rotation_wraps_around_the_regulars_list():
    """rotation() cycles through the twelve regulars in groups of three."""
    # Day 2 starts at index 0
    day2 = regulars.rotation(2)
    assert len(day2) == 3 and day2[0] == "mira"
    # Day 14 wraps back to the start (day 2 + 12 days, since PER_DAY=3 and len(REGULARS)=12)
    day14 = regulars.rotation(14)
    assert day14 == day2


def test_line_for_returns_correct_string_for_valid_levels():
    """line_for(regular_id, level) returns the exact story line for that bond level."""
    # Mira's first line
    assert "smells every berry" in regulars.line_for("mira", 1)
    # Mira's third line
    assert "pressed leaf" in regulars.line_for("mira", 3)


def test_line_for_rejects_invalid_levels():
    """line_for raises IndexError for levels outside 1-3 (note: Python wraps negative indices, so we test 4)."""
    with pytest.raises(IndexError):
        regulars.line_for("mira", 4)


def test_view_handles_empty_visits_dict():
    """view({}) returns a list of dicts for all regulars with visits=0 and level=0."""
    result = regulars.view({})
    assert len(result) == len(regulars.REGULARS)
    for entry in result:
        assert entry["visits"] == 0
        assert entry["level"] == 0
        assert entry["next_at"] == 1


def test_max_level_returns_zero_for_empty_visits():
    """max_level({}) returns 0 when no regulars have been served."""
    assert regulars.max_level({}) == 0
