"""Tests for the hint_view() function in hints.py."""

import hints
import cases
import lang


def test_hint_view_returns_next_item_from_shortest_path():
    """hint_view returns the first unseen item from the case's shortest path."""
    case = cases.BY_ID["latch"]
    seen = set()
    result = hints.hint_view(case, seen)
    assert result["item"] == case.shortest[0]
    assert result["text"] == "Try sending this one next. It is a good test: its answer rules a lot out."
    assert result["label"] == lang.item_words(case.kind, case.shortest[0])


def test_hint_view_skips_seen_items():
    """hint_view skips items that have already been seen."""
    case = cases.BY_ID["latch"]
    seen = {case.shortest[0]}
    result = hints.hint_view(case, seen)
    assert result["item"] == case.shortest[1]
    assert result["text"] == "Try sending this one next. It is a good test: its answer rules a lot out."
    assert result["label"] == lang.item_words(case.kind, case.shortest[1])


def test_hint_view_returns_empty_when_all_seen():
    """hint_view returns empty strings when all shortest-path items have been seen."""
    case = cases.BY_ID["latch"]
    seen = set(case.shortest)
    result = hints.hint_view(case, seen)
    assert result["item"] == ""
    assert result["label"] == ""
    assert "You have seen enough" in result["text"]
