"""Tests for Stock.with_count() in bridge.py."""


from bridge import Stock


def test_with_count_updates_existing_item():
    stock = Stock((("ku", 2), ("t", 3)))
    after = stock.with_count("ku", 5)
    assert after.count("ku") == 5
    assert after.count("t") == 3
    assert len(after.items) == 2


def test_with_count_adds_new_item():
    stock = Stock((("ku", 2),))
    after = stock.with_count("t", 1)
    assert after.count("ku") == 2
    assert after.count("t") == 1
    assert len(after.items) == 2


def test_with_count_removes_item_when_count_becomes_zero():
    stock = Stock((("ku", 2),))
    after = stock.with_count("ku", 0)
    assert after.count("ku") == 0
    assert len(after.items) == 0
