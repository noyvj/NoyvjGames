"""Tests for describe_tray() in compound.py."""

from compound import Tray, Item, describe_tray


def test_describe_tray_empty():
    """Edge case: an empty tray returns the empty message."""
    tray = Tray(items=())
    assert describe_tray(tray) == "The tray is empty."


def test_describe_tray_single_item():
    """Normal case: a single item on the tray."""
    item = Item(root="water", size="small")
    tray = Tray(items=(item,))
    assert describe_tray(tray) == "On the tray: small water."


def test_describe_tray_multiple_items():
    """Normal case: multiple items on the tray are comma-separated."""
    items = (Item(root="fire", size="big"), Item(root="grain", size="small"))
    tray = Tray(items=items)
    assert describe_tray(tray) == "On the tray: big fire, small grain."
