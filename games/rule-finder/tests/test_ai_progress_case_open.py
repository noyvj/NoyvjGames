"""Tests for the progress.case_open() function."""

import cases
import progress


def test_case_open_returns_true_for_existing_case():
    """case_open() returns True for a case ID present in cases.BY_ID."""
    real_id = cases.ALL_CASES[0].id
    assert progress.case_open(real_id) is True


def test_case_open_returns_false_for_nonexistent_case():
    """case_open() returns False for a case ID not in cases.BY_ID."""
    fake_id = "nonexistent-case"
    assert progress.case_open(fake_id) is False


def test_case_open_edge_case_empty_string():
    """case_open() handles an empty string correctly (returns False)."""
    assert progress.case_open("") is False
