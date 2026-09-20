"""Round-2 backlog: J2, J4, J6, J12, J13, J14, J18, J20, J24, J25, J26, J30."""


def _sell(env, ship_id="1", dest="verdant"):
    ship = env.ship(ship_id)
    ship.load()
    ship.depart(dest)
    env.tick(ship.transit_total_ticks)


def test_reset_ship_name(game_env):
    game_env.rename_ship("1", "Falcon")
    assert game_env.ship("1").name == "Falcon"
    game_env.elements["ship-1-reset-name-button"].dispatch("click", None)
    assert game_env.ship("1").name == "Ship 1"
    assert game_env.elements["ship-1-name-input"].value == ""


def test_automate_tooltip_states_permanence(game_env):
    assert "permanent" in game_env.elements["ship-1-automate-button"].title


def test_crashed_market_tooltip_has_eta(game_env):
    m = game_env.module
    m.market_multiplier[m.ORE] = 0.5
    m.render()
    title = game_env.elements["market-ore-display"].title
    assert "50 tick" in title
    m.market_multiplier[m.ORE] = 1.0
    m.render()
    assert game_env.elements["market-ore-display"].title == ""


def test_research_locked_tooltip(game_env):
    m = game_env.module
    m.research_points = 0
    m.render()
    assert "more research points" in game_env.elements["research-outer_reaches-unlock-button"].title
    assert "unlock" in game_env.elements["research-outer_reaches-unlock-button"].title


def test_sparkline_now_marker(game_env):
    m = game_env.module
    svg = m._trend_sparkline_svg([0.5, 0.6, 0.7], "price-sparkline", "Now: 9 credits")
    assert "sparkline-now" in svg and "Now: 9 credits" in svg
    assert "sparkline-now" not in m._trend_sparkline_svg([0.5, 0.6], "x")


def test_need_sparkline_avg_pct(game_env):
    game_env.tick(3)
    assert "avg" in game_env.elements["colony-aurum-need-sparkline"].innerHTML


def test_map_canvas_title_reflects_fleet_priority(game_env):
    assert "Fleet Priority" in game_env.elements["map-canvas"].title
    game_env.module.fleet_priority_enabled = True
    game_env.module.render()
    assert "Pink ring" in game_env.elements["map-canvas"].title


def test_veteran_badge_after_round_trips(game_env):
    m = game_env.module
    ship = game_env.ship("1")
    ship.route_legs = 0
    for i in range(m.VETERAN_ROUND_TRIPS * 2):
        ship.location = "aurum" if i % 2 == 0 else "verdant"
        ship.cargo_good = m.ORE
        ship.cargo_qty = 1
        dest = "verdant" if i % 2 == 0 else "aurum"
        ship.depart(dest)
        ship.transit_ticks_remaining = 1
        ship.advance_transit()
    assert ship.is_veteran
    m.render()
    assert "Veteran" in game_env.elements["ship-1-label"].innerText
    assert not game_env.ship("2").is_veteran


def test_route_change_resets_veteran_progress(game_env):
    m = game_env.module
    ship = game_env.ship("1")
    ship.route_legs = 6
    ship.route_key = frozenset(("aurum", "verdant"))
    ship.location = "aurum"
    ship.cargo_good, ship.cargo_qty = m.ORE, 1
    ship.depart("ferrum")
    ship.transit_ticks_remaining = 1
    ship.advance_transit()
    assert ship.route_legs == 1


def test_route_trend_arrow(game_env):
    m = game_env.module
    m.good_profit_recent[m.ORE] = [10, 10]
    assert m.route_trend_arrow(m.ORE) == ""
    m.good_profit_recent[m.ORE] = [10, 10, 20, 20]
    assert m.route_trend_arrow(m.ORE) == "▲"
    m.good_profit_recent[m.ORE] = [20, 20, 10, 10]
    assert m.route_trend_arrow(m.ORE) == "▼"
    m.good_profit_recent[m.ORE] = [10, 10, 10, 10]
    assert m.route_trend_arrow(m.ORE) == "▶"


def test_fleet_efficiency_and_overview(game_env):
    m = game_env.module
    assert m.fleet_efficiency_lines() == []
    for sid in ("1", "3", "4"):
        game_env.ship(sid).total_earned = 1000
    game_env.ship("2").total_earned = 10
    lines = m.fleet_efficiency_lines()
    assert len(lines) == 1 and "Ship 2" in lines[0]
    assert m.colony_overview_lines()
    game_env.toggle_summary()
    kids = [c.innerText for c in game_env.elements["summary-panel"].children]
    assert "Fleet efficiency" in kids and "Galaxy overview" in kids


def test_new_fields_round_trip_and_old_save_defaults(game_env):
    m = game_env.module
    ship = game_env.ship("1")
    ship.route_key, ship.route_legs, ship.total_earned = frozenset(("aurum", "verdant")), 4, 77
    m.good_profit_recent[m.ORE] = [1, 2]
    state = m.get_state()
    ship.route_key, ship.route_legs, ship.total_earned = None, 0, 0
    m.good_profit_recent.clear()
    m.load_state(state)
    assert ship.route_key == frozenset(("aurum", "verdant"))
    assert (ship.route_legs, ship.total_earned) == (4, 77)
    assert m.good_profit_recent[m.ORE] == [1, 2]
    old = m.get_state()
    for sh in old["ships"].values():
        for k in ("route_key", "route_legs", "total_earned"):
            del sh[k]
    del old["good_profit_recent"]
    m.load_state(old)
    assert ship.route_legs == 0 and ship.route_key is None
