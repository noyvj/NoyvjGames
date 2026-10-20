from orders import Customer


def C(items, arch="regular", patience=30, name="Tomas"):
    return Customer(name, arch, [[f, t, 0] for f, t in items], patience)


def test_wanted_returns_all_items_when_none_are_done():
    """Normal case: all items are pending."""
    c = C([("produce", 2), ("textiles", 1)])
    assert c.wanted() == [("produce", 2), ("textiles", 1)]


def test_wanted_filters_out_done_items():
    """Normal case: some items are already handed over."""
    c = C([("produce", 2), ("ceramics", 3)])
    c.items[0][2] = 1
    assert c.wanted() == [("ceramics", 3)]


def test_wanted_returns_empty_list_when_all_items_are_done():
    """Edge case: no items are pending."""
    c = C([("produce", 1)])
    c.items[0][2] = 1
    assert c.wanted() == []
