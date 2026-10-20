"""Tests for goods.is_wild()."""

import goods


def test_is_wild_returns_true_for_a_wildcard_good():
    assert goods.is_wild((goods.WILD, 1)) is True


def test_is_wild_returns_false_for_normal_goods():
    fam = goods.FAMILIES[0]
    assert goods.is_wild((fam, 2)) is False
    assert goods.is_wild((fam, 5)) is False


def test_is_wild_returns_false_for_none():
    assert goods.is_wild(None) is False
