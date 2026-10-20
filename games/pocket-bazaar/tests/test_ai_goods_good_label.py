"""Tests for goods.good_label()."""


import goods


def test_normal_tier_2_ceramics():
    """Tier 2 ceramics good returns its name and tier number."""
    assert goods.good_label(("ceramics", 2)) == "Cup (tier 2)"


def test_normal_tier_5_produce():
    """Tier 5 produce good returns its full name and tier number."""
    assert goods.good_label(("produce", 5)) == "Orchard basket (tier 5)"


def test_normal_tier_1_spices():
    """Tier 1 spices good returns its name and tier number."""
    assert goods.good_label(("spices", 1)) == "Bay leaf (tier 1)"


def test_edge_case_wildcard():
    """Wildcard good returns the fixed label 'Wildcard'."""
    assert goods.good_label((goods.WILD, 1)) == "Wildcard"
