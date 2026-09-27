"""O-1..O-4 -- Renew the Charter: the perk tree, founding conditions, the
lifetime ledger and the harder charter."""

import json
import random
import sys
import types

import pytest


def _endgame(module):
    module.endgame_reached = True


def _renew(module, times=1):
    for _ in range(times):
        _endgame(module)
        assert module.found_new_corporation() is True


def _give_points(module, points):
    module.charter_points_earned = points


def _one_trip(game_env, ship_id="1", destination="verdant"):
    game_env.load(ship_id=ship_id)
    game_env.depart(destination, ship_id=ship_id)
    game_env.tick(game_env.module.TRAVEL_TICKS)


# --------------------------------------------------------------- the tree

def test_the_tree_has_four_branches_of_three_with_scaling_costs(game_env):
    m = game_env.module
    assert len(m.CHARTER_PERKS) == 12
    for branch in m.CHARTER_BRANCHES:
        tiers = sorted(p["cost"] for p in m.CHARTER_PERKS.values() if p["branch"] == branch)
        assert tiers == [1, 2, 3], branch
    assert sum(p["cost"] for p in m.CHARTER_PERKS.values()) == 24


def test_prerequisites_are_known_and_point_to_a_cheaper_tier(game_env):
    m = game_env.module
    for perk_id, perk in m.CHARTER_PERKS.items():
        for required in perk["requires"]:
            assert required in m.CHARTER_PERKS
            assert m.CHARTER_PERKS[required]["cost"] < perk["cost"], perk_id
    # one perk needs two branches, so the tree is not just four chains
    assert m.CHARTER_PERKS["standing_convoy"]["requires"] == ("waystation_network", "standing_orders")


def test_nothing_can_be_bought_without_points_or_prerequisites(game_env):
    m = game_env.module
    assert not any(m.can_buy_charter_perk(p) for p in m.CHARTER_PERKS)
    _give_points(m, 100)
    assert m.can_buy_charter_perk("surveyed_lanes")
    assert not m.can_buy_charter_perk("waystation_network")  # needs Surveyed Lanes
    assert m.buy_charter_perk("waystation_network") is False
    assert m.buy_charter_perk("surveyed_lanes") is True
    assert m.can_buy_charter_perk("waystation_network")


def test_a_perk_is_bought_once_and_costs_its_points(game_env):
    m = game_env.module
    _give_points(m, 3)
    assert m.buy_charter_perk("surveyed_lanes") is True
    assert m.charter_points_available() == 2
    assert m.buy_charter_perk("surveyed_lanes") is False
    assert m.charter_points_available() == 2
    assert m.buy_charter_perk("waystation_network") is True
    assert m.charter_points_available() == 0
    assert m.buy_charter_perk("bogus") is False
    assert m.can_buy_charter_perk(["unhashable"]) is False


def test_standing_convoy_needs_both_branches(game_env):
    m = game_env.module
    _give_points(m, 100)
    for perk in ("surveyed_lanes", "waystation_network"):
        m.buy_charter_perk(perk)
    assert not m.can_buy_charter_perk("standing_convoy")
    m.buy_charter_perk("standing_orders")
    assert m.can_buy_charter_perk("standing_convoy")


def test_renewal_earns_points_and_a_harder_one_earns_one_more(game_env):
    m = game_env.module
    _renew(m)
    assert m.charter_points_earned == m.CHARTER_POINTS_PER_RENEWAL
    m.hard_charter_active = True  # pretend the charter just finished was a harder one
    _renew(m)
    assert m.charter_points_earned == 2 * m.CHARTER_POINTS_PER_RENEWAL + m.HARD_CHARTER_BONUS_POINTS


def test_perks_and_points_survive_a_renewal(game_env):
    m = game_env.module
    _give_points(m, 10)
    m.buy_charter_perk("surveyed_lanes")
    _renew(m)
    assert m.charter_perk("surveyed_lanes")
    assert m.charter_points_earned == 10 + m.CHARTER_POINTS_PER_RENEWAL
    assert m.charter_points_available() == 10 + m.CHARTER_POINTS_PER_RENEWAL - 1


# ------------------------------------------------------------ perk effects

def test_without_perks_every_value_is_the_plain_constant(game_env):
    m = game_env.module
    assert m.automation_cost() == m.AUTOMATION_COST
    assert m.colony_invest_cost() == m.COLONY_INVEST_COST
    assert m.trade_post_cost() == m.TRADE_POST_COST
    assert m.trade_post_income_each() == m.TRADE_POST_INCOME_PER_TICK
    assert m.development_threshold() == m.DEVELOPMENT_THRESHOLD
    assert m.guild_first_offer_ticks() == m.GUILD_FIRST_OFFER_TICKS
    assert m.guild_cooldown_ticks() == m.GUILD_COOLDOWN_TICKS
    assert m.guild_reward_multiplier() == m.GUILD_REWARD_MULTIPLIER
    assert m.charter_decay_multiplier("aurum") == 1.0
    assert m.founding_output_multiplier("aurum") == 1.0


def test_surveyed_lanes_adds_one_unit_of_cargo(game_env):
    m = game_env.module
    m.colony_states["aurum"].need_satisfaction = 0.5
    m.ships["1"].load()
    base = m.ships["1"].cargo_qty
    m.ships["1"].cargo_good, m.ships["1"].cargo_qty = None, 0
    m.charter_perks.add("surveyed_lanes")
    m.ships["1"].load()
    assert m.ships["1"].cargo_qty == base + m.CHARTER_CARGO_BONUS


def test_waystation_network_makes_trade_posts_cheaper_and_better(game_env):
    m = game_env.module
    m.charter_perks.add("waystation_network")
    assert m.trade_post_cost() == 300
    assert m.trade_post_income_each() == m.TRADE_POST_INCOME_PER_TICK + 1
    m.trade_posts.append("Home system")
    assert m.trade_post_income_per_tick() == 3


def test_standing_orders_discounts_automation(game_env):
    m = game_env.module
    m.charter_perks.add("standing_orders")
    assert m.automation_cost() == 120
    m.total_profit = 120
    assert m.automate_ship("1") is True
    assert m.total_profit == 0


def test_lab_automation_speeds_research(game_env):
    m = game_env.module
    m.research_points = 0.0
    game_env.tick(10)
    plain = m.research_points
    m.charter_perks.add("lab_automation")
    m.research_points = 0.0
    game_env.tick(10)
    assert m.research_points == pytest.approx(plain * 1.2)


def test_auto_balancers_speed_market_recovery(game_env):
    m = game_env.module
    m.market_multiplier["ore"] = 0.5
    m.recover_market()
    plain = m.market_multiplier["ore"] - 0.5
    m.market_multiplier["ore"] = 0.5
    m.charter_perks.add("auto_balancers")
    m.recover_market()
    assert m.market_multiplier["ore"] - 0.5 == pytest.approx(plain * 1.2)


def test_frontier_grants_cheapen_investment(game_env):
    m = game_env.module
    m.charter_perks.add("frontier_grants")
    m.total_profit = 45
    assert m.invest_in_colony("aurum") is True
    assert m.total_profit == 0


def test_settler_guilds_slow_need_decay(game_env):
    m = game_env.module
    m.colony_states["aurum"].need_satisfaction = 0.5
    m.colony_states["aurum"].decay()
    plain_drop = 0.5 - m.colony_states["aurum"].need_satisfaction
    m.colony_states["aurum"].need_satisfaction = 0.5
    m.charter_perks.add("settler_guilds")
    m.colony_states["aurum"].decay()
    assert 0.5 - m.colony_states["aurum"].need_satisfaction == pytest.approx(plain_drop * 0.9)


def test_charter_colonies_lower_the_development_threshold(game_env):
    m = game_env.module
    state = m.colony_states["aurum"]
    state.add_development(90)
    assert not state.is_developed()
    m.charter_perks.add("charter_colonies")
    state.add_development(0)
    assert state.is_developed()


def test_guild_perks_shorten_the_wait_and_raise_the_reward(game_env):
    m = game_env.module
    m.charter_perks.update({"guild_standing", "trusted_name"})
    assert m.guild_first_offer_ticks() == 15
    assert m.guild_cooldown_ticks() == 45
    assert m.guild_reward_multiplier() == pytest.approx(m.GUILD_REWARD_MULTIPLIER * 1.15)
    m._guild_clear(m.guild_first_offer_ticks())
    assert m.guild_cooldown == 15


def test_colonial_goodwill_lifts_home_colonies_when_bought_and_at_renewal(game_env):
    m = game_env.module
    m.colony_states["aurum"].need_satisfaction = 0.5
    _give_points(m, 100)
    for perk in ("guild_standing", "colonial_goodwill"):
        m.buy_charter_perk(perk)
    assert m.colony_states["aurum"].need_satisfaction == pytest.approx(0.6)
    m.charter_rng = random.Random(7)
    _renew(m)
    pair = m.founding_from_seed(m.founding_seed)["pair"]
    stretched = [c for c in m.COLONIES if c not in pair][0]
    assert m.colony_states[stretched].need_satisfaction == pytest.approx(m.FOUNDING_STRETCHED_NEED + 0.1)
    assert m.colony_states[pair[0]].need_satisfaction == pytest.approx(min(1.0, m.FOUNDING_THRIVING_NEED + 0.1))


def test_standing_convoy_automates_ship_one_free(game_env):
    m = game_env.module
    _give_points(m, 100)
    for perk in ("surveyed_lanes", "waystation_network", "standing_orders", "standing_convoy"):
        assert m.buy_charter_perk(perk) is True
    assert m.ships["1"].automated is True
    _renew(m)
    assert m.ships["1"].automated is True
    assert m.automated_ship_count() == 1


# ----------------------------------------------------- founding conditions

def test_the_first_charter_has_no_founding_conditions(game_env):
    m = game_env.module
    assert m.founding_seed == 0
    assert m.founding_focus("aurum") is None
    assert "standard opening" in m.founding_summary_text()
    assert m.colony_states["aurum"].need_satisfaction == m.STARTING_NEED_SATISFACTION


def test_founding_is_a_pure_function_of_the_seed(game_env):
    m = game_env.module
    assert m.founding_from_seed(12345) == m.founding_from_seed(12345)
    pairs = {tuple(m.founding_from_seed(seed)["pair"]) for seed in range(1, 200)}
    assert len(pairs) == 10  # every one of the ten home pairs can come up
    info = m.founding_from_seed(12345)
    assert len(info["pair"]) == 2 and set(info["pair"]) <= set(m.COLONIES)
    assert set(info["foci"]) == set(info["pair"])
    assert set(info["foci"].values()) <= set(m.FOUNDING_FOCI)


def test_renewal_rolls_a_saved_seed_and_sets_the_opening(game_env):
    m = game_env.module
    m.charter_rng = random.Random(42)
    _renew(m)
    assert 1 <= m.founding_seed <= m.FOUNDING_SEED_MAX
    a, b = m.founding_from_seed(m.founding_seed)["pair"]
    assert m.colony_states[a].need_satisfaction == m.FOUNDING_THRIVING_NEED
    assert m.colony_states[b].need_satisfaction == m.FOUNDING_THRIVING_NEED
    for colony_id in m.COLONIES:
        if colony_id not in (a, b):
            assert m.colony_states[colony_id].need_satisfaction == m.FOUNDING_STRETCHED_NEED
    assert m.ships["1"].location == a and m.ships["2"].location == b
    assert "start thriving and connected" in m.founding_summary_text()


def test_two_renewals_can_differ(game_env):
    m = game_env.module
    seeds = set()
    for seed in (1, 2, 3, 4, 5):
        m.charter_rng = random.Random(seed)
        _renew(m)
        seeds.add(m.founding_seed)
    assert len(seeds) > 1


def test_founding_foci_change_output_and_decay(game_env):
    m = game_env.module
    m.founding_seed = 0
    state = m.colony_states["aurum"]
    base_output = state.output_multiplier()
    seed = next(s for s in range(1, 500) if m.founding_from_seed(s)["foci"].get("aurum") == "bulk")
    m.founding_seed = seed
    assert state.output_multiplier() == pytest.approx(base_output * m.FOUNDING_FOCI["bulk"]["output"])
    seed = next(s for s in range(1, 500) if m.founding_from_seed(s)["foci"].get("aurum") == "steady")
    m.founding_seed = seed
    assert m.charter_decay_multiplier("aurum") == pytest.approx(m.FOUNDING_FOCI["steady"]["decay"])
    other = next(c for c in m.COLONIES if c not in m.founding_from_seed(seed)["pair"])
    assert m.charter_decay_multiplier(other) == 1.0


# ---------------------------------------------------------- lifetime ledger

def test_a_delivery_counts_units_and_the_route_once(game_env):
    m = game_env.module
    _one_trip(game_env)
    assert m.ledger_units_moved > 0
    assert m.ledger_routes_established == 1
    moved = m.ledger_units_moved
    _one_trip(game_env, destination="aurum")  # the same pair, back the other way
    assert m.ledger_units_moved > moved
    assert m.ledger_routes_established == 1
    _one_trip(game_env, destination="ferrum")
    assert m.ledger_routes_established == 2


def test_the_ledger_survives_renewal_but_a_route_can_count_again(game_env):
    m = game_env.module
    _one_trip(game_env)
    units = m.ledger_units_moved
    _renew(m)
    assert m.ledger_units_moved == units
    assert m.ledger_routes_established == 1
    assert m.ledger_routes_seen == set()
    assert m.charters_completed == 1
    m.ships["1"].location = "aurum"
    _one_trip(game_env)
    assert m.ledger_routes_established == 2  # a new charter's route is a new establishment


def test_the_ledger_panel_shows_the_totals(game_env):
    m = game_env.module
    _one_trip(game_env)
    _renew(m, 2)
    game_env.toggle_charter()
    text = " ".join(game_env.elements[i].innerText for i in (
        "ledger-units-display", "ledger-routes-display", "ledger-charters-display", "ledger-hard-display"))
    assert f"{m.ledger_units_moved:,}" in text
    assert "Charters completed: 2" in text


def test_disrupted_trips_and_stockpile_sales_are_not_goods_moved(game_env):
    m = game_env.module
    m.ledger_record_sale(0, None)
    assert m.ledger_units_moved == 0 and m.ledger_routes_established == 0
    m.total_profit = 1000
    m.buy_stockpile("ore")
    m.sell_stockpile("ore")
    assert m.ledger_units_moved == 0


# ----------------------------------------------------------- harder charter

def test_the_harder_charter_is_locked_until_the_first_endgame(game_env):
    m = game_env.module
    assert m.hard_charter_unlocked() is False
    assert m.set_hard_charter_next(True) is False
    assert m.hard_charter_next is False
    game_env.module.render()
    assert game_env.elements["hard-charter-toggle-button"].hidden is True
    _endgame(m)
    m.render()
    assert game_env.elements["hard-charter-toggle-button"].hidden is False


def test_the_toggle_button_flips_the_choice(game_env):
    m = game_env.module
    _endgame(m)
    m.render()
    game_env.elements["hard-charter-toggle-button"].dispatch("click", None)
    assert m.hard_charter_next is True
    assert "on" in game_env.elements["hard-charter-toggle-button"].innerText
    assert game_env.elements["hard-charter-toggle-button"].attributes["aria-pressed"] == "true"
    game_env.elements["hard-charter-toggle-button"].dispatch("click", None)
    assert m.hard_charter_next is False


def test_renewing_with_it_on_starts_a_harder_charter(game_env):
    m = game_env.module
    _endgame(m)
    m.set_hard_charter_next(True)
    assert m.found_new_corporation() is True
    assert m.hard_charter_active is True
    assert m.hard_charter_next is False  # a one-off choice, not sticky
    assert m.ledger_hard_completed == 0  # finishing a normal charter earns nothing extra
    assert m.charter_points_earned == m.CHARTER_POINTS_PER_RENEWAL


def test_the_harder_charter_saturates_markets_faster_and_fades_needs_sooner(game_env):
    m = game_env.module
    m.market_multiplier["ore"] = 1.0
    m.apply_market_sale("ore", 10)
    normal_drop = 1.0 - m.market_multiplier["ore"]
    m.colony_states["aurum"].need_satisfaction = 0.5
    m.colony_states["aurum"].decay()
    normal_fade = 0.5 - m.colony_states["aurum"].need_satisfaction
    m.hard_charter_active = True
    m.market_multiplier["ore"] = 1.0
    m.apply_market_sale("ore", 10)
    assert 1.0 - m.market_multiplier["ore"] == pytest.approx(normal_drop * m.HARD_CHARTER_SATURATION_MULTIPLIER)
    m.colony_states["aurum"].need_satisfaction = 0.5
    m.colony_states["aurum"].decay()
    assert 0.5 - m.colony_states["aurum"].need_satisfaction == pytest.approx(normal_fade * m.HARD_CHARTER_DECAY_MULTIPLIER)


def test_finishing_a_harder_charter_pays_a_point_and_counts_in_the_ledger(game_env):
    m = game_env.module
    _endgame(m)
    m.set_hard_charter_next(True)
    m.found_new_corporation()
    _endgame(m)
    before = m.charter_points_earned
    assert m.found_new_corporation() is True
    assert m.charter_points_earned == before + m.CHARTER_POINTS_PER_RENEWAL + m.HARD_CHARTER_BONUS_POINTS
    assert m.ledger_hard_completed == 1
    assert m.hard_charter_active is False


def test_the_toolbar_label_flags_a_harder_charter(game_env):
    m = game_env.module
    m.charters_completed = 1
    m.hard_charter_active = True
    m.render()
    assert "(harder)" in game_env.elements["charter-toggle-button"].innerText


# ----------------------------------------------------------- achievements

def test_the_charter_achievements(game_env):
    m = game_env.module
    for perk_id in ("charter_perk", "charter_veteran", "hard_charter_done"):
        assert perk_id in {a["id"] for a in m.ACHIEVEMENTS}
        assert perk_id not in m.achievement_ids_earned()
    _give_points(m, 5)
    m.buy_charter_perk("surveyed_lanes")
    assert "charter_perk" in m.achievement_ids_earned()
    _renew(m, 3)
    assert "charter_veteran" in m.achievement_ids_earned()
    assert "hard_charter_done" not in m.achievement_ids_earned()
    m.hard_charter_active = True
    _renew(m)
    assert "hard_charter_done" in m.achievement_ids_earned()


def test_renewing_does_not_retoast_the_charter_achievements(game_env):
    m = game_env.module
    _give_points(m, 5)
    m.buy_charter_perk("surveyed_lanes")
    m.render()
    game_env.elements["achievement-toast"].innerText = ""
    _renew(m)
    assert "Charter Perk" not in game_env.elements["achievement-toast"].innerText


# --------------------------------------------------------------- save/load

def test_a_first_run_save_has_no_charter_or_ledger_key(game_env):
    state = game_env.module.get_state()
    assert "charter" not in state and "ledger" not in state


def test_a_sale_writes_only_the_ledger_key(game_env):
    _one_trip(game_env)
    state = game_env.module.get_state()
    assert "ledger" in state and "charter" not in state
    assert state["ledger"]["routes_seen"] == [["aurum", "verdant"]]


def test_charter_state_round_trips(game_env):
    m = game_env.module
    _one_trip(game_env)
    m.charter_rng = random.Random(3)
    _give_points(m, 9)
    m.buy_charter_perk("surveyed_lanes")
    m.buy_charter_perk("standing_orders")
    _endgame(m)
    m.set_hard_charter_next(True)
    m.found_new_corporation()
    _one_trip(game_env)
    saved = json.loads(json.dumps(m.get_state()))
    snapshot = (
        m.charters_completed, m.charter_points_earned, set(m.charter_perks), m.founding_seed,
        m.hard_charter_active, m.ledger_units_moved, m.ledger_routes_established, set(m.ledger_routes_seen),
    )
    m.charters_completed, m.charter_points_earned, m.charter_perks, m.founding_seed = 0, 0, set(), 0
    m.hard_charter_active, m.ledger_units_moved, m.ledger_routes_established = False, 0, 0
    m.ledger_routes_seen = set()
    assert m.load_state(saved) is True
    assert snapshot == (
        m.charters_completed, m.charter_points_earned, set(m.charter_perks), m.founding_seed,
        m.hard_charter_active, m.ledger_units_moved, m.ledger_routes_established, set(m.ledger_routes_seen),
    )
    assert m.hard_charter_active is True and m.founding_seed != 0


def test_loading_a_save_without_the_keys_resets_them(game_env):
    m = game_env.module
    _one_trip(game_env)
    _renew(m)
    m.ledger_units_moved = 5  # the ledger key is written whenever anything was moved
    saved = m.get_state()
    assert "ledger" in saved
    saved.pop("charter")
    saved.pop("ledger", None)
    saved.pop("legacy")
    m.load_state(saved)
    assert m.charters_completed == 0 and m.charter_perks == set() and m.founding_seed == 0
    assert m.ledger_units_moved == 0 and m.ledger_routes_seen == set()


def test_an_old_legacy_save_migrates_to_charters_and_points(game_env):
    m = game_env.module
    saved = m.get_state()
    saved["legacy"] = {"level": 3, "achievements": []}
    assert "charter" not in saved
    m.load_state(saved)
    assert m.charters_completed == 3
    assert m.charter_points_earned == 3 * m.CHARTER_POINTS_PER_RENEWAL
    assert m.charter_perks == set() and m.founding_seed == 0


@pytest.mark.parametrize("bad", [
    "nope", 7, None, [], {"completed": True, "points": True, "seed": True},
    {"completed": -5, "points": 10**12, "seed": -1},
    {"completed": 1.5, "points": "9", "seed": [1]},
])
def test_a_tampered_charter_value_falls_back_to_defaults(game_env, bad):
    m = game_env.module
    saved = m.get_state()
    saved["charter"] = bad
    assert m.load_state(saved) is True
    assert m.charters_completed == 0 and m.charter_points_earned == 0 and m.founding_seed == 0
    assert m.charter_perks == set() and m.hard_charter_active is False


@pytest.mark.parametrize("perks", [
    "surveyed_lanes", 5, [["surveyed_lanes"]], [{"a": 1}], [None, 3, True, "not_a_perk"],
])
def test_tampered_perk_lists_never_crash_or_invent_perks(game_env, perks):
    m = game_env.module
    saved = m.get_state()
    saved["charter"] = {"completed": 2, "points": 50, "perks": perks}
    assert m.load_state(saved) is True
    assert m.charter_perks == set()


def test_only_known_affordable_perks_with_their_prerequisites_load(game_env):
    m = game_env.module
    saved = m.get_state()
    saved["charter"] = {"completed": 2, "points": 3, "perks": ["surveyed_lanes", "surveyed_lanes", "trusted_name", "waystation_network"]}
    m.load_state(saved)
    # trusted_name lacks its chain and is dropped; the other two cost 1 + 2 = 3, exactly affordable
    assert m.charter_perks == {"surveyed_lanes", "waystation_network"}
    saved["charter"] = {"completed": 2, "points": 2, "perks": ["surveyed_lanes", "waystation_network"]}
    m.load_state(saved)
    assert m.charter_perks == set()  # overspent: nothing is trusted


def test_a_hard_flag_needs_a_completed_charter_and_a_real_true(game_env):
    m = game_env.module
    saved = m.get_state()
    saved["charter"] = {"completed": 0, "points": 0, "hard": True}
    m.load_state(saved)
    assert m.hard_charter_active is False
    saved["charter"] = {"completed": 1, "points": 2, "hard": 1}
    m.load_state(saved)
    assert m.hard_charter_active is False
    saved["charter"] = {"completed": 1, "points": 2, "hard": True, "hard_next": True}
    m.load_state(saved)
    assert m.hard_charter_active is True and m.hard_charter_next is True


@pytest.mark.parametrize("bad", [
    "x", 3, {"units": True, "routes": -1, "hard_completed": 1.5},
    {"units": 10**15, "routes": "4"},
    {"routes_seen": "aurum"}, {"routes_seen": [["aurum"], ["aurum", "aurum"], ["aurum", 5], [{"a": 1}, "cryo"], "ab", None]},
])
def test_a_tampered_ledger_falls_back_safely(game_env, bad):
    m = game_env.module
    saved = m.get_state()
    saved["ledger"] = bad
    assert m.load_state(saved) is True
    assert m.ledger_units_moved == 0 and m.ledger_routes_established == 0 and m.ledger_hard_completed == 0
    assert m.ledger_routes_seen == set()


def test_valid_ledger_values_load(game_env):
    m = game_env.module
    saved = m.get_state()
    saved["ledger"] = {"units": 500, "routes": 4, "hard_completed": 1, "routes_seen": [["aurum", "verdant"], ["cryo", "helion"]]}
    m.load_state(saved)
    assert m.ledger_units_moved == 500 and m.ledger_routes_established == 4 and m.ledger_hard_completed == 1
    assert m.ledger_routes_seen == {frozenset(("aurum", "verdant")), frozenset(("cryo", "helion"))}


# ------------------------------------------------------------------- the UI

def test_the_panel_is_hidden_until_opened_and_toggles(game_env):
    el = game_env.elements
    game_env.module.render()
    assert el["charter-panel"].hidden is True
    game_env.toggle_charter()
    assert el["charter-panel"].hidden is False
    assert el["charter-toggle-button"].attributes["aria-expanded"] == "true"
    assert "Hide" in el["charter-toggle-button"].innerText
    game_env.toggle_charter()
    assert el["charter-panel"].hidden is True
    assert el["charter-toggle-button"].attributes["aria-expanded"] == "false"


def test_the_buy_buttons_reflect_points_prerequisites_and_ownership(game_env):
    m, el = game_env.module, game_env.elements
    _give_points(m, 1)
    game_env.toggle_charter()
    assert el["charter-perk-surveyed_lanes-buy-button"].disabled is False
    assert el["charter-perk-waystation_network-buy-button"].disabled is True
    assert "Surveyed Lanes" in el["charter-perk-waystation_network-status"].innerText
    assert "requires" in el["charter-perk-waystation_network-status"].innerText
    el["charter-perk-surveyed_lanes-buy-button"].dispatch("click", None)
    assert m.charter_perk("surveyed_lanes")
    button = el["charter-perk-surveyed_lanes-buy-button"]
    assert button.disabled is True and button.innerText == "Owned"
    assert "Owned" in el["charter-perk-surveyed_lanes-status"].innerText
    assert "aria-label" in button.attributes and "Surveyed Lanes" in button.attributes["aria-label"]


def test_buying_a_perk_goes_through_the_confirm_dialog(game_env):
    m = game_env.module
    asked = []

    class _Dialog:
        @staticmethod
        def ask(**options):
            asked.append(options)

    sys.modules["js"].window = types.SimpleNamespace(ConfirmDialog=_Dialog)
    try:
        _give_points(m, 1)
        game_env.toggle_charter()
        game_env.elements["charter-perk-surveyed_lanes-buy-button"].dispatch("click", None)
        assert len(asked) == 1 and not m.charter_perk("surveyed_lanes")
        assert asked[0]["id"] == "trade-empire-charter-perk-surveyed_lanes"
        assert "allowSkip" not in asked[0]
        asked[0]["onConfirm"]()
        assert m.charter_perk("surveyed_lanes")
    finally:
        del sys.modules["js"].window


def test_renewal_still_asks_every_time_and_mentions_the_charter(game_env):
    m = game_env.module
    asked = []

    class _Dialog:
        @staticmethod
        def ask(**options):
            asked.append(options)

    sys.modules["js"].window = types.SimpleNamespace(ConfirmDialog=_Dialog)
    try:
        _endgame(m)
        m.on_found_new_corporation()
        assert asked[0]["allowSkip"] is False
        assert asked[0]["confirmLabel"] == "Renew the Charter"
        assert "charter points" in asked[0]["message"]
    finally:
        del sys.modules["js"].window


def test_the_endgame_panel_previews_the_points(game_env):
    m, el = game_env.module, game_env.elements
    _endgame(m)
    m.render()
    assert f"{m.CHARTER_POINTS_PER_RENEWAL} charter points" in el["charter-renew-preview-display"].innerText
    assert el["found-new-corporation-button"].hidden is False


def test_the_summary_mentions_the_charter(game_env):
    m = game_env.module
    _renew(m)
    game_env.toggle_summary()
    text = " ".join(c.innerText for c in game_env.elements["summary-panel"].children)
    assert "Charter: 1 renewed" in text


def test_the_index_declares_the_panel_the_buttons_and_the_shortcut(game_env):
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    m = game_env.module
    for perk_id in m.CHARTER_PERKS:
        assert f'id="charter-perk-{perk_id}-buy-button"' in html
        assert f'id="charter-perk-{perk_id}-status"' in html
    for element_id in ("charter-toggle-button", "charter-panel", "hard-charter-toggle-button",
                       "ledger-units-display", "ledger-routes-display", "ledger-charters-display", "ledger-hard-display"):
        assert f'id="{element_id}"' in html
    assert 'toggle: "charter-toggle-button", panel: "charter-panel"' in html
    assert 'aria-controls="charter-panel"' in html


def test_the_light_theme_covers_the_charter_panel():
    from pathlib import Path
    css = (Path(__file__).resolve().parent.parent / "style.css").read_text(encoding="utf-8")
    light = css[css.index("Y11b light-theme polish"):]
    assert 'html[data-theme="light"] .charter-branch-title' in light
    assert 'html[data-theme="light"] .charter-ledger' in light
