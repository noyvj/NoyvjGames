"""Tests for Case.usable() in casework.py."""

import casework as cw
import progress


def test_usable_returns_only_valid_evidence_indices():
    """Normal case: usable(slot) should only contain evidence indices 0 through 5."""
    case = cw.Case(progress.DATA["1-1"])
    for slot in range(case.n):
        result = case.usable(slot)
        assert isinstance(result, set), "usable() must return a set"
        assert all(0 <= e < 6 for e in result), f"evidence index {result} out of range for slot {slot}"


def test_usable_excludes_evidence_fooled_by_features():
    """Normal case: usable(slot) contains evidence e if and only if at least one restless room in the slot reads it cleanly."""
    case = cw.Case(progress.DATA["2-1"])  # Chapter 2 introduces features
    for slot in range(case.n):
        result = case.usable(slot)
        for e in range(6):
            has_clean_reading = any(case.reading(room, e) != cw.DOUBTFUL for room in case.slots[slot])
            if has_clean_reading:
                assert e in result, f"evidence {e} has a clean reading in slot {slot} but is missing from usable({slot})"
            else:
                assert e not in result, f"evidence {e} is fooled by all rooms in slot {slot} but appears in usable({slot})"


def test_usable_edge_case_no_features_or_keepsakes():
    """Edge case: if no restless rooms in the slot have features or keepsakes, all 6 evidence should be usable."""
    # Chapter 1 cases have no features and no keepsakes. "1-1" is a good candidate.
    case = cw.Case(progress.DATA["1-1"])
    for slot in range(case.n):
        result = case.usable(slot)
        expected = set(range(6))
        assert result == expected, f"slot {slot} should have all 6 evidence usable, got {result}"
