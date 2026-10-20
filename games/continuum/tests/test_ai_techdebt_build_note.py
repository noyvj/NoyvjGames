"""Tests for techdebt.build_note()."""

import techdebt


def test_build_note_returns_expected_string_for_cost_100():
    record = {}
    cost = 100
    result = techdebt.build_note(record, cost)
    assert result == "Quick builds cost 25% less (about 25 materials back on a 100-material building) but add 5% technical debt each."


def test_build_note_returns_expected_string_for_cost_40():
    record = {}
    cost = 40
    result = techdebt.build_note(record, cost)
    assert result == "Quick builds cost 25% less (about 10 materials back on a 40-material building) but add 5% technical debt each."


def test_build_note_handles_zero_cost():
    record = {}
    cost = 0
    result = techdebt.build_note(record, cost)
    assert result == "Quick builds cost 25% less (about 0 materials back on a 0-material building) but add 5% technical debt each."
