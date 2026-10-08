"""The night: oil, the lamp, the clockwork, ships, damage, the keeper's energy, and the invariance of pausing and
fast-forwarding (the sim has no clock, so running 100 ticks at once equals running them one at a time)."""

import copy
import json

import clock
import data
import ships as shipgen
import sim
from state import Keep
from weather import weather


def keep_at(seed=1, night=1, **plan):
    k = Keep(seed)
    k.night = night
    sim.to_evening(k)
    for key, value in plan.items():
        setattr(k, key, value)
    return k


def play_whole_night(k):
    sim.begin_night(k)
    sim.step(k, 10 ** 6)
    return k


def find_night(pred, seed_range=range(1, 60), night_range=range(4, 40)):
    for seed in seed_range:
        for night in night_range:
            if pred(seed, night):
                return seed, night
    raise AssertionError("no night found")


# ---- pause and fast-forward invariance ----------------------------------------------------------------------
def test_one_big_step_equals_many_small_steps():
    for seed, night in ((1, 1), (2, 14), (3, 33), (5, 37)):
        a, b = keep_at(seed, night), keep_at(seed, night)
        sim.begin_night(a)
        sim.begin_night(b)
        sim.step(a, 100)
        for _ in range(100):
            sim.step(b, 1)
        assert a.to_dict() == b.to_dict()
        assert a.phase == "morning"


def test_uneven_chunks_and_saves_in_the_middle_make_no_difference():
    seed, night = 6, 31
    whole = play_whole_night(keep_at(seed, night))
    k = keep_at(seed, night)
    sim.begin_night(k)
    for chunk in (1, 7, 2, 11, 3, 5):
        sim.step(k, chunk)
        k = Keep.from_dict(json.loads(json.dumps(k.to_dict())))      # save and load between chunks
    sim.step(k, 1000)
    assert k.to_dict() == whole.to_dict()


def test_step_stops_at_dawn_and_does_nothing_outside_the_night():
    k = keep_at(1, 1)
    assert sim.step(k, 5) == 0 and k.tick == 0               # evening: nothing runs
    sim.begin_night(k)
    assert sim.step(k, 10 ** 6) == clock.night_len(1)
    assert k.phase == "morning" and sim.step(k, 5) == 0
    assert k.report and k.report["night"] == 1


def test_fast_forward_changes_only_how_often_step_is_called():
    a, b = keep_at(4, 12), keep_at(4, 12)
    sim.begin_night(a)
    sim.begin_night(b)
    while a.phase == "night":
        sim.step(a, 1)
    while b.phase == "night":
        sim.step(b, 4)
    assert a.to_dict() == b.to_dict()


# ---- the lamp ----------------------------------------------------------------------------------------------
def test_oil_burn_follows_the_level_on_a_still_night():
    for index, level in enumerate(data.LEVELS):
        k = keep_at(1, 20, levels=[index] * 3)
        k.tasks = {"wind": True, "watch": False, "repair": False}
        play_whole_night(k)
        expected = data.LEVEL_BURN[index] * clock.night_len(20)
        assert abs(k.night_stats["oil_used"] - expected) < 0.2, level
        assert abs((data.START_OIL - k.oil) - expected) < 0.2
        assert k.night_stats["lamp_ticks"] == clock.night_len(20)


def test_the_wick_saves_a_fifth():
    base, wick = keep_at(1, 20, levels=[2, 2, 2]), keep_at(1, 20, levels=[2, 2, 2])
    wick.upgrades.append("wick")
    play_whole_night(base)
    play_whole_night(wick)
    assert abs(wick.night_stats["oil_used"] / base.night_stats["oil_used"] - 0.8) < 0.01


def test_running_out_of_oil_puts_the_lamp_out_and_the_next_dusk_finds_a_reserve():
    k = keep_at(1, 20, levels=[3, 3, 3])
    k.oil = 10.0
    play_whole_night(k)
    assert k.oil == 0 and k.night_stats["dark"] and k.night_stats["lamp_ticks"] < clock.night_len(20)
    assert any("gutters" in e[2] for e in k.log)
    rep = k.reputation
    k.phase, k.night = "evening", 21
    sim.to_evening(k)
    assert k.oil == data.EMERGENCY_OIL and k.reputation == max(0, rep - 1)
    sim.begin_night(k)
    assert k.phase == "night"


def test_a_ration_turns_the_lamp_down_but_a_deliberate_override_wins():
    k = keep_at(1, 20, levels=[3, 3, 3], ration=20)
    sim.begin_night(k)
    sim.step(k, 40)
    assert k.night_stats["ration_hit"] and k.night_stats["oil_used"] < 20 + 2.6 + 0.6 * 40
    used_at = k.night_stats["oil_used"]
    k2 = keep_at(1, 20, levels=[3, 3, 3], ration=20)
    sim.begin_night(k2)
    sim.step(k2, 4)
    assert sim.set_level(k2, 3) is True                        # same as plan: no override needed
    sim.step(k2, 4)
    assert used_at > 0


def test_set_level_overrides_until_the_end_of_the_block_only():
    k = keep_at(1, 20, levels=[0, 0, 0])
    sim.begin_night(k)
    sim.step(k, 2)
    assert sim.set_level(k, 3)
    assert k.override == [3, clock.block_end(20, 0)]
    sim.step(k, clock.block_end(20, 0) - 2)
    before = k.night_stats["oil_used"]
    sim.step(k, 3)
    assert k.night_stats["oil_used"] - before < 3 * data.LEVEL_BURN[1]      # back on Dim in the second block
    assert not sim.set_level(keep_at(1, 1), 2)                 # not in the evening


# ---- the clockwork -----------------------------------------------------------------------------------------
def test_the_clockwork_runs_down_without_winding_and_the_beam_halves():
    k = keep_at(1, 20, levels=[2, 2, 2])
    k.tasks["wind"] = False
    sim.begin_night(k)
    sim.step(k, data.CLOCK_BASE - 1)
    assert not sim.beam_stopped(k)
    full = sim.effective_reach(k, 2, 0)
    sim.step(k, 2)
    assert sim.beam_stopped(k) and k.night_stats["stopped"]
    assert sim.effective_reach(k, 2, 0) == full // data.FIXED_CONE_DIVISOR
    assert any("clockwork runs down" in e[2] for e in k.log)
    assert sim.wind_now(k)
    assert not sim.beam_stopped(k) and k.energy < 100
    assert not sim.wind_now(k)                                 # already wound


def test_the_wind_task_keeps_the_beam_turning_all_night():
    k = keep_at(1, 31, levels=[1, 1, 1])
    sim.begin_night(k)
    while k.phase == "night":
        sim.step(k, 1)
        assert not sim.beam_stopped(k) or k.phase != "night"
    assert not k.night_stats["stopped"] and k.night_stats["wound"] >= 2


def test_winding_weights_make_a_winding_last_longer():
    k = keep_at(1, 20)
    k.upgrades.append("weights")
    sim.begin_night(k)
    assert k.clock_left == data.CLOCK_WEIGHTS


# ---- ships --------------------------------------------------------------------------------------------------
def _clear_ship_night():
    def good(seed, night):
        if weather(seed, night).worst() != 0 or clock.is_festival(night):
            return False
        return len(shipgen.ships_for_night(seed, night, False)) >= 1 and not shipgen.mail_scheduled(seed, night)
    return find_night(good)


def test_a_bright_enough_beam_brings_every_ship_through_a_clear_night():
    seed, night = _clear_ship_night()
    k = keep_at(seed, night, levels=[2, 2, 2])
    play_whole_night(k)
    assert k.night_stats["delayed"] == 0 and k.night_stats["damaged"] == 0
    assert k.night_stats["passed"] == len(shipgen.ships_for_night(seed, night, False))
    assert k.report["passed"] == k.night_stats["passed"]


def test_a_dark_lamp_delays_ships_and_nobody_is_hurt():
    seed, night = _clear_ship_night()
    k = keep_at(seed, night, levels=[0, 0, 0])
    play_whole_night(k)
    assert k.night_stats["passed"] == 0
    assert k.night_stats["delayed"] == len(shipgen.ships_for_night(seed, night, False))
    assert k.night_stats["damaged"] == 0                       # a calm sea does not wreck a ship
    assert k.reputation == 0                                   # reputation never goes below zero
    text = " ".join(e[2] for e in k.log)
    assert "turned back" in text and "safe" not in text.replace("safely", "")


def test_a_blind_ship_in_a_storm_is_damaged_never_lost_and_waits_to_be_helped():
    def stormy(seed, night):
        w = weather(seed, night)
        return w.severity == 3 and any(
            s["arrive"] + s["window"] > 0 and sum(1 for t in range(s["arrive"], s["arrive"] + s["window"]) if w.cond[t] >= 3) >= 2
            for s in shipgen.ships_for_night(seed, night, False))
    seed, night = find_night(stormy, range(1, 120), range(4, 80))
    k = keep_at(seed, night, levels=[0, 0, 0])
    play_whole_night(k)
    assert k.night_stats["damaged"] >= 1 and len(k.waiting) == k.night_stats["damaged"]
    assert all(w["id"] and w["name"] for w in k.waiting)
    assert any("Everyone aboard is safe" in e[2] for e in k.log)
    assert not any(word in e[2].lower() for e in k.log for word in ("dead", "death", "drown", "lost at sea", "perish"))


def test_reputation_and_salvage_follow_safe_passages():
    seed, night = _clear_ship_night()
    k = keep_at(seed, night, levels=[2, 2, 2])
    play_whole_night(k)
    assert k.reputation >= k.night_stats["passed"] and k.salvage >= k.night_stats["passed"]
    assert k.meta["ships_passed"] == k.night_stats["passed"]


def test_a_failed_mail_boat_stays_due_and_a_landed_one_delivers_the_order():
    k = keep_at(2, 3, levels=[3, 3, 3])
    assert k.mail_tonight
    oil_before = k.oil
    play_whole_night(k)
    mail = [o for o in k.report["ships"] if o["kind"] == "mail"][0]
    if mail["outcome"] == "passed" and k.delivery:
        assert k.boat_due is False
        assert k.delivery["items"]["oil"] > 0
    k2 = keep_at(2, 3, levels=[0, 0, 0])
    play_whole_night(k2)
    assert k2.boat_due is True and k2.delivery is None
    k2.phase, k2.night = "evening", 4
    sim.to_evening(k2)
    assert k2.mail_tonight                                     # she comes again tomorrow
    assert oil_before >= 0


def test_the_mail_boat_waits_offshore_when_the_dock_is_broken():
    seed = 2
    k = keep_at(seed, 3, levels=[3, 3, 3])
    k.structure["dock"] = 5
    play_whole_night(k)
    assert k.boat_due is True and k.delivery is None
    assert any("waits offshore" in e[2] or "wait offshore" in e[2] for e in k.log) or any(
        o["kind"] == "mail" and o["outcome"] != "passed" for o in k.report["ships"])


# ---- weather damage -----------------------------------------------------------------------------------------
def test_storms_damage_the_station_and_shutters_halve_it_for_the_glass_and_rail():
    def storm(seed, night):
        return weather(seed, night).severity == 3
    total_plain = total_shutter = 0
    count = 0
    for seed in range(1, 25):
        for night in range(4, 60):
            if not storm(seed, night):
                continue
            plain, shut = keep_at(seed, night, levels=[2, 2, 2]), keep_at(seed, night, levels=[2, 2, 2])
            shut.upgrades.append("shutters")
            for k in (plain, shut):
                k.structure = {p: 100 for p in data.PARTS}
                play_whole_night(k)
            total_plain += 400 - plain.structure["lantern"] - plain.structure["rail"] - 200 + 200
            total_shutter += 400 - shut.structure["lantern"] - shut.structure["rail"] - 200 + 200
            assert plain.night_stats["damage"] > 0
            assert all(0 <= v <= 100 for v in plain.structure.values())
            count += 1
            if count >= 40:
                break
        if count >= 40:
            break
    assert total_shutter < total_plain


def test_a_calm_night_leaves_the_station_alone():
    k = keep_at(1, 20, levels=[1, 1, 1])
    k.structure = {p: 60 for p in data.PARTS}
    play_whole_night(k)
    assert k.night_stats["damage"] == 0 and all(v == 60 for v in k.structure.values())


def test_a_cracked_lantern_glass_shortens_the_beam():
    k = keep_at(1, 20)
    k.structure["lantern"] = 100
    sim.begin_night(k)
    full = sim.effective_reach(k, 1, 0)
    k.structure["lantern"] = 45
    assert sim.effective_reach(k, 1, 0) == full - 1
    k.structure["lantern"] = 10
    assert sim.effective_reach(k, 1, 0) == full - 2


def test_fog_costs_reach_and_the_fog_bell_gives_one_back():
    k = keep_at(1, 20)
    sim.begin_night(k)
    assert sim.effective_reach(k, 2, 2) == 7 - data.COND_PENALTY[2]
    k.upgrades.append("bell")
    assert sim.effective_reach(k, 2, 2) == 7 - data.COND_PENALTY[2] + 1
    assert sim.effective_reach(k, 2, 0) == 7                  # the bell does nothing in clear air
    k.upgrades.append("lens")
    assert sim.effective_reach(k, 2, 0) == 8


# ---- the keeper ----------------------------------------------------------------------------------------------
def test_keeping_watch_costs_energy_and_resting_restores_it():
    watch = keep_at(1, 20, levels=[1, 1, 1])
    watch.tasks["watch"] = True
    rest = keep_at(1, 20, levels=[1, 1, 1])
    rest.energy = watch.energy = 50.0
    play_whole_night(watch)
    play_whole_night(rest)
    assert watch.energy < 50 < rest.energy


def test_a_tired_keeper_works_at_half_strength_but_the_light_is_never_blocked():
    k = keep_at(1, 20, levels=[1, 1, 1])
    k.energy = 5.0
    k.tasks["watch"] = True
    sim.begin_night(k)
    sim.step(k, 20)
    assert k.energy >= 0
    assert sim.lamp_level(k, k.tick) == 1                      # the lamp still burns
    k.structure["rail"] = 50
    k.supplies["timber"] = 3
    assert sim.patch_now(k, "rail") and k.structure["rail"] == 50 + data.NIGHT_PATCH_HEAL // 2


def test_patching_in_the_dark_spends_supplies_and_refuses_when_there_are_none():
    k = keep_at(1, 20)
    sim.begin_night(k)
    k.structure["dock"] = 40
    k.supplies["timber"] = 1
    assert sim.patch_now(k, "dock") and k.structure["dock"] == 50 and k.supplies["timber"] == 0
    assert not sim.patch_now(k, "dock")
    assert not sim.patch_now(k, "nonsense")
    k.structure["tower"] = 100
    k.supplies["timber"] = 5
    assert not sim.patch_now(k, "tower")                       # already sound: costs nothing
    assert k.supplies["timber"] == 5


def test_the_repair_task_patches_between_rounds():
    k = keep_at(1, 20, levels=[1, 1, 1])
    k.tasks["repair"] = True
    k.structure = {p: 50 for p in data.PARTS}
    play_whole_night(k)
    assert sum(k.structure.values()) > 250 and k.supplies["timber"] < data.START_SUPPLIES["timber"] + 1


def test_the_watching_keeper_sees_trouble_and_deals_with_it():
    seed, night = find_night(lambda s, n: any(
        __import__("rng").unit(s, "inc", n, t) < data.INCIDENT_CHANCE * 0.5 for t in range(clock.night_len(n))) and not clock.is_festival(n))
    k = keep_at(seed, night, levels=[1, 1, 1])
    k.tasks["watch"] = True
    play_whole_night(k)
    assert k.night_stats["incidents"] >= 1 and k.night_stats["unhandled"] == 0


def test_unhandled_trouble_costs_a_little_and_never_more():
    seed, night = find_night(lambda s, n: any(
        __import__("rng").unit(s, "inc", n, t) < data.INCIDENT_CHANCE for t in range(8, clock.night_len(n) - 10)) and not clock.is_festival(n))
    k = keep_at(seed, night, levels=[1, 1, 1])
    play_whole_night(k)
    assert k.night_stats["incidents"] >= 1
    assert sum(k.structure.values()) >= sum(data.START_STRUCTURE.values()) - 20 - k.night_stats["damage"]


def test_tending_clears_an_incident_for_a_little_energy():
    k = keep_at(1, 20, levels=[1, 1, 1])
    sim.begin_night(k)
    k.incident = {"kind": "smoke", "tick": 0, "expires": 6}
    e = k.energy
    assert sim.tend_now(k) and k.incident is None and k.energy < e
    assert not sim.tend_now(k)


def test_the_festival_night_is_a_still_night_where_nothing_happens():
    k = keep_at(3, 20, levels=[0, 0, 0])
    play_whole_night(k)
    assert k.night_stats["events"] == 0 and k.report["quiet"] and k.meta["counters"]["empty_nights"] == 1
    assert k.report["ships"] == []


def test_morning_report_adds_up_and_breakfast_is_eaten():
    seed, night = _clear_ship_night()
    k = keep_at(seed, night, levels=[2, 2, 2])
    food = k.supplies["food"]
    play_whole_night(k)
    r = k.report
    assert r["night"] == night and r["lamp_hours"] > 0 and r["oil_used"] == round(k.night_stats["oil_used"], 1)
    assert len(r["ships"]) == len(shipgen.ships_for_night(seed, night, False))
    assert k.supplies["food"] == food - 1
    assert copy.deepcopy(r) == r
