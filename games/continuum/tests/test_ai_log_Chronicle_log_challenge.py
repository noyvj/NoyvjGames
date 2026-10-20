"""Tests for Chronicle.log_challenge()."""

import log


def test_log_challenge_appends_a_challenge_entry():
    """Normal case: verifies that log_challenge creates a LogEntry with the correct kind and attributes."""
    chronicle = log.Chronicle()
    chronicle.log_challenge(season=5, era="tribal", text="The council has issued a new directive.")
    assert len(chronicle.entries) == 1
    entry = chronicle.entries[0]
    assert entry.season == 5
    assert entry.era == "tribal"
    assert entry.kind == "challenge"
    assert entry.text == "The council has issued a new directive."


def test_log_challenge_appends_multiple_entries_sequentially():
    """Normal case: verifies that repeated calls append entries in order."""
    chronicle = log.Chronicle()
    chronicle.log_challenge(season=1, era="tribal", text="First challenge.")
    chronicle.log_challenge(season=2, era="tribal", text="Second challenge.")
    assert len(chronicle.entries) == 2
    assert chronicle.entries[0].text == "First challenge."
    assert chronicle.entries[1].text == "Second challenge."


def test_log_challenge_handles_empty_text():
    """Edge case: verifies that an empty string for text is still appended without error."""
    chronicle = log.Chronicle()
    chronicle.log_challenge(season=3, era="agrarian", text="")
    assert len(chronicle.entries) == 1
    entry = chronicle.entries[0]
    assert entry.kind == "challenge"
    assert entry.text == ""
