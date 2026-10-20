"""Tests for goods.good_name()."""

import goods


def test_good_name_returns_correct_name_for_produce_tier_1():
    assert goods.good_name(("produce", 1)) == "Berry"


def test_good_name_returns_correct_name_for_textiles_tier_3():
    assert goods.good_name(("textiles", 3)) == "Scarf"


def test_good_name_handles_wildcard_edge_case():
    assert goods.good_name((goods.WILD, 1)) == "Wildcard"
