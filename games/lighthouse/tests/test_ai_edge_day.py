"""Edge-case tests for day.py public functions."""

import data
import day
import re
import sim
from state import Keep


def keep_at(night=1, seed=3, phase="day"):
    k = Keep(seed)
    k.night = night
    sim.to_evening(k)
    k.phase = phase
    if phase == "day":
        k.day_slots = 5
    return k


def test_set_order_rejects_invalid_types_and_sums():
    k = keep_at(1)
    # Empty dict should fail sum check
    ok, _ = day.set_order(k, {})
    assert not ok
    # All zeros should fail sum check
    ok, _ = day.set_order(k, {"oil": 0, "food": 0, "timber": 0, "tar": 0, "glass": 0})
    assert not ok
    # Negative values should be rejected
    ok, _ = day.set_order(k, {"oil": -1, "food": 0, "timber": 0, "tar": 0, "glass": 13})
    assert not ok
    # Non-integer values should be rejected
    ok, _ = day.set_order(k, {"oil": 1.5, "food": 0, "timber": 0, "tar": 0, "glass": 10.5})
    assert not ok
    # Correct order at max capacity for one crate
    ok, msg = day.set_order(k, {"oil": 12, "food": 0, "timber": 0, "tar": 0, "glass": 0})
    assert ok and msg == "Order sent ashore."


def test_repair_handles_maxed_parts_and_missing_supplies():
    k = keep_at(1)
    # Largest allowed structure value (100) should be rejected
    k.structure["tower"] = 100
    ok, msg = day.repair(k, "tower")
    assert not ok and "already sound" in msg.lower()

    # Missing supplies should be rejected
    k.structure["tower"] = 50  # Reset to allow repair check
    k.supplies = {"oil": 0, "food": 0, "timber": 0, "tar": 0, "glass": 0}
    ok, msg = day.repair(k, "tower")
    assert not ok and "need more" in msg.lower()


def test_rest_clamps_energy_to_max():
    k = keep_at(1)
    # Energy just below max should clamp to max after rest
    k.energy = data.ENERGY_MAX - 0.5
    ok, _ = day.rest(k)
    assert ok and k.energy == float(data.ENERGY_MAX)


def test_tidy_clamps_comfort_to_max():
    k = keep_at(1)
    # Comfort at max should be rejected
    k.comfort = data.COMFORT_MAX
    ok, msg = day.tidy(k)
    assert not ok and "could not be cosier" in msg.lower()
    # Comfort just below max should clamp to max after tidy
    k.comfort = data.COMFORT_MAX - 1
    ok, _ = day.tidy(k)
    assert ok and k.comfort == data.COMFORT_MAX


def test_beachcomb_clamps_supply_cap_and_respects_combed_flag():
    k = keep_at(1)
    # Supplies at max cap should clamp (not add) but still succeed
    for kind in ("timber", "tar", "glass", "food"):
        k.supplies[kind] = data.SUPPLY_CAP
    ok, msg = day.beachcomb(k)
    assert ok and "bring back some salvage" in msg.lower()
    # Second beachcomb on the same day should be rejected
    ok, msg = day.beachcomb(k)
    assert not ok and "already walked" in msg.lower()


def test_buy_upgrade_rejects_invalid_ids_and_insufficient_salvage():
    k = keep_at(1)
    # Invalid upgrade id should be rejected
    ok, msg = day.buy_upgrade(k, "nonexistent")
    assert not ok and "no such upgrade" in msg.lower()
    # Already bought upgrade should be rejected
    k.upgrades.append("lens")
    ok, msg = day.buy_upgrade(k, "lens")
    assert not ok and "already have that" in msg.lower()
    # Insufficient salvage should be rejected
    k.salvage = 0
    k.upgrades = []
    ok, msg = day.buy_upgrade(k, "lens")
    assert not ok and re.search(r"need \d+ salvage", msg.lower())
