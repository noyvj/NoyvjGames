"""Milestone 11: ships on the map. Every ship (automated or manual, so
the map stays useful during manual play too) renders as a moving dot,
interpolated between origin and destination using the trip's own fixed
tick count at departure time -- so a ship already mid-flight isn't
retroactively distorted if Fast Ships research changes travel time for
future departures.
"""

import pytest


def test_docked_ship_position_matches_its_colony_node(game_env):
    ship = game_env.ship("1")  # docked at aurum
    assert game_env.module.ship_map_position(ship) == game_env.module.NODE_POSITIONS["aurum"]


def test_in_transit_ship_starts_at_origin(game_env):
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    ship = game_env.ship("1")
    x, y = game_env.module.ship_map_position(ship)
    origin_x, origin_y = game_env.module.NODE_POSITIONS["aurum"]
    assert x == pytest.approx(origin_x)
    assert y == pytest.approx(origin_y)


def test_in_transit_ship_reaches_destination_on_arrival_tick(game_env):
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    ship = game_env.ship("1")
    # One tick before arrival: nearly, but not quite, at the destination.
    game_env.tick(game_env.module.TRAVEL_TICKS - 1)
    x, y = game_env.module.ship_map_position(ship)
    dest_x, dest_y = game_env.module.NODE_POSITIONS["verdant"]
    assert (x, y) != (dest_x, dest_y)


def test_ship_position_interpolates_partway_through_transit(game_env):
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    ship = game_env.ship("1")
    game_env.tick(game_env.module.TRAVEL_TICKS // 2)
    x, y = game_env.module.ship_map_position(ship)
    origin_x, origin_y = game_env.module.NODE_POSITIONS["aurum"]
    dest_x, dest_y = game_env.module.NODE_POSITIONS["verdant"]
    # Should be strictly between origin and destination on both axes
    # (or equal, if a node happens to share a coordinate).
    assert min(origin_x, dest_x) <= x <= max(origin_x, dest_x)
    assert min(origin_y, dest_y) <= y <= max(origin_y, dest_y)


def test_ship_position_returns_to_a_node_after_arrival(game_env):
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    ship = game_env.ship("1")
    assert game_env.module.ship_map_position(ship) == game_env.module.NODE_POSITIONS["verdant"]


def test_transit_total_ticks_fixed_at_departure_even_if_travel_ticks_changes_later(game_env):
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    ship = game_env.ship("1")
    assert ship.transit_total_ticks == game_env.module.TRAVEL_TICKS

    # Researching Fast Ships mid-flight shouldn't retroactively change
    # this ship's own trip duration.
    game_env.module.research_points = 100
    game_env.module.unlock_research("fast_ships")
    assert ship.transit_total_ticks == game_env.module.TRAVEL_TICKS


def test_render_map_draws_one_dot_per_ship(game_env):
    ctx = game_env.elements["map-canvas"].getContext("2d")
    ship_arc_count = sum(
        1 for name, args in ctx.calls if name == "arc" and args[2] == game_env.module.SHIP_DOT_RADIUS
    )
    assert ship_arc_count == len(game_env.module.ships)


def test_automated_and_manual_ships_use_distinct_colors(game_env):
    assert game_env.module.AUTOMATED_SHIP_COLOR != game_env.module.MANUAL_SHIP_COLOR


def test_render_map_does_not_error_with_a_mixed_automated_and_manual_fleet(game_env):
    game_env.module.total_profit = 1000
    game_env.module.automate_ship("1")  # ship 1 automated, 2-4 stay manual
    game_env.module.render()  # would raise if the mixed-color loop broke
    ctx = game_env.elements["map-canvas"].getContext("2d")
    ship_arc_count = sum(
        1 for name, args in ctx.calls if name == "arc" and args[2] == game_env.module.SHIP_DOT_RADIUS
    )
    assert ship_arc_count > 0


def test_map_redraws_on_tick_so_ship_dots_move(game_env):
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    ctx = game_env.elements["map-canvas"].getContext("2d")
    calls_before = len(ctx.calls)
    game_env.tick(1)
    calls_after = len(ctx.calls)
    assert calls_after > calls_before  # render_map() ran again this tick
