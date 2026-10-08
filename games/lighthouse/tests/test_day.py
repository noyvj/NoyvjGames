"""The day: five tasks of daylight, repairs that spend supplies, upgrades paid in salvage, the boat order, and
the turn of the evening."""

import clock
import data
import day
import sim
from state import Keep


def morning_keep(seed=1, night=20):
    k = Keep(seed)
    k.night = night
    sim.to_evening(k)
    sim.begin_night(k)
    sim.step(k, 10 ** 6)
    day.end_morning(k)
    return k


def test_the_morning_leads_to_five_slots_of_daylight():
    k = morning_keep()
    assert k.phase == "day" and k.day_slots == data.DAY_SLOTS
    assert day.end_morning(k) is False
    assert day.end_day(k) is True and k.phase == "evening" and k.night == 21 and k.day_slots == 0


def test_a_repair_mends_spends_supplies_and_uses_a_slot():
    k = morning_keep()
    k.structure["tower"] = 30
    k.supplies.update(timber=3, tar=3)
    ok, text = day.repair(k, "tower")
    assert ok and k.structure["tower"] == 65 and k.supplies["timber"] == 2 and k.supplies["tar"] == 2 and k.day_slots == 4
    assert "tower" in text
    k.structure["dock"] = 100
    ok, text = day.repair(k, "dock")
    assert not ok and "sound" in text and k.day_slots == 4


def test_a_repair_without_supplies_is_refused_and_costs_nothing():
    k = morning_keep()
    k.structure["lantern"] = 20
    k.supplies["glass"] = 1
    energy, slots = k.energy, k.day_slots
    ok, text = day.repair(k, "lantern")
    assert not ok and "glass" in text and k.energy == energy and k.day_slots == slots and k.structure["lantern"] == 20


def test_a_tired_keeper_mends_half_as_much():
    k = morning_keep()
    k.structure["rail"] = 20
    k.energy = 5.0
    k.supplies["timber"] = 4
    assert day.repair(k, "rail")[0] and k.structure["rail"] == 20 + data.DAY_REPAIR_HEAL // 2


def test_daylight_runs_out():
    k = morning_keep()
    for _ in range(data.DAY_SLOTS):
        assert day.tidy(k)[0] or day.rest(k)[0]
    ok, text = day.rest(k)
    assert not ok and "daylight" in text
    assert not day.repair(k, "tower")[0]


def test_rest_tidy_and_comfort():
    k = morning_keep()
    k.energy = 40.0
    assert day.rest(k)[0] and k.energy == 70
    assert day.tidy(k)[0] and k.comfort == 1
    assert day.rest(k)[0] and k.energy == 99          # 68 + 30 + 1 comfort, under the cap of 100
    k.comfort = data.COMFORT_MAX
    assert not day.tidy(k)[0]


def test_beachcombing_is_once_a_day_and_always_pays_a_salvage():
    k = morning_keep()
    s = k.salvage
    assert day.beachcomb(k)[0] and k.salvage == s + 1
    ok, text = day.beachcomb(k)
    assert not ok and "already" in text and k.day_slots == data.DAY_SLOTS - 1
    day.end_day(k)
    k.phase = "day"
    k.day_slots = 5
    k.combed = False
    assert day.beachcomb(k)[0]


def test_the_greenhouse_box_grows_food_only_once_built():
    k = morning_keep()
    assert not day.garden(k)[0]
    k.upgrades.append("greenhouse")
    f = k.supplies["food"]
    assert day.garden(k)[0] and k.supplies["food"] == f + 2


def test_helping_a_damaged_ship_is_rewarded_and_the_small_boat_makes_it_cheaper():
    k = morning_keep()
    k.waiting.append({"id": "9-1", "kind": "fisher", "name": "Brave Wren"})
    k.supplies.update(timber=1, tar=0)
    assert not day.rescue(k, "9-1")[0]
    k.supplies["tar"] = 1
    rep = k.reputation
    ok, text = day.rescue(k, "9-1")
    assert ok and k.reputation == rep + 2 and k.waiting == [] and k.meta["rescues"] == 1 and "Brave Wren" in text
    assert not day.rescue(k, "9-1")[0]
    k.waiting.append({"id": "9-2", "kind": "cargo", "name": "Old Keel"})
    k.upgrades.append("boat")
    k.supplies.update(timber=1, tar=0)
    assert day.rescue(k, "9-2")[0]


def test_tidy_achievement_counter_counts_a_day_of_five_repairs_once():
    k = morning_keep()
    k.structure = {p: 10 for p in data.PARTS}
    k.supplies = {"food": 6, "tar": 20, "glass": 20, "timber": 20}
    for part in data.PARTS:
        assert day.repair(k, part)[0]
    assert k.meta["counters"]["tidy_days"] == 1
    k.structure["tower"] = 10
    k.day_slots = 3
    day.repair(k, "tower")
    assert k.meta["counters"]["tidy_days"] == 1


def test_upgrades_cost_salvage_and_apply_once():
    k = morning_keep()
    k.salvage = 5
    ok, text = day.buy_upgrade(k, "lens")
    assert not ok and "8 salvage" in text and k.upgrades == []
    k.salvage = 20
    assert day.buy_upgrade(k, "lens")[0] and k.salvage == 12 and k.upgrades == ["lens"]
    assert not day.buy_upgrade(k, "lens")[0]
    assert not day.buy_upgrade(k, "warp")[0]
    k.phase = "night"
    assert not day.buy_upgrade(k, "wick")[0]
    assert {u["id"] for u in data.UPGRADES} == set(data.UPGRADE_IDS) and len(data.UPGRADES) == 9


def test_the_bigger_cistern_holds_more_oil_and_the_boat_fills_it():
    k = morning_keep()
    k.upgrades.append("cistern")
    assert k.oil_cap() == data.OIL_CAP_BIG
    k.oil = 10.0
    k.order = {"oil": 12, "food": 0, "timber": 0, "tar": 0, "glass": 0}
    d = sim.deliver(k)
    assert k.oil == min(10 + 12 * 40, data.OIL_CAP_BIG) and d["items"]["oil"] == 270


def test_the_order_must_add_up_to_the_boat_and_changes_what_arrives():
    k = morning_keep()
    assert not day.set_order(k, {"oil": 1, "food": 1, "timber": 1, "tar": 1, "glass": 1})[0]
    assert not day.set_order(k, {"oil": 6.5, "food": 0, "timber": 0, "tar": 0, "glass": 5.5})[0]
    assert not day.set_order(k, {"oil": -1, "food": 13, "timber": 0, "tar": 0, "glass": 0})[0]
    assert day.set_order(k, {"oil": 2, "food": 2, "timber": 4, "tar": 2, "glass": 2})[0]
    k.oil, k.supplies = 0.0, {"food": 0, "tar": 0, "glass": 0, "timber": 0}
    sim.deliver(k)
    assert k.oil == 80 and k.supplies == {"food": 6, "tar": 4, "glass": 2, "timber": 8}


def test_the_year_ends_after_forty_nights_then_the_light_runs_on_endlessly():
    k = Keep(2)
    sim.to_evening(k)
    assert k.mode == "year"
    for _ in range(data.NIGHTS_PER_YEAR):
        k.oil = 150.0
        sim.begin_night(k)
        sim.step(k, 10 ** 6)
        if clock.year_night(k.night) == data.NIGHTS_PER_YEAR:
            break
        day.end_morning(k)
        day.end_day(k)
    assert k.night == 40 and k.phase == "morning"
    assert day.end_morning(k) and k.phase == "yearend" and k.meta["years"] == 1
    assert not day.end_day(k)                                 # the year-end screen has to be answered
    assert day.continue_endless(k) and k.mode == "endless" and k.phase == "day"
    assert day.end_day(k) and k.night == 41 and clock.year_of(k.night) == 2
