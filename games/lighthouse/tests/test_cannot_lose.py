"""The keeper cannot die or lose: from any state the night, the morning, the day and the evening all lead on, the
numbers stay in range, and the cheapest or laziest play never reaches a dead end."""

import clock
import data
import day
import harness
import sim
from state import Keep


def check_bounds(k):
    assert 0 <= k.oil <= data.OIL_CAP_BIG
    assert 0 <= k.energy <= data.ENERGY_MAX
    assert all(0 <= v <= 100 for v in k.structure.values())
    assert all(0 <= k.supplies[s] <= data.SUPPLY_CAP for s in data.SUPPLIES)
    assert k.reputation >= 0 and k.salvage >= 0 and 0 <= k.comfort <= data.COMFORT_MAX
    assert len(k.waiting) <= 6 and len(k.log) <= data.LOG_KEEP


def worst_play(k, nights):
    """Spend nothing, repair nothing, never wind, never buy: the worst keeper there could be."""
    for _ in range(nights):
        assert k.phase == "evening"
        k.levels = [0, 0, 0]
        k.tasks = {"wind": False, "watch": False, "repair": False}
        before = k.night
        sim.begin_night(k)
        sim.step(k, 10 ** 6)
        assert k.phase == "morning" and k.report
        check_bounds(k)
        day.end_morning(k)
        if k.phase == "yearend":
            day.continue_endless(k)
        assert k.phase == "day"
        day.end_day(k)
        assert k.night == before + 1
    return k


def test_a_thousand_seeds_of_the_worst_play_still_reach_the_next_morning():
    for seed in range(1, 1001):
        k = Keep(seed)
        sim.to_evening(k)
        worst_play(k, 4)
        assert k.meta["nights_kept"] == 4


def test_a_few_years_of_neglect_never_dead_ends_and_stays_in_bounds():
    for seed in (1, 2, 3):
        k = Keep(seed)
        sim.to_evening(k)
        worst_play(k, 130)
        assert k.night == 131 and clock.year_of(k.night) == 4
        assert k.structure and k.meta["years"] == 3


def test_an_empty_tank_and_empty_stores_still_light_the_lamp():
    k = Keep(4)
    k.oil = 0.0
    k.supplies = {s: 0 for s in data.SUPPLIES}
    k.structure = {p: 0 for p in data.PARTS}
    k.energy = 0.0
    sim.to_evening(k)
    assert k.oil == data.EMERGENCY_OIL
    sim.begin_night(k)
    sim.step(k, 10 ** 6)
    assert k.phase == "morning"
    check_bounds(k)
    day.end_morning(k)
    for task in (day.rest, day.tidy, day.beachcomb):
        task(k)
    assert day.end_day(k)


def test_hunger_costs_energy_once_and_never_blocks_the_light():
    k = Keep(4)
    k.supplies["food"] = 0
    sim.to_evening(k)
    sim.begin_night(k)
    sim.step(k, 10 ** 6)
    assert k.hungry
    day.end_morning(k)
    day.end_day(k)
    assert not k.hungry and k.phase == "evening"


def test_the_harness_policies_all_play_a_year_and_the_careful_one_does_well():
    results = {}
    for style in ("idle", "miser", "careful"):
        k = Keep(11)
        sim.to_evening(k)
        harness.play(k, 40, style)
        check_bounds(k)
        results[style] = k
        assert k.meta["nights_kept"] == 40 and k.phase in ("yearend", "evening", "day")
    careful, miser = results["careful"], results["miser"]
    assert careful.meta["ships_passed"] > miser.meta["ships_passed"]
    assert careful.meta["ships_passed"] >= 0.8 * (careful.meta["ships_passed"] + careful.meta["ships_delayed"] + careful.meta["ships_damaged"])
    assert careful.reputation > miser.reputation


def test_every_phase_has_a_way_forward():
    k = Keep(5)
    sim.to_evening(k)
    seen = []
    for _ in range(400):
        seen.append(k.phase)
        if k.phase == "evening":
            sim.begin_night(k)
        elif k.phase == "night":
            sim.step(k, 10 ** 6)
        elif k.phase == "morning":
            day.end_morning(k)
        elif k.phase == "yearend":
            day.continue_endless(k)
        elif k.phase == "day":
            day.end_day(k)
    assert set(seen) == {"evening", "night", "morning", "day", "yearend"}
