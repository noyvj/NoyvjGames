"""J-6 -- throughput per ship: units delivered per ship per 100 ticks, per ship,
per route and across the fleet, shown on the Ledger and in the Summary."""

import pytest


def _trip(game_env, ship_id="1", destination="ferrum"):
    game_env.load(ship_id=ship_id)
    game_env.depart(destination, ship_id=ship_id)
    game_env.tick(game_env.module.TRAVEL_TICKS)


def test_nothing_to_report_before_any_delivery(game_env):
    m = game_env.module
    assert m.ship_throughput(m.ships["5"]) is None  # not purchased
    assert m.route_throughput(m.ORE) is None
    assert m.throughput_lines() == []
    assert "no deliveries yet" in m.throughput_text()
    assert "no deliveries yet" in game_env.elements["throughput-display"].innerText


def test_ticks_owned_counts_only_purchased_ships(game_env):
    m = game_env.module
    game_env.tick(7)
    assert m.ships["1"].ticks_owned == 7 and m.ships["5"].ticks_owned == 0


def test_a_delivery_counts_units_by_ship_and_by_good(game_env):
    m = game_env.module
    _trip(game_env)
    ship = m.ships["1"]
    assert ship.units_moved == m.ships["1"].units_by_good[m.ORE] > 0
    assert ship.ticks_owned == m.TRAVEL_TICKS


def test_ship_throughput_is_units_per_hundred_ticks(game_env):
    m = game_env.module
    _trip(game_env)
    ship = m.ships["1"]
    assert m.ship_throughput(ship) == pytest.approx(ship.units_moved / ship.ticks_owned * 100)


def test_route_throughput_averages_over_the_ships_that_hauled_the_good(game_env):
    m = game_env.module
    a, b = m.ships["1"], m.ships["2"]
    a.units_by_good[m.ORE], a.ticks_owned = 30, 100
    b.units_by_good[m.ORE], b.ticks_owned = 10, 100
    assert m.route_throughput(m.ORE) == pytest.approx(20.0)
    assert m.route_throughput(m.GRAIN) is None


def test_a_disrupted_trip_moves_nothing(game_env):
    m = game_env.module
    m.route_hazards_enabled = True
    m.hazard_rng.random = lambda: 0.0
    _trip(game_env)
    assert m.ships["1"].units_moved == 0


def test_the_ledger_line_and_summary_show_it(game_env):
    _trip(game_env)
    assert "units per ship per 100 ticks across the fleet" in game_env.elements["throughput-display"].innerText
    game_env.toggle_summary()
    texts = [c.innerText for c in game_env.elements["summary-panel"].children]
    assert any("Throughput per ship" in t for t in texts)
    assert any(t.startswith("Ship 1:") and "units per 100 ticks" in t for t in texts)
    assert any("units/ship/100 ticks" in t and t.startswith("Ore") for t in texts)


def test_counters_round_trip_and_tampering_falls_back(game_env):
    m = game_env.module
    _trip(game_env)
    saved = m.get_state()
    units = m.ships["1"].units_moved
    m.ships["1"].units_moved = 0
    m.load_state(saved)
    assert m.ships["1"].units_moved == units
    entry = saved["ships"]["1"]
    for bad in (True, -4, "x", None, 10**15, 2.5):
        entry["units_moved"] = entry["ticks_owned"] = bad
        entry["units_by_good"] = {"bogus": 5, m.ORE: bad, m.GRAIN: 3, 7: 1}
        m.load_state(saved)
        ship = m.ships["1"]
        assert (ship.units_moved, ship.ticks_owned) == (0, 0), bad
        assert ship.units_by_good == {m.GRAIN: 3}
    entry["units_by_good"] = "nope"
    m.load_state(saved)
    assert m.ships["1"].units_by_good == {}
