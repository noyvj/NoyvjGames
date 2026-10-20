"""Edge-case tests for bridge.py."""

from bridge import Stock, react, describe_stock


def test_stock_with_count_clamps_to_max():
    stock = Stock()
    new_stock = stock.with_count("thing", 10)
    assert new_stock.count("thing") == 7


def test_stock_with_count_clamps_to_min():
    stock = Stock()
    new_stock = stock.with_count("thing", -5)
    assert new_stock.count("thing") == 0


def test_stock_with_count_removes_on_zero():
    stock = Stock((("thing", 3),))
    new_stock = stock.with_count("thing", 0)
    assert new_stock.count("thing") == 0


def test_react_empty_message():
    reaction = react("", Stock())
    assert reaction.understood is False
    assert reaction.reason == "silence"


def test_react_unknown_noun():
    reaction = react("xyz", Stock())
    assert reaction.understood is False
    assert reaction.reason == "no_thing"


def test_describe_stock_empty():
    assert describe_stock(Stock()) == "The counter is empty."
