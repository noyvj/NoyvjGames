"""Tests for the next_item() function in hints.py."""

import hints
import cases


def test_next_item_returns_first_unseen_item_from_shortest_path():
    """next_item() returns the first item in the case's shortest path that hasn't been seen yet."""
    case = cases.BY_ID["latch"]
    seen = set()
    result = hints.next_item(case, seen)
    assert result == case.shortest[0]


def test_next_item_skips_seen_items_and_returns_next_unseen():
    """next_item() skips items that have been seen and returns the next unseen item."""
    case = cases.BY_ID["latch"]
    seen = {case.shortest[0]}
    result = hints.next_item(case, seen)
    assert result == case.shortest[1]


def test_next_item_returns_none_when_all_shortest_path_items_are_seen():
    """next_item() returns None when all items in the shortest path have been seen."""
    case = cases.BY_ID["latch"]
    seen = set(case.shortest)
    result = hints.next_item(case, seen)
    assert result is None


def test_next_item_works_with_different_case_types():
    """next_item() works correctly with cases from different domains (numbers, shapes, grids)."""
    # Test with a number case
    num_case = cases.BY_ID["latch"]
    seen = set()
    result = hints.next_item(num_case, seen)
    assert result in num_case.shortest

    # Test with a shape case
    shape_case = cases.BY_ID["hinge"]
    seen = set()
    result = hints.next_item(shape_case, seen)
    assert result in shape_case.shortest

    # Test with a grid case
    grid_case = cases.BY_ID["pane"]
    seen = set()
    result = hints.next_item(grid_case, seen)
    assert result in grid_case.shortest
