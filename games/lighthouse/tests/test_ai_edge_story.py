"""Edge-case tests for story.py public functions."""


from state import Keep
import lore
import story
from data import SUPPLY_CAP


def test_label_ship_limits():
    """Tests label_ship with quiet mode off, sailor unknown, and sailor known."""
    k = Keep(1)
    real_sid = lore.SAILOR_ORDER[0]

    # Quiet mode or unknown sailor returns plain text
    k.quiet = True
    assert story.label_ship(k, {"id": "s1", "who": None}, "Ship") == "Ship"

    k.quiet = False
    k.story["met"] = {}
    assert story.label_ship(k, {"id": "s1", "who": "unknown_sailor"}, "Ship") == "Ship"

    # Known sailor includes name
    k.story["met"][real_sid] = 1
    expected = "%s (%s)" % ("Ship", story.sailor_name(real_sid))
    assert story.label_ship(k, {"id": "s1", "who": real_sid}, "Ship") == expected


def test_delivered_ids_limits():
    """Tests delivered_ids with empty inbox and populated inbox."""
    k = Keep(1)
    assert story.delivered_ids(k) == []

    k.story["inbox"] = [{"id": "l1"}, {"id": "l2"}]
    assert story.delivered_ids(k) == ["l1", "l2"]


def test_lens_cloth_bonus_limits():
    """Tests lens_cloth_bonus with quiet mode, zero buff, and active buff."""
    k = Keep(1)
    k.story.setdefault("buffs", {})

    # Quiet mode disables bonus
    k.quiet = True
    k.story["buffs"]["lens_cloth"] = 5
    assert story.lens_cloth_bonus(k) == 0

    # Zero or missing buff returns zero
    k.quiet = False
    k.story["buffs"]["lens_cloth"] = 0
    assert story.lens_cloth_bonus(k) == 0

    # Active buff returns one
    k.story["buffs"]["lens_cloth"] = 1
    assert story.lens_cloth_bonus(k) == 1


def test_eerie_defaults_and_explicit_values():
    """Tests eerie() fallback to True and explicit False."""
    k = Keep(1)

    # Missing attribute defaults to True
    if hasattr(k, "_eerie"):
        delattr(k, "_eerie")
    assert story.eerie(k) is True

    # Explicit False overrides default
    k._eerie = False
    assert story.eerie(k) is False


def test_read_letter_rejects_invalid_inputs():
    """Tests read_letter rejecting unknown letters and already-read letters."""
    k = Keep(1)

    # Unknown letter ID (inbox is empty, so it's not delivered)
    ok, msg = story.read_letter(k, "nonexistent")
    assert ok is False
    assert "no such letter" in msg.lower()

    # Already read letter (must be in inbox to pass the first check)
    real_lid = lore.LETTER_ORDER[0]
    k.story["inbox"] = [{"id": real_lid}]
    k.story["read"] = [real_lid]
    ok, msg = story.read_letter(k, real_lid)
    assert ok is False
    assert "read that one" in msg.lower()


def test_take_gift_clamps_supplies_to_cap():
    """Tests take_gift clamping food supplies to SUPPLY_CAP."""
    k = Keep(1)

    # Find a gift with a food effect
    food_gift_id = None
    for gid, g in lore.GIFTS.items():
        if "food" in g.get("effect", {}):
            food_gift_id = gid
            break
    assert food_gift_id is not None, "Expected at least one gift with food effect"

    # Set supplies above cap and apply gift
    k.supplies["food"] = SUPPLY_CAP + 10
    story.take_gift(k, food_gift_id)

    assert k.supplies["food"] == SUPPLY_CAP
    assert food_gift_id in k.story["gifts"]
