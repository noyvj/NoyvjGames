"""Milestone 2: a third colony (Ferrum Forge) turns the fixed A<->B pair
into a real triangle, and a second ship gives the player two
independent, manually-assigned routes to run rather than one.
"""


def test_three_colonies_exist(game_env):
    # Renamed in spirit by Milestone 5 (which adds two more), but kept
    # as "at least the original triangle" so this file still documents
    # Milestone 2's own guarantee.
    assert {"aurum", "verdant", "ferrum"}.issubset(game_env.module.COLONIES)


def test_two_ships_exist(game_env):
    assert {"1", "2"}.issubset(game_env.module.ships)


def test_ships_start_at_different_colonies(game_env):
    assert game_env.ship("1").location == "aurum"
    assert game_env.ship("2").location == "verdant"


def test_each_colony_produces_a_different_good_needed_elsewhere(game_env):
    colonies = game_env.module.COLONIES
    produced = {c["produces"] for c in colonies.values()}
    needed = {c["needs"] for c in colonies.values()}
    assert produced == needed  # a genuine cycle: everything produced is needed somewhere


def test_ship_can_depart_to_either_other_colony(game_env):
    ship = game_env.ship("1")  # docked at aurum
    assert {"verdant", "ferrum"}.issubset(ship.other_colonies())
    assert "aurum" not in ship.other_colonies()


def test_ships_operate_independently(game_env):
    game_env.load(ship_id="1")
    game_env.depart("ferrum", ship_id="1")
    assert game_env.ship("2").location == "verdant"
    assert not game_env.ship("2").in_transit


def test_both_ships_can_run_simultaneously(game_env):
    game_env.load(ship_id="1")
    game_env.depart("ferrum", ship_id="1")
    game_env.load(ship_id="2")
    game_env.depart("aurum", ship_id="2")
    assert game_env.ship("1").in_transit
    assert game_env.ship("2").in_transit
    assert game_env.ship("1").destination == "ferrum"
    assert game_env.ship("2").destination == "aurum"


def test_tick_advances_both_ships_transits(game_env):
    game_env.load(ship_id="1")
    game_env.depart("ferrum", ship_id="1")
    game_env.load(ship_id="2")
    game_env.depart("aurum", ship_id="2")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    assert game_env.ship("1").location == "ferrum"
    assert game_env.ship("2").location == "aurum"


def test_profit_accumulates_from_both_ships(game_env):
    game_env.load(ship_id="1")
    game_env.depart("ferrum", ship_id="1")  # sells 10 ore @ 8 = 80
    game_env.load(ship_id="2")
    game_env.depart("aurum", ship_id="2")  # sells 10 grain @ 6 = 60
    game_env.tick(game_env.module.TRAVEL_TICKS)
    assert game_env.total_profit == 80 + 60


def test_ferrum_produces_machinery(game_env):
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    game_env.load(ship_id="1")  # now at verdant, loads grain
    game_env.depart("ferrum", ship_id="1")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    assert game_env.ship("1").location == "ferrum"
    game_env.load(ship_id="1")
    assert game_env.ship("1").cargo_good == "machinery"


def test_render_shows_both_ship_panels_independently(game_env):
    game_env.load(ship_id="1")
    game_env.module.render()
    assert "loaded with" in game_env.elements["ship-1-status"].innerText
    assert "loaded with" not in game_env.elements["ship-2-status"].innerText


def test_depart_button_for_own_colony_stays_hidden(game_env):
    game_env.load(ship_id="1")  # docked at aurum
    game_env.module.render()
    assert game_env.elements["ship-1-depart-aurum-button"].hidden is True
    assert game_env.elements["ship-1-depart-verdant-button"].hidden is False
    assert game_env.elements["ship-1-depart-ferrum-button"].hidden is False
