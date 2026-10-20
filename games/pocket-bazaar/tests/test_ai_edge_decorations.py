"""Pocket Bazaar -- edge-case tests for decorations.py."""


import decorations


def test_ids_returns_all_decoration_ids():
    """ids() should return exactly the IDs from DECORATIONS, no more, no less."""
    ids = decorations.ids()
    assert len(ids) == 40
    assert set(ids) == {d[0] for d in decorations.DECORATIONS}


def test_view_with_empty_state():
    """view() with empty owned, put, and zero coins should return slots with no affordable items."""
    result = decorations.view([], {}, 0)
    assert len(result) == len(decorations.SLOTS)
    for slot_data in result:
        assert slot_data["put"] is None
        for item in slot_data["items"]:
            assert item["owned"] is False
            assert item["affordable"] is False


def test_view_handles_missing_put_keys():
    """view() should not crash when put dict lacks keys for all slots."""
    result = decorations.view([], {}, 1000)
    for slot_data in result:
        # .get(slot) returns None if key missing, which is valid
        assert slot_data["put"] is None or slot_data["put"] in [i["id"] for i in slot_data["items"]]


def test_can_buy_rejects_invalid_id():
    """can_buy() should reject decoration IDs that do not exist."""
    ok, msg = decorations.can_buy([], "nonexistent_decoration", 100)
    assert ok is False
    assert "no such" in msg.lower()


def test_can_buy_rejects_already_owned():
    """can_buy() should reject IDs the player already owns."""
    owned = ["awning_striped"]
    ok, msg = decorations.can_buy(owned, "awning_striped", 100)
    assert ok is False
    assert "already own" in msg.lower()


def test_can_buy_accepts_exact_coins():
    """can_buy() should accept the player when coins exactly match the cost."""
    decor_id = "sign_plain"
    cost = decorations.BY_ID[decor_id][3]
    ok, msg = decorations.can_buy([], decor_id, cost)
    assert ok is True
    assert msg == ""


def test_can_buy_rejects_insufficient_coins():
    """can_buy() should reject the player when coins are less than the cost."""
    decor_id = "sign_plain"
    cost = decorations.BY_ID[decor_id][3]
    ok, msg = decorations.can_buy([], decor_id, cost - 1)
    assert ok is False
    assert f"That costs {cost} coins and you have {cost - 1}" in msg


def test_can_buy_handles_negative_coins():
    """can_buy() should handle negative coin values gracefully."""
    ok, msg = decorations.can_buy([], "sign_plain", -5)
    assert ok is False
