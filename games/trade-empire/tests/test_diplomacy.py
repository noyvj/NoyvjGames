"""J23 -- diplomatic relations: units delivered across star systems raise a
relations level, a small permanent bonus on every sale's proceeds."""


def _trip(game, origin, destination, good, qty):
    ship = game.ships[next(iter(game.ships))]
    ship.location = None
    ship.origin = origin
    ship.destination = destination
    ship.cargo_good = good
    ship.cargo_qty = qty
    ship.transit_ticks_remaining = 1
    return ship.advance_transit()


def _unlock_kepler(game_env):
    game_env.module.research_points = 10_000
    game_env.module.unlocked_research.add("automation_slot_2")
    game_env.unlock_research("galaxy_expansion")


def test_no_bonus_before_any_cross_system_trade(game_env):
    game = game_env.module
    assert game.diplomacy_level() == 0 and game.diplomacy_multiplier() == 1.0
    result = _trip(game, "aurum", "ferrum", game.ORE, 10)
    assert result[2] == 10 * game.current_sell_price(game.ORE)
    assert game.cross_system_units == 0


def test_only_trips_that_cross_systems_count(game_env):
    game = game_env.module
    _unlock_kepler(game_env)
    _trip(game, "aurum", "ferrum", game.ORE, 10)  # same system
    assert game.cross_system_units == 0
    _trip(game, "aurum", "kepler_c", game.ORE, 12)  # home -> Kepler
    assert game.cross_system_units == 12


def test_levels_unlock_at_the_thresholds_and_scale_the_bonus(game_env):
    game = game_env.module
    for units, level in [(0, 0), (24, 0), (25, 1), (75, 2), (150, 3), (5000, 3)]:
        game.cross_system_units = units
        assert game.diplomacy_level() == level
        assert abs(game.diplomacy_multiplier() - (1 + level * game.DIPLOMACY_BONUS_PER_LEVEL)) < 1e-9
    game.cross_system_units = 10
    assert game.diplomacy_units_to_next_level() == 15
    game.cross_system_units = 150
    assert game.diplomacy_units_to_next_level() == 0


def test_the_bonus_applies_to_sale_proceeds(game_env):
    game = game_env.module
    _unlock_kepler(game_env)
    game.cross_system_units = game.DIPLOMACY_THRESHOLDS[0]
    base = 10 * game.current_sell_price(game.ORE)
    result = _trip(game, "aurum", "ferrum", game.ORE, 10)
    assert result[2] == int(round(base * (1 + game.DIPLOMACY_BONUS_PER_LEVEL)))
    assert result[2] > base


def test_status_line_hidden_until_a_second_system_is_reachable(game_env):
    game = game_env.module
    game.render_market()
    assert game_env.elements["diplomacy-status"].hidden is True
    _unlock_kepler(game_env)
    game.cross_system_units = 10
    game.render_market()
    status = game_env.elements["diplomacy-status"]
    assert status.hidden is False
    assert "level 0 of 3" in status.innerText and "15 more" in status.innerText


def test_state_round_trip_and_bad_saved_values(game_env):
    game = game_env.module
    game.cross_system_units = 80
    saved = game.get_state()
    assert saved["cross_system_units"] == 80
    game.cross_system_units = 0
    game.load_state(saved)
    assert game.cross_system_units == 80
    for bad in (-3, 1e30, True, "many", None):
        saved["cross_system_units"] = bad
        game.load_state(saved)
        assert game.cross_system_units == 0
    del saved["cross_system_units"]
    game.cross_system_units = 5
    game.load_state(saved)
    assert game.cross_system_units == 0
