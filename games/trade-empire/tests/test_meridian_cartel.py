"""J-11 / J-12 / J-3 -- Meridian Freight (a shadow rival firm seen only through price moves, with a rumoured then
real ledger line) and the Cartel Board (squeeze and dump, with a plainly shown backlash window)."""

import json
import sys
import types

import pytest


def _contest(m, good=None, left=25):
    m.meridian_enabled = True
    m.meridian_contest = {"good": good or m.ORE, "left": left}


def _deep(m):
    m.unlocked_research.update({"galaxy_expansion", "outer_reaches", "deep_survey", "umbral_reach"})
    for cid in list(m.EXPANSION_COLONIES) + list(m.RIFT_COLONIES) + list(m.DEEP_COLONIES):
        m.colony_states.setdefault(cid, m.ColonyState(cid))
    m.total_profit = m.max_profit_ever = 100_000
    return m


# ------------------------------------------------------------------ Meridian

def test_off_by_default_changes_nothing(game_env):
    m = game_env.module
    assert not m.meridian_enabled and m.meridian_multiplier(m.ORE) == 1.0
    game_env.tick(200)
    assert m.meridian_ticks == 0 and m.meridian_contest is None
    assert "meridian" not in m.get_state()


def test_it_contests_one_good_every_cycle_for_25_ticks(game_env):
    m = game_env.module
    m.meridian_enabled = True
    game_env.tick(m.MERIDIAN_CYCLE)
    assert m.meridian_contest is not None and m.meridian_contest["left"] == m.MERIDIAN_CONTEST_TICKS
    good = m.meridian_contest["good"]
    assert good in m.seasonal_reachable_goods()
    game_env.tick(m.MERIDIAN_CONTEST_TICKS)
    assert m.meridian_contest is None
    assert m.records["meridian_contests"] == 1
    game_env.tick(m.MERIDIAN_CYCLE - m.MERIDIAN_CONTEST_TICKS)
    assert m.meridian_contest is not None and m.records["meridian_contests"] == 2


def test_the_contest_is_deterministic_for_a_seed(game_env):
    m = game_env.module
    picks = [m._meridian_pick(c) for c in range(1, 8)]
    assert picks == [m._meridian_pick(c) for c in range(1, 8)]
    m.founding_seed = 999
    assert picks != [m._meridian_pick(c) for c in range(1, 8)]


def test_the_contested_good_sells_for_twelve_percent_less_and_others_do_not(game_env):
    m = game_env.module
    base = m.current_sell_price(m.ORE)
    _contest(m, m.ORE)
    assert m.meridian_multiplier(m.ORE) == pytest.approx(0.88) and m.meridian_multiplier(m.GRAIN) == 1.0
    assert m.current_sell_price(m.ORE) < base


def test_it_is_seen_only_as_a_price_move_in_the_market_row_until_intel(game_env):
    m = game_env.module
    _contest(m, m.ORE)
    m.render()
    # the sparkline history is the market's own; the dip is the price line itself
    assert "Meridian" not in game_env.elements["market-ore-display"].innerText


def test_undercutting_ends_it_and_shields_the_good(game_env):
    m = game_env.module
    _contest(m, m.ORE)
    m.total_profit = 500
    assert m.undercut_meridian() is True
    assert m.total_profit == 500 - m.MERIDIAN_UNDERCUT_COST and m.meridian_contest is None
    assert m.meridian_shield == {"good": m.ORE, "left": m.MERIDIAN_SHIELD_TICKS}
    assert m.records["meridian_answers"] == 1 and "rival_answered" in m.achievement_ids_earned()
    assert m.undercut_meridian() is False  # nothing to undercut


def test_undercut_needs_credits(game_env):
    m = game_env.module
    _contest(m)
    m.total_profit = m.MERIDIAN_UNDERCUT_COST - 1
    assert m.can_undercut_meridian() is False and m.undercut_meridian() is False


def test_a_shielded_good_is_not_contested_next_cycle(game_env):
    m = game_env.module
    m.meridian_enabled = True
    m.meridian_ticks = m.MERIDIAN_CYCLE - 1
    target = m._meridian_pick(1)
    m.meridian_shield = {"good": target, "left": 30}
    game_env.tick(1)
    assert m.meridian_contest is None


def test_an_exclusive_guild_contract_keeps_meridian_off_the_good(game_env):
    m = game_env.module
    _contest(m, m.ORE)
    m.guild_state = "active"
    m.guild_contract.update(good=m.ORE, destination="ferrum", units=10, delivered=0, ticks_left=100, reward=100)
    assert m.meridian_active_contest() is None and m.meridian_multiplier(m.ORE) == 1.0
    m.guild_state = "none"
    assert m.meridian_active_contest() is not None


def test_a_contract_signed_before_the_cycle_counts_as_an_answer(game_env):
    m = game_env.module
    m.meridian_enabled = True
    m.meridian_ticks = m.MERIDIAN_CYCLE - 1
    target = m._meridian_pick(1)
    m.guild_state = "active"
    m.guild_contract.update(good=target, destination="ferrum", units=10, delivered=0, ticks_left=100, reward=100)
    m.meridian_tick()
    assert m.records["meridian_answers"] == 1


def test_ignoring_it_costs_only_the_dip(game_env):
    m = game_env.module
    _contest(m, m.ORE, left=3)
    before = m.total_profit
    game_env.tick(5)
    assert m.meridian_contest is None and m.total_profit >= before


def test_ledger_line_is_a_rumour_without_intel_and_real_with_it(game_env):
    m = game_env.module
    m.meridian_enabled = True
    line = m.meridian_ledger_line()
    assert line.startswith("Rumour: Meridian moved about") and "unverified" in line
    assert line == m.meridian_ledger_line()  # stable within a cycle
    m.unlocked_research.add("market_insight")
    real = m.meridian_ledger_line()
    assert real.startswith("Intel: Meridian moved 0 units this cycle")
    _contest(m, m.ORE)
    m.meridian_units = 340
    real = m.meridian_ledger_line()
    assert "340 units this cycle" in real and "Contesting Ore" in real and "-12%" in real


def test_the_intel_desk_is_the_other_route_to_the_real_numbers(game_env):
    m = game_env.module
    m.meridian_enabled = True
    m.total_profit = 1000
    game_env.elements["desk-toggle-button"].dispatch("click", None)
    assert game_env.elements["meridian-intel-button"].hidden is False
    game_env.elements["meridian-intel-button"].dispatch("click", None)
    assert m.meridian_intel_bought and m.total_profit == 1000 - m.MERIDIAN_INTEL_COST
    assert m.meridian_ledger_line().startswith("Intel:")
    assert game_env.elements["meridian-intel-button"].hidden is True


def test_units_moved_follow_the_cycle_and_reset(game_env):
    m = game_env.module
    m.meridian_enabled = True
    game_env.tick(10)
    assert m.meridian_units == 10 * m.MERIDIAN_UNITS_QUIET
    game_env.tick(m.MERIDIAN_CYCLE - 10)
    assert m.meridian_units == 0


def test_the_toggle_and_the_undercut_button(game_env):
    m = game_env.module
    el = game_env.elements
    el["desk-toggle-button"].dispatch("click", None)
    el["meridian-toggle-button"].dispatch("click", None)
    assert m.meridian_enabled and el["meridian-toggle-button"].innerText == "Meridian Freight: on"
    assert el["meridian-undercut-button"].hidden is True
    _contest(m, m.ORE)
    m.total_profit = 200
    m.render()
    assert el["meridian-undercut-button"].hidden is False
    el["meridian-undercut-button"].dispatch("click", None)
    assert m.meridian_contest is None


def test_meridian_state_round_trips(game_env):
    m = game_env.module
    _contest(m, m.GRAIN, left=11)
    m.meridian_ticks, m.meridian_units = 77, 55
    m.meridian_shield = {"good": m.ORE, "left": 9}
    m.meridian_intel_bought = True
    state = json.loads(json.dumps(m.get_state()))
    m.meridian_enabled, m.meridian_contest, m.meridian_shield = False, None, None
    m.load_state(state)
    assert m.meridian_enabled and m.meridian_contest == {"good": "grain", "left": 11}
    assert m.meridian_shield == {"good": "ore", "left": 9} and m.meridian_ticks == 77 and m.meridian_units == 55
    assert m.meridian_intel_bought


@pytest.mark.parametrize("raw", [
    "x", 3, [], {"enabled": 1, "ticks": "9", "units": True},
    {"enabled": True, "contest": {"good": "nope", "left": 5}},
    {"enabled": True, "contest": {"good": "ore", "left": 99}},
    {"enabled": True, "contest": {"good": "ore", "left": 0}},
    {"enabled": True, "contest": {"good": "isotopes", "left": 5}},
    {"enabled": True, "contest": {"good": ["ore"], "left": 5}},
    {"enabled": True, "shield": {"good": "ore", "left": 99}},
    {"enabled": True, "contest": "ore"},
])
def test_tampered_meridian_values_are_dropped(game_env, raw):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["meridian"] = raw
    assert m.load_state(state) is True
    assert m.meridian_contest is None and m.meridian_shield is None
    assert m.meridian_enabled is (isinstance(raw, dict) and raw.get("enabled") is True)


def test_a_renewal_switches_meridian_off_but_keeps_the_counts(game_env):
    m = game_env.module
    m.meridian_enabled = True
    m.records["meridian_answers"] = 3
    m.endgame_reached = True
    m.found_new_corporation()
    assert not m.meridian_enabled and m.records["meridian_answers"] == 3


# -------------------------------------------------------------------- Cartel

def test_cartel_is_locked_until_the_exchange_or_the_endgame(game_env):
    m = game_env.module
    m.total_profit = 10_000
    assert not m.cartel_open() and squeeze_none(m)
    m.endgame_reached = True
    assert m.cartel_open()


def squeeze_none(m):
    return m.squeeze(m.ORE) is None and m.dump(m.ORE) is None


def test_a_squeeze_costs_eight_units_and_raises_the_price_for_twenty_ticks(game_env):
    m = _deep(game_env.module)
    price = m.current_sell_price(m.ORE)
    before = m.total_profit
    assert m.squeeze(m.ORE) == "spike"
    assert m.total_profit == before - m.CARTEL_SQUEEZE_UNITS * price
    assert m.cartel_multiplier(m.ORE) == pytest.approx(1.30) and m.current_sell_price(m.ORE) > price
    game_env.tick(m.CARTEL_SPIKE_TICKS)
    assert m.cartel_multiplier(m.ORE) == 1.0


def test_a_second_squeeze_inside_the_window_backfires_into_a_slump(game_env):
    m = _deep(game_env.module)
    m.squeeze(m.ORE)
    game_env.tick(10)
    assert m.cartel_backlash_left(m.ORE) == m.CARTEL_BACKLASH_WINDOW - 10
    before = m.total_profit
    assert m.squeeze(m.ORE) == "backlash" and m.total_profit < before  # the credits are still spent
    assert m.cartel_multiplier(m.ORE) == pytest.approx(0.75)
    assert m.cartel_effects[m.ORE]["left"] == m.CARTEL_SLUMP_TICKS


def test_after_the_window_a_squeeze_is_safe_again(game_env):
    m = _deep(game_env.module)
    m.squeeze(m.ORE)
    game_env.tick(m.CARTEL_BACKLASH_WINDOW)
    assert m.cartel_backlash_left(m.ORE) == 0 and m.squeeze(m.ORE) == "spike"


def test_the_window_is_per_good(game_env):
    m = _deep(game_env.module)
    m.squeeze(m.ORE)
    assert m.cartel_backlash_left(m.GRAIN) == 0 and m.squeeze(m.GRAIN) == "spike"


def test_a_dump_sells_the_stockpile_and_crashes_the_price(game_env):
    m = _deep(game_env.module)
    m.stockpile[m.ORE] = 10
    before_price = m.market_multiplier[m.ORE]
    before = m.total_profit
    expected = m.stockpile_sale_value(m.ORE)
    assert m.dump(m.ORE) == "sold"
    assert m.stockpile[m.ORE] == 0 and m.total_profit == before + expected
    assert m.market_multiplier[m.ORE] < before_price
    assert m.dump(m.ORE) is None  # nothing left to dump


def test_a_dump_ends_a_meridian_contest_and_shields_the_good(game_env):
    m = _deep(game_env.module)
    _contest(m, m.ORE)
    m.stockpile[m.ORE] = 5
    assert m.dump(m.ORE) == "shielded"
    assert m.meridian_contest is None and m.meridian_shield["good"] == m.ORE
    assert m.records["meridian_answers"] == 1


def test_a_second_move_inside_the_window_dump_backfires(game_env):
    m = _deep(game_env.module)
    m.squeeze(m.ORE)
    _contest(m, m.ORE)
    m.stockpile[m.ORE] = 5
    m.market_multiplier[m.ORE] = 1.0
    before = m.market_multiplier[m.ORE]
    assert m.dump(m.ORE) == "backlash"
    assert m.meridian_contest is not None  # no shield on a backfire
    assert m.market_multiplier[m.ORE] <= before - m.CARTEL_DUMP_EXTRA_DROP - 0.04


def test_moves_are_counted_and_earn_board_member(game_env):
    m = _deep(game_env.module)
    for good in (m.ORE, m.GRAIN, m.MACHINERY, m.WATER):
        m.squeeze(good)
    assert m.records["cartel_moves"] == 4 and "board_member" not in m.achievement_ids_earned()
    m.squeeze(m.ENERGY)
    assert "board_member" in m.achievement_ids_earned()
    assert {a["id"]: a["progress"] for a in m.achievements_summary()}["board_member"] == (5, 5)


def test_a_squeeze_sets_the_price_memory_ghost_line(game_env):
    m = _deep(game_env.module)
    m.market_multiplier[m.ORE] = 0.7
    m.squeeze(m.ORE)
    assert m.price_memory[m.ORE] == pytest.approx(0.7)


def test_a_squeeze_needs_credits_and_a_reachable_good(game_env):
    m = _deep(game_env.module)
    m.total_profit = 1
    assert m.can_squeeze(m.ORE) is False
    m.total_profit = 10_000
    m.unlocked_research.difference_update({"umbral_reach"})
    m.endgame_reached = True
    assert m.can_squeeze(m.NEUTRONIUM) is False and m.can_squeeze("nope") is False and m.can_squeeze(None) is False


def test_the_row_text_states_the_window_plainly(game_env):
    m = _deep(game_env.module)
    assert "no backlash window" in m.cartel_row_text(m.ORE)
    m.squeeze(m.ORE)
    text = m.cartel_row_text(m.ORE)
    assert f"backlash window: {m.CARTEL_BACKLASH_WINDOW} tick(s), a move now backfires" in text and "squeeze premium +30%" in text


def test_the_cartel_ui_squeezes_dumps_and_asks_before_a_backfire(game_env):
    m = _deep(game_env.module)
    el = game_env.elements
    el["desk-toggle-button"].dispatch("click", None)
    assert el["cartel-controls"].hidden is False and el["cartel-ore-row"].hidden is False
    el["cartel-ore-squeeze-button"].dispatch("click", None)
    assert m.cartel_effects[m.ORE]["kind"] == "spike"
    asked = []

    class Dialog:
        def ask(self, **options):
            asked.append(options)

    sys.modules["js"].window = types.SimpleNamespace(ConfirmDialog=Dialog())
    el["cartel-ore-squeeze-button"].dispatch("click", None)
    assert asked and "BACKFIRE" in asked[0]["message"] and asked[0]["allowSkip"] is False
    assert m.cartel_effects[m.ORE]["kind"] == "spike"  # not done until confirmed
    asked[0]["onConfirm"]()
    assert m.cartel_effects[m.ORE]["kind"] == "slump"
    m.stockpile[m.GRAIN] = 5
    m.render()
    assert el["cartel-grain-dump-button"].disabled is False and el["cartel-grain-dump-button"].innerText == "Dump 5"


def test_goods_from_locked_systems_have_no_row(game_env):
    m = game_env.module
    m.endgame_reached = True
    m.render()
    game_env.elements["desk-toggle-button"].dispatch("click", None)
    assert game_env.elements["cartel-ore-row"].hidden is False
    assert game_env.elements["cartel-neutronium-row"].hidden is True


def test_locked_status_text(game_env):
    game_env.elements["desk-toggle-button"].dispatch("click", None)
    assert "Locked" in game_env.elements["cartel-status"].innerText
    assert game_env.elements["cartel-controls"].hidden is True


def test_cartel_state_round_trips_and_is_absent_when_unused(game_env):
    m = _deep(game_env.module)
    assert "cartel" not in m.get_state()
    m.squeeze(m.ORE)
    game_env.tick(6)
    state = json.loads(json.dumps(m.get_state()))
    assert state["cartel"]["effects"]["ore"]["left"] == m.CARTEL_SPIKE_TICKS - 6
    m.cartel_effects.clear()
    m.cartel_last.clear()
    m.load_state(state)
    assert m.cartel_effects["ore"]["left"] == m.CARTEL_SPIKE_TICKS - 6 and m.cartel_last["ore"] == 6


@pytest.mark.parametrize("raw", [
    "x", 3, [], {"effects": "x", "last": 5},
    {"effects": {"ore": {"kind": "spike", "left": 99}}},
    {"effects": {"ore": {"kind": "spike", "left": 0}}},
    {"effects": {"ore": {"kind": "boost", "left": 5}}},
    {"effects": {"nope": {"kind": "spike", "left": 5}}},
    {"effects": {"isotopes": {"kind": "spike", "left": 5}}},
    {"effects": {"ore": "spike"}},
    {"effects": {"ore": {"kind": "slump", "left": True}}},
    {"last": {"ore": 80}}, {"last": {"ore": -1}}, {"last": {"ore": "3"}}, {"last": {"nope": 3}}, {"last": {"ore": 2.5}},
])
def test_tampered_cartel_values_are_dropped(game_env, raw):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["cartel"] = raw
    assert m.load_state(state) is True
    assert m.cartel_effects == {} and m.cartel_last == {}


def test_a_spike_longer_than_its_kind_allows_is_dropped(game_env):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["cartel"] = {"effects": {"ore": {"kind": "spike", "left": m.CARTEL_SLUMP_TICKS}}}
    m.load_state(state)
    assert m.cartel_effects == {}


def test_a_renewal_clears_the_cartel_and_keeps_the_move_count(game_env):
    m = _deep(game_env.module)
    m.squeeze(m.ORE)
    m.endgame_reached = True
    m.found_new_corporation()
    assert m.cartel_effects == {} and m.cartel_last == {} and m.records["cartel_moves"] == 1


def test_sandbox_round_trip_restores_the_real_rival_and_cartel(game_env):
    m = _deep(game_env.module)
    _contest(m, m.GRAIN)
    m.squeeze(m.ORE)
    before = json.dumps(m.get_state(), sort_keys=True)
    m.sandbox_enter()
    assert m.cartel_effects == {} and not m.meridian_enabled
    m.sandbox_leave()
    assert json.dumps(m.get_state(), sort_keys=True) == before


def test_sandbox_moves_do_not_count(game_env):
    m = game_env.module
    m.sandbox_enter()
    m.squeeze(m.ORE)
    assert m.cartel_effects  # works in practice
    m.sandbox_leave()
    assert m.records["cartel_moves"] == 0
