"""Tests for the codex.summary() function."""

import codex


def test_summary_marks_filled_when_case_is_named():
    """summary() marks a case as filled when it's in the named dict."""
    named = {"latch": {"t": 0, "r": "even"}}
    read = set()
    summary = codex.summary(named, read)
    latch_entry = [e for e in summary if e["id"] == "latch"][0]
    assert latch_entry["filled"] is True
    hinge_entry = [e for e in summary if e["id"] == "hinge"][0]
    assert hinge_entry["filled"] is False


def test_summary_marks_read_when_case_is_both_named_and_read():
    """summary() marks a case as read only when it's both named and in read set."""
    named = {"latch": {"t": 0, "r": "even"}, "hinge": {"t": 1, "r": "odd"}}
    read = {"latch"}
    summary = codex.summary(named, read)
    latch_entry = [e for e in summary if e["id"] == "latch"][0]
    assert latch_entry["read"] is True
    hinge_entry = [e for e in summary if e["id"] == "hinge"][0]
    assert hinge_entry["read"] is False


def test_summary_handles_empty_named_and_read():
    """summary() works correctly with empty named and read collections."""
    named = {}
    read = set()
    summary = codex.summary(named, read)
    assert all(not e["filled"] and not e["read"] for e in summary)
