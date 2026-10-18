"""Tests for Case.stock_of()."""

import cases
from shift import Case


def test_stock_of_returns_initial_count_for_item_on_shelf():
    """Normal case: item is on the shelf, returns its initial stock from the authored data."""
    d = cases.ALL[0]
    c = Case(d)
    st = c.new_state()
    # Pick the first item on the shelf
    item = c.items[0]
    assert c.stock_of(st, item) == d["stock"][item]


def test_stock_of_returns_initial_count_for_another_item():
    """Normal case: a different item on the shelf returns its own count."""
    # Find a shift with at least two items to test a second index
    for d in cases.ALL:
        c = Case(d)
        if len(c.items) >= 2:
            st = c.new_state()
            item = c.items[1]
            assert c.stock_of(st, item) == d["stock"][item]
            break


def test_stock_of_returns_zero_for_item_not_on_shelf():
    """Edge case: item is not in this shift's shelf, returns 0."""
    d = cases.ALL[0]
    c = Case(d)
    st = c.new_state()
    fake_item = "nonexistent_supply"
    assert c.stock_of(st, fake_item) == 0
