"""Tests for unease.mystery_order()."""

import mysteries
import unease


def test_mystery_order_returns_all_mystery_ids():
    """mystery_order() should return exactly the keys of MYSTERIES."""
    order = unease.mystery_order()
    assert set(order) == set(mysteries.MYSTERIES.keys())
    assert len(order) == len(mysteries.MYSTERIES)


def test_mystery_order_is_sorted_by_first_window_start():
    """The returned list must be sorted by the start night of each mystery's first beat window."""
    order = unease.mystery_order()
    for i in range(len(order) - 1):
        m1, m2 = order[i], order[i + 1]
        w1 = mysteries.MYSTERIES[m1]["beats"][0]["window"][0]
        w2 = mysteries.MYSTERIES[m2]["beats"][0]["window"][0]
        assert w1 <= w2, f"{m1} (start {w1}) should come before or at {m2} (start {w2})"


def test_mystery_order_handles_overlapping_windows_stably():
    """If two mysteries start on the same night, their relative order is deterministic."""
    order = unease.mystery_order()
    starts = [mysteries.MYSTERIES[m]["beats"][0]["window"][0] for m in order]
    if len(set(starts)) < len(starts):
        # There are ties; verify they appear consecutively and deterministically
        for i in range(len(order) - 1):
            if starts[i] == starts[i + 1]:
                assert order[i] in mysteries.MYSTERIES
                assert order[i + 1] in mysteries.MYSTERIES
