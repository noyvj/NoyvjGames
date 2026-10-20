from bridge import Stock, describe_stock


def test_empty_stock():
    """describe_stock returns the empty message for an empty stock."""
    stock = Stock()
    assert describe_stock(stock) == "The counter is empty."


def test_single_item_stock():
    """describe_stock describes a stock with one item correctly."""
    stock = Stock(((("water", 3),)))
    assert describe_stock(stock) == "On the counter: 3 water."


def test_multiple_items_stock():
    """describe_stock describes a stock with multiple items correctly."""
    stock = Stock((("water", 2), ("fire", 5), ("grain", 1)))
    assert describe_stock(stock) == "On the counter: 2 water, 5 fire, 1 grain."
