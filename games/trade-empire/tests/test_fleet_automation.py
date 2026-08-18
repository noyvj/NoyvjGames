"""Milestone 12: fleet-level automation. With every good needed by
exactly one colony, a single automated ship's route is already fixed --
there's no destination choice to prioritize on its own route. Fleet
Priority mode instead lets an idle automated ship abandon its home
shuttle and reposition empty to whichever producer feeds the fleet's
most under-served colony, rather than blindly reloading its local
produce every tick. Off by default, so Milestone 6's per-route
autopilot behavior is preserved exactly when the mode isn't switched on.
"""


def test_fleet_priority_defaults_to_disabled(game_env):
    assert game_env.module.fleet_priority_enabled is False


def test_toggling_fleet_priority_flips_the_flag(game_env):
    game_env.toggle_fleet_priority()
    assert game_env.module.fleet_priority_enabled is True
    game_env.toggle_fleet_priority()
    assert game_env.module.fleet_priority_enabled is False


def test_most_urgent_colony_is_the_one_with_lowest_satisfaction(game_env):
    module = game_env.module
    for state in module.colony_states.values():
        state.need_satisfaction = 0.5
    module.colony_states["cryo"].need_satisfaction = 0.1
    assert module.most_urgent_colony() == "cryo"


def test_colony_producing_reverses_colony_needing(game_env):
    module = game_env.module
    for colony_id, colony in module.COLONIES.items():
        assert module.colony_producing(colony["produces"]) == colony_id


def test_automation_without_fleet_priority_still_loads_locally(game_env):
    # Milestone 6 baseline: fleet priority off means an idle automated
    # ship just loads whatever its own colony produces, regardless of
    # which colony is most under-served fleet-wide.
    module = game_env.module
    module.colony_states["helion"].need_satisfaction = 0.0  # most urgent
    module.total_profit = 1000
    module.automate_ship("1")  # ship 1 starts docked at aurum
    module.run_automation()
    ship = game_env.ship("1")
    assert ship.location == "aurum"
    assert ship.loaded
    assert ship.cargo_good == module.COLONIES["aurum"]["produces"]


def test_fleet_priority_repositions_idle_ship_toward_urgent_producer(game_env):
    module = game_env.module
    game_env.toggle_fleet_priority()
    # Grain (verdant's produce) satisfies aurum's need -- make aurum the
    # most urgent colony so an idle ship elsewhere should head for verdant.
    module.colony_states["aurum"].need_satisfaction = 0.0
    module.total_profit = 1000
    module.automate_ship("3")  # ship 3 starts docked at ferrum, empty
    module.run_automation()
    ship = game_env.ship("3")
    assert ship.in_transit
    assert ship.destination == "verdant"
    assert not ship.loaded  # repositioned empty, not carrying cargo


def test_fleet_priority_does_not_reposition_a_ship_already_at_the_right_producer(game_env):
    module = game_env.module
    game_env.toggle_fleet_priority()
    module.colony_states["aurum"].need_satisfaction = 0.0
    module.total_profit = 1000
    module.automate_ship("2")  # ship 2 starts docked at verdant, which
    module.run_automation()  # already produces aurum's need (grain)
    ship = game_env.ship("2")
    assert ship.docked
    assert ship.location == "verdant"
    assert ship.loaded  # loaded normally instead of repositioning nowhere


def test_reposition_requires_the_ship_to_be_empty(game_env):
    module = game_env.module
    ship = game_env.ship("1")
    ship.load()
    assert ship.reposition("verdant") is False


def test_reposition_moves_ship_out_of_dock(game_env):
    module = game_env.module
    ship = game_env.ship("1")  # docked at aurum, empty
    assert ship.reposition("ferrum") is True
    assert ship.in_transit
    assert ship.origin == "aurum"
    assert ship.destination == "ferrum"


def test_repositioned_ship_arrives_and_docks_without_a_sale(game_env):
    module = game_env.module
    ship = game_env.ship("1")
    ship.reposition("ferrum")
    total_profit_before = module.total_profit
    game_env.tick(module.TRAVEL_TICKS)
    assert ship.docked
    assert ship.location == "ferrum"
    assert module.total_profit == total_profit_before  # no cargo, no sale


def test_fleet_priority_toggle_button_updates_label(game_env):
    button = game_env.elements["fleet-priority-button"]
    assert "OFF" in button.innerText
    game_env.toggle_fleet_priority()
    assert "ON" in button.innerText
