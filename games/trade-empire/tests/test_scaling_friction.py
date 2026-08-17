"""Milestone 5: manual scaling friction. No new mechanic -- two more
colonies (Cryo, Helion, needing exactly what the other produces) and
two more ships, purely to make manual play genuinely busy and motivate
Milestone 6's automation. Every existing system (need satisfaction,
market prices, routes) already generalizes to the larger roster without
code changes.
"""


def test_five_colonies_exist(game_env):
    assert set(game_env.module.COLONIES) == {"aurum", "verdant", "ferrum", "cryo", "helion"}


def test_four_ships_exist(game_env):
    assert set(game_env.module.ships) == {"1", "2", "3", "4"}


def test_new_ships_start_at_new_and_old_colonies(game_env):
    assert game_env.ship("3").location == "ferrum"
    assert game_env.ship("4").location == "cryo"


def test_cryo_and_helion_need_exactly_each_other(game_env):
    cryo = game_env.module.COLONIES["cryo"]
    helion = game_env.module.COLONIES["helion"]
    assert cryo["needs"] == helion["produces"]
    assert helion["needs"] == cryo["produces"]


def test_every_produced_good_is_needed_somewhere_across_all_five(game_env):
    colonies = game_env.module.COLONIES
    produced = {c["produces"] for c in colonies.values()}
    needed = {c["needs"] for c in colonies.values()}
    assert produced == needed


def test_all_five_colonies_have_flavor_text(game_env):
    for colony_id in game_env.module.COLONIES:
        assert colony_id in game_env.module.COLONY_FLAVOR
        assert len(game_env.module.COLONY_FLAVOR[colony_id]) > 0


def test_any_ship_can_reach_the_new_colonies_too(game_env):
    ship = game_env.ship("1")  # docked at aurum, part of the original triangle
    assert "cryo" in ship.other_colonies()
    assert "helion" in ship.other_colonies()


def test_need_system_generalizes_to_new_colonies(game_env):
    cryo_state = game_env.module.colony_states["cryo"]
    assert cryo_state.need_satisfaction == game_env.module.STARTING_NEED_SATISFACTION
    game_env.load(ship_id="4")  # docked at cryo, loads water
    game_env.depart("helion", ship_id="4")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    helion_state = game_env.module.colony_states["helion"]
    assert helion_state.need_satisfaction > game_env.module.STARTING_NEED_SATISFACTION


def test_market_system_generalizes_to_new_goods(game_env):
    assert set(game_env.module.market_multiplier) == {"ore", "grain", "machinery", "water", "energy"}
    game_env.load(ship_id="4")
    game_env.depart("helion", ship_id="4")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    assert game_env.module.market_multiplier["water"] < 1.0


def test_all_four_ships_can_run_simultaneously(game_env):
    game_env.load(ship_id="1")
    game_env.depart("ferrum", ship_id="1")
    game_env.load(ship_id="2")
    game_env.depart("aurum", ship_id="2")
    game_env.load(ship_id="3")
    game_env.depart("verdant", ship_id="3")
    game_env.load(ship_id="4")
    game_env.depart("helion", ship_id="4")
    for ship_id in ("1", "2", "3", "4"):
        assert game_env.ship(ship_id).in_transit


def test_profit_accumulates_across_all_four_ships(game_env):
    game_env.load(ship_id="1")
    game_env.depart("ferrum", ship_id="1")  # ore
    game_env.load(ship_id="2")
    game_env.depart("aurum", ship_id="2")  # grain
    game_env.load(ship_id="3")
    game_env.depart("verdant", ship_id="3")  # machinery
    game_env.load(ship_id="4")
    game_env.depart("helion", ship_id="4")  # water
    game_env.tick(game_env.module.TRAVEL_TICKS)
    assert game_env.total_profit == 80 + 60 + 100 + 50


def test_render_covers_all_five_colonies_without_error(game_env):
    game_env.module.render()  # would KeyError/raise if any colony element were missing
    for colony_id in game_env.module.COLONIES:
        assert len(game_env.elements[f"colony-{colony_id}-need-display"].innerText) > 0


def test_render_covers_all_four_ships_without_error(game_env):
    game_env.module.render()
    for ship_id in game_env.module.ships:
        assert len(game_env.elements[f"ship-{ship_id}-status"].innerText) > 0
