import lore
import data
import story
from state import Keep


def _find_gift(effect_key):
    for gid, g in lore.GIFTS.items():
        if g.get("effect", {}).get(effect_key) is not None:
            return gid
    raise ValueError(f"No gift with effect '{effect_key}' found")


def test_take_gift_adds_food_and_updates_state():
    """Normal case: a gift with food effect updates supplies, state, and returns the correct message."""
    k = Keep(1)
    gid = _find_gift("food")
    initial_food = k.supplies["food"]
    g = lore.GIFTS[gid]
    expected_food = min(data.SUPPLY_CAP, initial_food + g["effect"]["food"])

    msg = story.take_gift(k, gid)

    assert k.supplies["food"] == expected_food
    assert gid in k.story["gifts"]
    assert gid in k.meta["story"]["gifts"]
    assert f"(+{g['effect']['food']} food)" in msg


def test_take_gift_adds_lens_cloth_effect():
    """Normal case: a gift with lens_cloth effect updates buffs and returns the correct message."""
    k = Keep(1)
    gid = _find_gift("lens_cloth")
    expected_nights = lore.GIFTS[gid]["effect"]["lens_cloth"]

    msg = story.take_gift(k, gid)

    assert k.story["buffs"]["lens_cloth"] == expected_nights
    assert gid in k.story["gifts"]
    assert f"for {expected_nights} nights" in msg


def test_take_gift_caps_food_at_supply_cap():
    """Edge case: food supply is capped at SUPPLY_CAP even if the gift would exceed it."""
    k = Keep(1)
    k.supplies["food"] = data.SUPPLY_CAP - 1
    gid = _find_gift("food")
    lore.GIFTS[gid]

    story.take_gift(k, gid)

    assert k.supplies["food"] == data.SUPPLY_CAP
