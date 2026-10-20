"""Tests for Keep.add_log() in state.py."""

from state import Keep
from data import LOG_KEEP


def test_add_log_appends_entry_with_current_tick_and_truncated_line():
    k = Keep(1)
    k.tick = 42
    k.add_log("ship", "A ship passes safely")
    assert len(k.log) == 1
    entry = k.log[0]
    assert entry[0] == 42
    assert entry[1] == "ship"
    assert entry[2] == "A ship passes safely"


def test_add_log_truncates_long_lines():
    k = Keep(1)
    long_line = "x" * 1000
    k.add_log("note", long_line)
    assert len(k.log) == 1
    assert len(k.log[0][2]) == 900


def test_add_log_truncates_oldest_entries_when_exceeding_limit():
    k = Keep(1)
    # Fill log up to limit
    for i in range(LOG_KEEP):
        k.add_log("note", f"entry {i}")
    assert len(k.log) == LOG_KEEP

    # Add one more
    k.add_log("note", "overflow entry")
    assert len(k.log) == LOG_KEEP
    # Oldest should be gone, newest at the end
    assert k.log[-1][2] == "overflow entry"
    assert k.log[0][2] != "entry 0"
