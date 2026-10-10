"""Round-7 pass: the sortable fleet overview (C-14)."""
from .test_career import _play


def _setup_fleet(game_env):
    s = game_env.state
    s.plant_counts.update({"coal": 4, "gas": 1, "solar": 6, "battery": 2})
    s.plant_age.update({"coal": 12.0, "gas": 2.0, "solar": 0.0, "battery": 1.0})
    s.maintenance_schedule["coal"] = 3
    s.funds = 100000


def _press(game_env, key):
    game_env.elements[f"fleet-sort-{key}"].dispatch("click", None)


def _order(game_env):
    body = game_env.elements["fleet-body"].innerHTML
    names = []
    for chunk in body.split('<th scope="row">')[1:]:
        names.append(chunk.split("</th>")[0].split(" ", 1)[1])
    return names


def test_fleet_rows_cover_every_plant_type(game_env):
    _setup_fleet(game_env)
    game_env.module.render()
    assert len(_order(game_env)) == 7
    rows = {r["type"]: r for r in game_env.module.fleet_rows()}
    assert rows["coal"]["count"] == 4 and rows["coal"]["wear"] == game_env.state.wear_percent("coal")
    assert rows["coal"]["risk"] > 0 and rows["solar"]["risk"] == 0
    assert rows["battery"]["generating"] is False and rows["battery"]["revenue"] == 0.0


def test_revenue_column_matches_the_mix_hover_figures(game_env):
    _setup_fleet(game_env)
    g = game_env.module
    rows = {r["type"]: r for r in g.fleet_rows()}
    shares = sum(rows[t]["revenue"] for t in g.GENERATION_TYPES)
    paid = min(game_env.state.total_capacity(), game_env.state.demand) * g.REVENUE_PER_UNIT_MET
    assert abs(shares - paid) < 1e-6


def test_next_maintenance_counts_rounds_to_the_schedule(game_env):
    _setup_fleet(game_env)
    g = game_env.module
    assert g.rounds_until_scheduled_maintenance("coal") == 2  # round 1: fires when round_number % 3 == 0, round 3
    game_env.state.round_number = 3
    assert g.rounds_until_scheduled_maintenance("coal") == 0
    game_env.state.round_number = 4
    assert g.rounds_until_scheduled_maintenance("coal") == 2
    game_env.state.round_number = 6
    assert g.rounds_until_scheduled_maintenance("coal") == 0
    assert g.rounds_until_scheduled_maintenance("gas") is None  # manual
    assert g.rounds_until_scheduled_maintenance("hydro") is None  # none standing


def test_next_maintenance_agrees_with_what_advance_round_does(game_env):
    _setup_fleet(game_env)
    g = game_env.module
    for _ in range(8):
        due = g.rounds_until_scheduled_maintenance("coal")
        played = game_env.state.round_number
        before = game_env.state.maintenance_actions_count
        _play(game_env, 1)
        assert (game_env.state.maintenance_actions_count > before) == (due == 0), played


def test_default_sort_is_units_high_to_low_and_headers_flip(game_env):
    _setup_fleet(game_env)
    game_env.module.render()
    assert _order(game_env)[:3] == ["Solar", "Coal", "Battery Storage"]
    assert "▼" in game_env.elements["fleet-sort-count"].innerText
    _press(game_env, "count")
    assert _order(game_env)[0] == "Nuclear"  # ascending: the empty types first, in plant order
    assert "▲" in game_env.elements["fleet-sort-count"].innerText


def test_sorting_each_column(game_env):
    _setup_fleet(game_env)
    g = game_env.module
    g.render()
    _press(game_env, "plant")
    assert _order(game_env)[0] == "Battery Storage" and _order(game_env)[-1] == "Wind"
    _press(game_env, "wear")
    assert _order(game_env)[0] == "Coal"
    _press(game_env, "risk")
    assert _order(game_env)[0] == "Coal"
    _press(game_env, "revenue")
    top = max((r for r in g.fleet_rows()), key=lambda r: r["revenue"])["plant"]
    assert _order(game_env)[0] == top
    _press(game_env, "next")
    assert _order(game_env)[-1] == "Coal"  # high to low: every manual-only type sorts ahead of a scheduled one
    assert g.fleet_sort_key == "next"


def test_manual_only_sorts_last_when_ascending(game_env):
    _setup_fleet(game_env)
    g = game_env.module
    rows = g.sort_fleet_rows(g.fleet_rows(), "next", False)
    assert rows[0]["type"] == "coal" and rows[0]["next"] == 2
    assert all(r["next"] is None for r in rows[1:])


def test_unknown_sort_key_is_refused(game_env):
    assert game_env.module.set_fleet_sort("nope") is False
    assert game_env.module.fleet_sort_key == "count"


def test_empty_fleet_reads_none_standing(game_env):
    game_env.module.render()
    body = game_env.elements["fleet-body"].innerHTML
    assert body.count("none standing") == 7


def test_sort_is_not_saved(game_env):
    _press(game_env, "wear")
    assert not any("fleet" in key for key in game_env.module.get_state())
