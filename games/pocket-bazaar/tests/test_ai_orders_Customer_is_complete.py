

from orders import Customer


def C(items, arch="regular", patience=30, name="Tomas"):
    return Customer(name, arch, [[f, t, 0] for f, t in items], patience)


def test_all_items_complete_returns_true():
    """Normal case: every item is already handed over."""
    c = C([("produce", 2), ("textiles", 3)])
    for item in c.items:
        item[2] = 1
    assert c.is_complete() is True


def test_some_items_incomplete_returns_false():
    """Normal case: at least one item still needs to be handed over."""
    c = C([("produce", 2), ("textiles", 3)])
    c.items[0][2] = 1
    assert c.is_complete() is False


def test_all_items_incomplete_returns_false():
    """Normal case: no items have been handed over yet."""
    c = C([("produce", 2), ("textiles", 3)])
    assert c.is_complete() is False


def test_single_item_done_returns_true():
    """Edge case: a single-item order that is complete."""
    c = C([("ceramics", 1)])
    c.items[0][2] = 1
    assert c.is_complete() is True
