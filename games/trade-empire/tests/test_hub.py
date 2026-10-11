"""J-21 / J-22 -- Hub & Spoke: a Distribution Hub that halves trips to its same-system neighbours, caps its own
good's stockpile, steers Fleet Priority between equally urgent colonies, and is drawn with a thick ring."""

import json

import pytest


def _open(m, credits=5000):
    m.unlocked_research.add(m.HUB_RESEARCH)
    m.total_profit = m.max_profit_ever = credits
    return m


def test_locked_until_the_automation_expansion(game_env):
    m = game_env.module
    m.total_profit = 5000
    assert not m.hub_open() and m.set_hub("aurum") is False
    game_env.elements["lab-toggle-button"].dispatch("click", None)
    assert "Locked" in game_env.elements["hub-status"].innerText


def test_setting_a_hub_costs_credits_and_moving_costs_again(game_env):
    m = _open(game_env.module)
    assert m.set_hub("ferrum") is True and m.total_profit == 5000 - m.HUB_COST
    assert m.set_hub("ferrum") is False  # already the hub
    assert m.set_hub("aurum") is True and m.total_profit == 5000 - 2 * m.HUB_COST and m.hub_colony == "aurum"
    assert m.records["hubs_set"] == 2


def test_hub_needs_enough_credits_a_real_and_reachable_colony(game_env):
    m = _open(game_env.module, credits=119)
    assert m.set_hub("aurum") is False
    m.total_profit = 1000
    assert m.set_hub("kepler_a") is False and m.set_hub("nope") is False and m.set_hub(None) is False
    assert m.set_hub(["aurum"]) is False


def test_clearing_is_free(game_env):
    m = _open(game_env.module)
    m.set_hub("aurum")
    before = m.total_profit
    assert m.clear_hub() is True and m.hub_colony is None and m.total_profit == before
    assert m.clear_hub() is False


def test_trips_to_and_from_the_hub_take_half_as_long_rounded_up(game_env):
    m = _open(game_env.module)
    assert m.hub_trip_ticks("aurum", "verdant", 5) == 5
    m.set_hub("aurum")
    assert m.hub_trip_ticks("aurum", "verdant", 5) == 3
    assert m.hub_trip_ticks("verdant", "aurum", 5) == 3
    assert m.hub_trip_ticks("verdant", "ferrum", 5) == 5  # neither end is the hub
    assert m.hub_trip_ticks("aurum", "verdant", 1) == 1 and m.hub_trip_ticks("aurum", "verdant", 2) == 1
    assert m.hub_trip_ticks("aurum", "aurum", 5) == 5


def test_a_trip_to_another_system_is_not_halved(game_env):
    m = _open(game_env.module)
    m.unlocked_research.add("galaxy_expansion")
    for cid in m.EXPANSION_COLONIES:
        m.colony_states.setdefault(cid, m.ColonyState(cid))
    m.set_hub("aurum")
    assert m.hub_trip_ticks("aurum", "kepler_a", 5) == 5
    m.set_hub("kepler_a")
    assert m.hub_trip_ticks("kepler_a", "kepler_b", 5) == 3


def test_a_real_ship_departing_from_the_hub_arrives_sooner(game_env):
    m = _open(game_env.module)
    plain = m.ships["3"]
    plain.load()
    plain.depart("aurum")
    m.set_hub("aurum")
    ship = m.ships["1"]
    ship.load()
    ship.depart("verdant")
    assert ship.transit_total_ticks == 3 and plain.transit_total_ticks == 5
    game_env.tick(3)
    assert ship.location == "verdant"


def test_without_a_hub_travel_times_are_untouched(game_env):
    m = game_env.module
    ship = m.ships["1"]
    ship.load()
    ship.depart("verdant")
    assert ship.transit_total_ticks == m.TRAVEL_TICKS


def test_the_hubs_own_good_has_a_smaller_stockpile(game_env):
    m = _open(game_env.module)
    assert m.stockpile_capacity(m.ORE) == m.STOCKPILE_CAPACITY
    m.set_hub("aurum")  # Aurum makes ore
    assert m.stockpile_capacity(m.ORE) == m.HUB_STOCKPILE_CAP and m.stockpile_capacity(m.GRAIN) == 15
    m.stockpile[m.ORE] = m.HUB_STOCKPILE_CAP
    assert m.can_stockpile_buy(m.ORE) is False
    m.stockpile[m.ORE] = m.HUB_STOCKPILE_CAP - 3
    m.buy_stockpile(m.ORE)
    assert m.stockpile[m.ORE] == m.HUB_STOCKPILE_CAP  # topped up to the cap, not 5 more


def test_stock_above_the_new_cap_is_kept_not_destroyed(game_env):
    m = _open(game_env.module)
    m.stockpile[m.ORE] = 14
    m.set_hub("aurum")
    assert m.stockpile[m.ORE] == 14 and m.can_stockpile_buy(m.ORE) is False
    assert m.sell_stockpile(m.ORE) is True


def test_the_market_row_shows_the_hub_cap(game_env):
    m = _open(game_env.module)
    m.set_hub("aurum")
    m.render()
    assert f"/{m.HUB_STOCKPILE_CAP}" in game_env.elements["stockpile-ore-status"].innerText
    assert "/15" in game_env.elements["stockpile-grain-status"].innerText


# ---------------------------------------------------------------- Fleet Priority

def test_fleet_priority_target_is_the_plain_urgent_colony_without_a_hub(game_env):
    m = game_env.module
    m.colony_states["ferrum"].need_satisfaction = 0.2
    m.colony_states["aurum"].need_satisfaction = 0.21
    assert m.fleet_priority_target(m.ships["1"]) == m.most_urgent_colony() == "ferrum"


def test_with_a_hub_a_nearly_as_urgent_colony_that_is_quicker_to_serve_wins(game_env):
    m = _open(game_env.module)
    # Ship 1 sits at Aurum (hub). Ferrum needs ore (made at Aurum, the hub's neighbour trip is halved only for hub trips).
    m.set_hub("verdant")  # Verdant makes grain, which Aurum needs
    ship = m.ships["1"]
    ship.location = "aurum"
    for state in m.colony_states.values():
        state.need_satisfaction = 0.9
    m.colony_states["ferrum"].need_satisfaction = 0.20   # producer of its need (ore) is Aurum: 0 ticks away
    m.colony_states["aurum"].need_satisfaction = 0.22    # producer of its need (grain) is the hub Verdant: 3 ticks
    assert m.most_urgent_colony() == "ferrum"
    assert m.fleet_priority_target(ship) == "ferrum"
    ship.location = "ferrum"
    # from Ferrum: Aurum's need is made at the hub (halved, 3) and Ferrum's own need is made at Aurum (5, not hub)
    assert m.fleet_priority_target(ship) == "aurum"


def test_a_clearly_more_urgent_colony_is_never_skipped(game_env):
    m = _open(game_env.module)
    m.set_hub("verdant")
    for state in m.colony_states.values():
        state.need_satisfaction = 0.9
    m.colony_states["ferrum"].need_satisfaction = 0.1
    m.colony_states["aurum"].need_satisfaction = 0.3
    m.ships["1"].location = "ferrum"
    assert m.fleet_priority_target(m.ships["1"]) == "ferrum"


def test_automation_uses_the_target_and_still_repositions(game_env):
    m = _open(game_env.module)
    m.set_hub("verdant")
    m.set_fleet_priority(True)
    m.ships["1"].automated = True
    for state in m.colony_states.values():
        state.need_satisfaction = 0.9
    m.colony_states["ferrum"].need_satisfaction = 0.1
    m.ships["1"].location = "cryo"
    m.run_automation()
    assert m.ships["1"].in_transit and m.ships["1"].destination == "aurum"  # Aurum makes ore, which Ferrum needs


# ---------------------------------------------------------------- map and UI

def test_the_map_draws_a_thick_ring_and_the_word_hub(game_env):
    m = _open(game_env.module)
    m.set_hub("aurum")
    ctx = game_env.elements["map-canvas"].getContext("2d")
    ctx.calls.clear()
    m.render()
    texts = [args[0] for name, args in ctx.calls if name == "fillText"]
    assert "HUB" in texts
    rings = [args for name, args in ctx.calls if name == "arc" and args[2] == m.NODE_RADIUS + 3]
    assert len(rings) == 1
    assert "Distribution Hub" in game_env.elements["map-canvas"].title and "half as long" in game_env.elements["map-canvas"].title


def test_no_ring_or_tooltip_without_a_hub(game_env):
    m = game_env.module
    ctx = game_env.elements["map-canvas"].getContext("2d")
    ctx.calls.clear()
    m.render()
    assert "HUB" not in [args[0] for name, args in ctx.calls if name == "fillText"]
    assert "Distribution Hub" not in game_env.elements["map-canvas"].title


def test_the_buttons_set_move_and_clear_the_hub(game_env):
    m = _open(game_env.module)
    el = game_env.elements
    el["lab-toggle-button"].dispatch("click", None)
    assert el["hub-set-aurum-button"].hidden is False and el["hub-set-kepler_a-button"].hidden is True
    assert el["hub-clear-button"].hidden is True and "No hub set" in el["hub-status"].innerText
    el["hub-set-ferrum-button"].dispatch("click", None)
    assert m.hub_colony == "ferrum" and el["hub-set-ferrum-button"].hidden is True
    assert "Distribution Hub: Ferrum Forge" in el["hub-status"].innerText
    assert "Move the hub to" in el["hub-set-aurum-button"].innerText
    el["hub-clear-button"].dispatch("click", None)
    assert m.hub_colony is None


def test_the_buttons_disable_when_you_cannot_afford_it(game_env):
    _open(game_env.module, credits=10)
    game_env.elements["lab-toggle-button"].dispatch("click", None)
    assert game_env.elements["hub-set-aurum-button"].disabled is True


def test_first_hub_achievement(game_env):
    m = _open(game_env.module)
    assert "first_hub" not in m.achievement_ids_earned()
    m.set_hub("aurum")
    assert "first_hub" in m.achievement_ids_earned()


# ---------------------------------------------------------------------- saves

def test_nothing_saved_until_a_hub_is_set(game_env):
    assert "hub" not in game_env.module.get_state()


def test_hub_round_trips(game_env):
    m = _open(game_env.module)
    m.set_hub("ferrum")
    state = json.loads(json.dumps(m.get_state()))
    assert state["hub"] == "ferrum"
    m.hub_colony = None
    m.load_state(state)
    assert m.hub_colony == "ferrum"


@pytest.mark.parametrize("raw", ["nope", 3, ["aurum"], {"a": 1}, True, "kepler_a", "", None])
def test_tampered_hub_values_are_dropped(game_env, raw):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["hub"] = raw
    assert m.load_state(state) is True and m.hub_colony is None


def test_a_renewal_clears_the_hub_but_keeps_the_count(game_env):
    m = _open(game_env.module)
    m.set_hub("aurum")
    m.endgame_reached = True
    m.found_new_corporation()
    assert m.hub_colony is None and m.records["hubs_set"] == 1


def test_sandbox_round_trip_keeps_the_real_hub(game_env):
    m = _open(game_env.module)
    m.set_hub("aurum")
    before = json.dumps(m.get_state(), sort_keys=True)
    m.sandbox_enter()
    assert m.hub_colony is None
    m.sandbox_leave()
    assert json.dumps(m.get_state(), sort_keys=True) == before
