"""Tests for shop.rules_from()."""

import shop


def test_rules_from_empty_owned_returns_empty_dict():
    assert shop.rules_from([]) == {}


def test_rules_from_all_upgrades_returns_all_rules():
    owned = ["scales", "broom", "tipjar"]
    rules = shop.rules_from(owned)
    assert rules == {"scales": True, "broom_refund": 1, "tip_pct": 40}


def test_rules_from_subset_returns_only_matching_rules():
    owned = ["broom", "tipjar"]
    rules = shop.rules_from(owned)
    assert rules == {"broom_refund": 1, "tip_pct": 40}


def test_rules_from_ignores_junk_in_owned_list():
    owned = ["scales", "junk_upgrade", 5]
    rules = shop.rules_from(owned)
    assert rules == {"scales": True}
