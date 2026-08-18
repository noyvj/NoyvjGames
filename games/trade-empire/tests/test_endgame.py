"""Milestone 14: endgame. A soft win-state -- reaching a fully
automated fleet, Fleet Priority, and the Kepler Cluster all at once is
narrated as the player's pattern spreading to an abstracted, growing
background galaxy that trickles in passive revenue. Deliberately not a
literal simulation of hundreds of colonies (impractical, and no more
meaningful to look at); the sandbox never locks or ends regardless.
"""


def _meet_endgame_criteria(game_env):
    """Automates every ship, switches on Fleet Priority, and unlocks
    Galaxy Expansion -- the exact criteria endgame_criteria_met() checks."""
    module = game_env.module
    module.total_profit = 10_000
    for ship_id in module.ships:
        module.automate_ship(ship_id)
    game_env.toggle_fleet_priority()
    module.research_points = 1000
    game_env.unlock_research("galaxy_expansion")


def test_endgame_not_reached_by_default(game_env):
    assert game_env.module.endgame_reached is False


def test_endgame_criteria_requires_all_three_conditions(game_env):
    module = game_env.module
    module.total_profit = 10_000
    for ship_id in module.ships:
        module.automate_ship(ship_id)
    # Fleet fully automated, but Fleet Priority is off and Kepler isn't
    # unlocked yet -- criteria shouldn't be met.
    assert module.endgame_criteria_met() is False


def test_endgame_reached_once_all_criteria_met(game_env):
    module = game_env.module
    _meet_endgame_criteria(game_env)
    assert module.endgame_criteria_met() is True
    game_env.tick(1)
    assert module.endgame_reached is True


def test_endgame_is_sticky_even_if_fleet_priority_is_later_toggled_off(game_env):
    module = game_env.module
    _meet_endgame_criteria(game_env)
    game_env.tick(1)
    assert module.endgame_reached is True
    game_env.toggle_fleet_priority()  # turn it back off
    game_env.tick(1)
    assert module.endgame_reached is True  # still reached -- it's a one-way flag


def test_background_world_count_grows_after_endgame_and_caps(game_env):
    module = game_env.module
    _meet_endgame_criteria(game_env)
    game_env.tick(1)  # the reaching tick itself already counts as tick 1
    assert module.background_world_count() == module.ENDGAME_BACKGROUND_WORLDS_PER_TICK
    game_env.tick(5)
    assert module.background_world_count() == 6 * module.ENDGAME_BACKGROUND_WORLDS_PER_TICK
    module.ticks_since_endgame = 10_000  # far past the cap
    assert module.background_world_count() == module.ENDGAME_BACKGROUND_WORLD_CAP


def test_background_revenue_adds_to_total_profit_each_tick_after_endgame(game_env):
    module = game_env.module
    _meet_endgame_criteria(game_env)
    game_env.tick(1)
    profit_before = module.total_profit
    game_env.tick(1)
    assert module.total_profit > profit_before


def test_no_background_revenue_before_endgame(game_env):
    module = game_env.module
    profit_before = module.total_profit
    game_env.tick(5)
    assert module.total_profit == profit_before  # nothing automated, no sales, no background


def test_endgame_panel_hidden_before_reached(game_env):
    assert game_env.elements["endgame-panel"].hidden is True


def test_endgame_panel_visible_once_reached(game_env):
    module = game_env.module
    _meet_endgame_criteria(game_env)
    game_env.tick(1)
    assert game_env.elements["endgame-panel"].hidden is False
    assert "worlds" in game_env.elements["endgame-worlds-display"].innerText
