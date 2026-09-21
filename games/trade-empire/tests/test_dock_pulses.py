"""J10 -- a brief docking/undocking pulse on the map."""


def _ship_docked_with_cargo(game, colony="aurum"):
    ship = game.ships["1"]
    ship.location = colony
    ship.cargo_good = game.ORE
    ship.cargo_qty = 5
    return ship


def test_departing_adds_an_undock_pulse_at_the_origin(game_env):
    game = game_env.module
    game.dock_pulses.clear()
    ship = _ship_docked_with_cargo(game)
    assert ship.depart("ferrum")
    assert ["aurum", "undock", 0] in game.dock_pulses


def test_arriving_adds_a_dock_pulse_at_the_destination(game_env):
    game = game_env.module
    game.dock_pulses.clear()
    ship = game.ships["1"]
    ship.location = None
    ship.origin, ship.destination = "aurum", "ferrum"
    ship.cargo_good, ship.cargo_qty = game.ORE, 5
    ship.transit_ticks_remaining = 1
    ship.advance_transit()
    assert ["ferrum", "dock", 0] in game.dock_pulses


def test_pulses_age_each_tick_and_expire(game_env):
    game = game_env.module
    game.dock_pulses[:] = [["aurum", "dock", 0]]
    for expected_age in range(1, game.DOCK_PULSE_TICKS):
        game.age_dock_pulses()
        assert game.dock_pulses == [["aurum", "dock", expected_age]]
    game.age_dock_pulses()
    assert game.dock_pulses == []


def test_undock_rings_grow_and_dock_rings_close_in(game_env):
    game = game_env.module
    undock = [game.dock_pulse_radius("undock", a) for a in range(game.DOCK_PULSE_TICKS)]
    dock = [game.dock_pulse_radius("dock", a) for a in range(game.DOCK_PULSE_TICKS)]
    assert undock == sorted(undock) and undock[0] < undock[-1]
    assert dock == sorted(dock, reverse=True) and dock[0] > dock[-1]


def _arc_count_after_render(game_env):
    game = game_env.module
    ctx = game_env.elements["map-canvas"].getContext("2d")
    ctx.calls.clear()
    game.render_map()
    return len([1 for name, _ in ctx.calls if name == "arc"])


def test_the_map_draws_a_ring_for_each_live_pulse(game_env):
    game = game_env.module
    game.dock_pulses.clear()
    baseline = _arc_count_after_render(game_env)
    game.dock_pulses[:] = [["aurum", "dock", 0], ["ferrum", "undock", 1]]
    assert _arc_count_after_render(game_env) == baseline + 2


def test_no_pulses_are_drawn_with_reduced_motion(game_env):
    game = game_env.module
    game.dock_pulses.clear()
    baseline = _arc_count_after_render(game_env)
    game.dock_pulses[:] = [["aurum", "dock", 0]]
    assert _arc_count_after_render(game_env) == baseline + 1
    game._reduced_motion_on = lambda: True
    assert _arc_count_after_render(game_env) == baseline


def test_pulses_for_locked_system_colonies_are_ignored(game_env):
    game = game_env.module
    game.dock_pulses.clear()
    baseline = _arc_count_after_render(game_env)
    game.dock_pulses[:] = [["kepler_a", "dock", 0]]
    assert _arc_count_after_render(game_env) == baseline
