import shop


def test_ids_returns_all_upgrade_ids():
    """ids() should return exactly the list of upgrade IDs defined in UPGRADES."""
    ids = shop.ids()
    assert len(ids) == 6
    assert set(ids) == {"preview", "broom", "tipjar", "shelf", "scales", "counter"}


def test_view_with_zero_and_negative_coins():
    """view() should mark all upgrades as unaffordable when coins are zero or negative."""
    v = shop.view([], 0)
    assert all(not item["affordable"] for item in v)
    assert all(item["owned"] is False for item in v)

    v_neg = shop.view([], -10)
    assert all(not item["affordable"] for item in v_neg)


def test_view_with_large_coins_and_owned_flags():
    """view() should mark upgrades as affordable with large coins, and correctly flag owned items."""
    max_cost = max(u["cost"] for u in shop.UPGRADES)
    v = shop.view(["broom"], max_cost + 1000)
    assert all(item["affordable"] for item in v)
    assert any(item["owned"] and item["id"] == "broom" for item in v)
    assert not any(item["owned"] and item["id"] != "broom" for item in v)


def test_can_buy_rejects_invalid_upgrade_ids():
    """can_buy() should reject None, wrong types, and missing keys."""
    assert shop.can_buy([], None, 100) == (False, "There is no such upgrade.")
    assert shop.can_buy([], 123, 100) == (False, "There is no such upgrade.")
    assert shop.can_buy([], "missing_key", 100) == (False, "There is no such upgrade.")


def test_can_buy_edge_cases_for_coins_and_owned():
    """can_buy() should handle exact cost, just below, just above, negative coins, and junk in owned."""
    # Exact cost
    assert shop.can_buy([], "broom", 120) == (True, "")
    # Just below
    assert shop.can_buy([], "broom", 119) == (False, "That costs 120 coins and you have 119.")
    # Just above
    assert shop.can_buy([], "broom", 121) == (True, "")
    # Negative coins
    assert shop.can_buy([], "broom", -5) == (False, "That costs 120 coins and you have -5.")
    # Already owned
    assert shop.can_buy(["broom"], "broom", 999) == (False, "You already have that.")
    # Junk in owned list should not affect check for other upgrades
    assert shop.can_buy(["junk", 123], "preview", 150) == (True, "")


def test_rules_from_empty_and_full_ownership():
    """rules_from() should return empty dict for no upgrades, and all rules when owned."""
    assert shop.rules_from([]) == {}

    full_owned = ["scales", "broom", "tipjar"]
    rules = shop.rules_from(full_owned)
    assert rules["scales"] is True
    assert rules["broom_refund"] == 1
    assert rules["tip_pct"] == 40

    # Junk in owned list should be ignored
    junk_rules = shop.rules_from(["scales", "broom", "tipjar", "nonexistent"])
    assert junk_rules == rules
