"""Tests for optics.placed_from()."""

import optics


def test_placed_from_returns_a_dict_with_tuple_keys_and_values():
    # Normal case: multiple pieces on a bench layout, built like test_solver.py
    slots = [(0, 1), (2, 3)]
    combo = [("mirror", 0), ("splitter", 1)]
    layout = {cell: x for cell, x in zip(slots, combo)}
    result = optics.placed_from(layout)
    assert isinstance(result, dict)
    assert result == {(0, 1): ("mirror", 0), (2, 3): ("splitter", 1)}
    for k in result:
        assert isinstance(k, tuple)


def test_placed_from_handles_a_single_piece():
    # Normal case: one piece placed
    layout = {(3, 4): ("prism", 0)}
    result = optics.placed_from(layout)
    assert result == {(3, 4): ("prism", 0)}


def test_placed_from_returns_an_empty_dict_for_empty_input():
    # Edge case: no pieces placed
    layout = {}
    result = optics.placed_from(layout)
    assert result == {}
