"""Milestone 6: automation v1. A limited number of ships (2 of 4 in
this version) can be bought into fully autonomous operation for a flat
one-time cost. An automated ship loads whatever its colony produces and
departs for whichever colony needs it, every tick, with no further
input -- "a route can run itself."
"""


def test_ships_start_unautomated(game_env):
    for ship_id in game_env.module.ships:
        assert game_env.ship(ship_id).automated is False


def test_automate_ship_fails_without_enough_profit(game_env):
    assert game_env.module.total_profit < game_env.module.AUTOMATION_COST
    result = game_env.module.automate_ship("1")
    assert result is False
    assert game_env.ship("1").automated is False


def test_automate_ship_succeeds_with_enough_profit_and_deducts_cost(game_env):
    game_env.module.total_profit = 1000
    result = game_env.module.automate_ship("1")
    assert result is True
    assert game_env.ship("1").automated is True
    assert game_env.module.total_profit == 1000 - game_env.module.AUTOMATION_COST


def test_automated_ship_count_tracks_automated_ships(game_env):
    game_env.module.total_profit = 1000
    assert game_env.module.automated_ship_count() == 0
    game_env.module.automate_ship("1")
    assert game_env.module.automated_ship_count() == 1


def test_automation_slots_are_limited(game_env):
    game_env.module.total_profit = 10000
    for ship_id in ("1", "2"):
        assert game_env.module.automate_ship(ship_id) is True
    assert game_env.module.automation_slots_available() is False
    result = game_env.module.automate_ship("3")
    assert result is False
    assert game_env.ship("3").automated is False


def test_automating_an_already_automated_ship_is_a_noop(game_env):
    game_env.module.total_profit = 1000
    game_env.module.automate_ship("1")
    profit_after_first = game_env.module.total_profit
    result = game_env.module.automate_ship("1")
    assert result is False
    assert game_env.module.total_profit == profit_after_first


def test_colony_needing_finds_the_right_colony(game_env):
    # Ore is needed by Ferrum in this world's fixed cycle.
    assert game_env.module.colony_needing("ore") == "ferrum"
    assert game_env.module.colony_needing("water") == "helion"


def test_automated_ship_loads_itself_on_tick(game_env):
    game_env.module.total_profit = 1000
    game_env.module.automate_ship("1")  # docked at aurum, empty
    game_env.tick(1)
    assert game_env.ship("1").loaded


def test_automated_ship_departs_for_the_colony_that_needs_its_good(game_env):
    game_env.module.total_profit = 1000
    game_env.module.automate_ship("1")  # docked at aurum, produces ore
    game_env.tick(1)  # loads
    game_env.tick(1)  # departs
    assert game_env.ship("1").in_transit
    assert game_env.ship("1").destination == "ferrum"  # needs ore


def test_automated_ship_completes_a_full_cycle_without_any_manual_input(game_env):
    game_env.module.total_profit = 1000
    starting_profit = game_env.module.total_profit
    game_env.module.automate_ship("1")
    # tick 1: loads. tick 2: departs. ticks 3-7: transit, arriving (and
    # immediately reloading, since run_automation runs after transit
    # resolution within the same tick) on tick 7.
    game_env.tick(2 + game_env.module.TRAVEL_TICKS)
    assert game_env.ship("1").location == "ferrum"
    assert game_env.ship("1").loaded  # already reloaded itself, same tick as arrival
    assert game_env.module.total_profit > starting_profit - game_env.module.AUTOMATION_COST


def test_manual_ships_are_unaffected_by_automating_a_different_ship(game_env):
    game_env.module.total_profit = 1000
    game_env.module.automate_ship("1")
    game_env.tick(2 + game_env.module.TRAVEL_TICKS)
    assert game_env.ship("2").location == "verdant"
    assert not game_env.ship("2").loaded


def test_render_hides_manual_controls_for_automated_ship(game_env):
    game_env.module.total_profit = 1000
    game_env.module.automate_ship("1")
    game_env.module.render()
    assert game_env.elements["ship-1-load-button"].hidden is True
    assert game_env.elements["ship-1-depart-ferrum-button"].hidden is True


def test_render_shows_automated_status_text(game_env):
    game_env.module.total_profit = 1000
    game_env.module.automate_ship("1")
    game_env.module.render()
    assert "Automated" in game_env.elements["ship-1-status"].innerText


def test_automate_button_click_dispatches(game_env):
    game_env.module.total_profit = 1000
    game_env.module.render()
    game_env.automate(ship_id="1")
    assert game_env.ship("1").automated is True


def test_automate_button_disabled_without_enough_profit(game_env):
    game_env.module.render()
    assert game_env.elements["ship-1-automate-button"].disabled is True


def test_automate_button_shows_automated_once_active(game_env):
    game_env.module.total_profit = 1000
    game_env.module.automate_ship("1")
    game_env.module.render()
    assert game_env.elements["ship-1-automate-button"].innerText == "Automated"
    assert game_env.elements["ship-1-automate-button"].disabled is True


def test_render_shows_automation_slots_used(game_env):
    game_env.module.total_profit = 1000
    game_env.module.automate_ship("1")
    game_env.module.render()
    assert "1/2" in game_env.elements["automation-slots-display"].innerText
