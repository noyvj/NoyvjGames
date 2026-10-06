"""K-27 sparklines and K-16 "why did that change": the per-season stat history
(statlog.py), the sparkline drawing (views.py), the waterfall explainer
(explain.py) and their wiring into the City Views dashboard.

The history rides in `campaign.ui["stat_history"]`, so the save-robustness
cases here are about that one key: absent by default, validated on every read,
junk dropped, old saves untouched."""

import copy
import json
import math

import explain
import save
import sim
import statlog
import views


def _play(game_env, seasons=3):
    game_env.advance_season(seasons)
    return game_env.module.statlog.rows(game_env.module.campaign.ui)


def _row(**overrides):
    values = {key: 0.0 for key in statlog.COLUMN_KEYS}
    values["season"] = 1.0
    values.update(overrides)
    return [values[key] for key in statlog.COLUMN_KEYS]


# --- the history itself ------------------------------------------------------
def test_columns_are_unique_and_cover_every_role_and_building():
    assert len(statlog.COLUMN_KEYS) == len(set(statlog.COLUMN_KEYS))
    for role in sim.ROLES:
        assert f"role_{role}" in statlog.COLUMN_KEYS
    for building in sim.BUILDINGS:
        assert f"bld_{building}" in statlog.COLUMN_KEYS


def test_a_fresh_settlement_has_no_history_key_at_all(game_env):
    assert statlog.KEY not in game_env.module.campaign.ui
    assert statlog.KEY not in game_env.module.get_state()["ui"]


def test_one_row_is_recorded_per_completed_season(game_env):
    rows = _play(game_env, 3)
    assert len(rows) == 3
    assert [statlog.value(r, "season") for r in rows] == [1, 2, 3]
    assert all(len(r) == len(statlog.COLUMN_KEYS) for r in rows)
    assert statlog.value(rows[-1], "population") == game_env.state.population


def test_history_is_capped_and_drops_the_oldest_first(game_env):
    ui = game_env.module.campaign.ui
    ui[statlog.KEY] = [_row(season=float(i + 1)) for i in range(statlog.MAX_ROWS)]
    game_env.advance_season(2)
    rows = statlog.rows(ui)
    assert len(rows) == statlog.MAX_ROWS
    assert statlog.value(rows[0], "season") == 3
    assert statlog.value(rows[-1], "season") == 2  # the real season just played, after the seeded 1..120


def test_a_look_back_records_nothing(game_env):
    m = game_env.module
    game_env.advance_season(2)
    m.campaign.ui["stat_history"] = statlog.rows(m.campaign.ui)
    before = copy.deepcopy(m.campaign.ui[statlog.KEY])
    m.campaign.revisiting = "tribal"  # a Look Back holds time; a stray advance must not write
    m.on_advance_season()
    m.campaign.revisiting = None
    assert m.campaign.ui[statlog.KEY] == before


def test_history_round_trips_through_get_state_and_load_state(game_env):
    m = game_env.module
    rows = _play(game_env, 4)
    data = json.loads(json.dumps(m.get_state()))
    assert data["ui"][statlog.KEY] == rows
    m.campaign.ui.pop(statlog.KEY)
    assert m.load_state(data) is True
    assert statlog.rows(m.campaign.ui) == rows


def test_an_old_save_without_the_key_loads_and_starts_recording(game_env):
    m = game_env.module
    game_env.advance_season(2)
    data = json.loads(json.dumps(m.get_state()))
    data["ui"].pop(statlog.KEY, None)
    assert m.load_state(data) is True
    assert statlog.rows(m.campaign.ui) == []
    game_env.advance_season(1)
    assert len(statlog.rows(m.campaign.ui)) == 1


def test_hostile_values_are_dropped_not_trusted():
    good = _row(season=5.0)
    nan_row = _row()
    nan_row[2] = float("nan")
    inf_row = _row()
    inf_row[3] = float("inf")
    bool_row = _row()
    bool_row[4] = True
    str_row = _row()
    str_row[5] = "9"
    short_row = good[:-1]
    long_row = good + [1.0]
    zero_season = _row(season=0.0)
    cleaned = statlog.clean(
        [good, nan_row, inf_row, bool_row, str_row, short_row, long_row, zero_season, None, "row", 5, {"a": 1}, [[]]]
    )
    assert cleaned == [good]


def test_a_non_list_history_reads_as_empty():
    for junk in (None, 5, "rows", {"a": [1]}, True, 3.5):
        assert statlog.clean(junk) == []
        assert statlog.rows({statlog.KEY: junk}) == []
    assert statlog.rows(None) == []


def test_values_are_clamped_and_a_huge_list_is_trimmed():
    row = _row()
    row[2] = 1e30
    row[3] = -1e30
    cleaned = statlog.clean([row] * (statlog.MAX_ROWS + 50))
    assert len(cleaned) == statlog.MAX_ROWS
    assert cleaned[0][2] == statlog.VALUE_LIMIT and cleaned[0][3] == -statlog.VALUE_LIMIT


def test_load_state_with_a_hostile_history_does_not_break_the_dashboard(game_env):
    m = game_env.module
    data = json.loads(json.dumps(m.get_state()))
    data["ui"][statlog.KEY] = [[float("nan")] * len(statlog.COLUMN_KEYS), "x", {"season": 2}, None, [True] * len(statlog.COLUMN_KEYS)]
    assert m.load_state(data) is True
    game_env.toggle_views()
    assert game_env.elements["views-dashboard"].children  # renders, with no sparklines


def test_a_new_settlement_starts_with_a_blank_history(game_env):
    import sys
    import types

    class Storage:
        data = {}

        def getItem(self, key):
            return self.data.get(key)

        def setItem(self, key, value):
            self.data[key] = value

    sys.modules["js"].window = types.SimpleNamespace(localStorage=Storage())
    m = game_env.module
    game_env.advance_season(3)
    assert statlog.rows(m.campaign.ui)
    m.found_new_settlement()
    assert statlog.rows(m.campaign.ui) == []


def test_recording_never_changes_the_simulation(game_env):
    other = save.Campaign()
    for _ in range(5):
        other.state.advance_season(other.tree.effects())
    game_env.advance_season(5)
    assert game_env.state.population == other.state.population
    assert game_env.state.resources["food"] == other.state.resources["food"]


def test_snapshot_survives_a_garbage_state():
    c = save.Campaign()
    c.state.resources["food"] = float("nan")
    c.state.land_health = float("inf")
    values = statlog.snapshot(c.state, c.tree.effects(), None)
    row = statlog._row_from(values)
    assert all(math.isfinite(v) for v in row)


# --- sparklines (K-27) -------------------------------------------------------
def test_every_dashboard_stat_that_has_a_key_maps_to_a_real_column():
    for label, key in views.SPARK_KEYS.items():
        assert key in statlog.COLUMN_KEYS, (label, key)


def test_every_numeric_dashboard_row_has_a_sparkline_key():
    c = save.Campaign()
    c.state.era = "relay"
    c.state.buildings["canals"] = 1
    c.state.advance_season(c.tree.effects())
    no_spark = {"Era", "Season", "Born / lost", "Last season"}
    for section in views.dashboard(c.state, c.tree.effects(), (1, 45)):
        for label, _value in section["rows"]:
            if label not in no_spark:
                assert views.spark_key(label), f"no sparkline for dashboard row {label!r}"


def test_sparkline_needs_two_values_and_ignores_junk():
    assert views.sparkline_svg([]) == ""
    assert views.sparkline_svg([3.0]) == ""
    assert views.sparkline_svg([None, "a", True, float("nan")]) == ""
    svg = views.sparkline_svg([1, None, 2, float("inf"), 3])
    assert svg.startswith("<svg") and svg.count(",") >= 3


def test_sparkline_states_its_numbers_as_text():
    svg = views.sparkline_svg([4, 9, 2, 7], "Food", lambda v: f"{v:.0f}")
    assert 'aria-label="Food: last 4 seasons, from 4 to 7 (lowest 2, highest 9)"' in svg
    assert "<title>" in svg and 'role="img"' in svg


def test_a_flat_series_draws_a_flat_line():
    svg = views.sparkline_svg([5, 5, 5])
    ys = {p.split(",")[1] for p in svg.split('points="')[1].split('"')[0].split()}
    assert len(ys) == 1


def test_sparkline_keeps_at_most_the_series_it_is_given():
    svg = views.sparkline_svg(list(range(100)))
    assert "last 100 seasons" in svg  # the caller trims to 20; the drawing never invents points
    assert statlog.series([_row(season=float(i + 1)) for i in range(50)], "season", 20)[0] == 31


# --- the dashboard wiring ----------------------------------------------------
def _dash_rows(game_env):
    rows = []
    for section in game_env.elements["views-dashboard"].children:
        rows.extend(c for c in section.children if "views-dash-row" in c.className)
    return rows


def _row_named(rows, label):
    for row in rows:
        if row.children and row.children[0].innerText == label:
            return row
    raise AssertionError(f"no dashboard row {label!r}")


def test_before_two_seasons_the_dashboard_has_no_deltas_or_hover(game_env):
    game_env.toggle_views()
    game_env.advance_season(1)
    rows = _dash_rows(game_env)
    assert rows
    assert not any("views-dash-row--why" in r.className for r in rows)
    assert not any(c.className == "views-dash-delta" for r in rows for c in r.children)
    assert game_env.elements["views-dashboard"].className == "views-dashboard views-dashboard--spark"


def test_the_dashboard_gains_sparklines_deltas_and_a_hover_waterfall(game_env):
    game_env.toggle_views()
    game_env.advance_season(4)
    rows = _dash_rows(game_env)
    food = _row_named(rows, "Food")
    classes = [c.className for c in food.children]
    assert "views-dash-spark" in classes and "views-dash-value" in classes and "views-dash-delta" in classes
    spark = next(c for c in food.children if c.className == "views-dash-spark")
    assert "<svg" in spark.innerHTML and "polyline" in spark.innerHTML
    assert "views-dash-row--why" in food.className
    assert food.attributes["tabindex"] == "0"
    pop = next(c for c in food.children if c.className == "why-pop")
    names = [line.children[0].innerText for line in pop.children[1:]]
    assert names[-1] == "Net change"
    assert "Gathered" in names and "Eaten" in names
    assert pop.attributes["role"] == "tooltip"
    assert "Why:" in food.attributes["aria-label"]


def test_the_delta_text_carries_an_arrow_and_a_sign(game_env):
    game_env.toggle_views()
    game_env.advance_season(4)
    for row in _dash_rows(game_env):
        for child in row.children:
            if child.className == "views-dash-delta":
                assert child.innerText[0] in "▲▼▬"


def test_a_stat_without_a_breakdown_gets_a_delta_but_no_hover(game_env):
    game_env.toggle_views()
    game_env.advance_season(4)
    equity = _row_named(_dash_rows(game_env), "Equity")
    assert any(c.className == "views-dash-delta" for c in equity.children)
    assert "views-dash-row--why" not in equity.className


def test_a_look_back_shows_the_plain_dashboard(game_env):
    m = game_env.module
    game_env.toggle_views()
    game_env.advance_season(3)
    m.campaign.revisiting = "tribal"
    m.update_views_panel()
    rows = _dash_rows(game_env)
    assert rows
    assert not any(c.className in ("views-dash-spark", "views-dash-delta") for r in rows for c in r.children)
    m.campaign.revisiting = None


def test_the_dashboard_is_unchanged_before_any_season(game_env):
    game_env.toggle_views()
    rows = _dash_rows(game_env)
    assert not any(c.className in ("views-dash-spark", "views-dash-delta") for r in rows for c in r.children)
    assert game_env.elements["views-dashboard"].className == "views-dashboard"


# --- the explainer (K-16) ------------------------------------------------------
def _history_and_report(game_env, seasons=4):
    game_env.advance_season(seasons)
    m = game_env.module
    return statlog.rows(m.campaign.ui), m.state.last_report, m.current_effects()


def test_the_top_factors_and_the_rest_add_up_to_the_net_change(game_env):
    history, report, effects = _history_and_report(game_env)
    for key in explain.EXPLAINABLE:
        out = explain.explain(key, history, report, effects)
        assert out is not None, key
        assert len(out["factors"]) <= explain.TOP_FACTORS
        assert math.isclose(sum(a for _, a in out["factors"]) + out["other"], out["net"], abs_tol=0.06), key


def test_food_is_explained_by_what_was_gathered_eaten_and_lost(game_env):
    history, report, effects = _history_and_report(game_env)
    out = explain.explain("food", history, report, effects)
    labels = [label for label, _ in out["factors"]]
    assert "Gathered" in labels and "Eaten" in labels
    gathered = dict(out["factors"])["Gathered"]
    assert math.isclose(gathered, report["food_gathered"], abs_tol=1e-6)


def test_the_score_is_explained_by_its_four_components_weighted(game_env):
    history, report, effects = _history_and_report(game_env)
    out = explain.explain("score", history, report, effects)
    names = {label for label, _ in out["factors"]} | ({"other"} if out["other"] else set())
    assert names <= {"Livability", "Equity", "Resource balance", "Resilience", "other"}
    assert math.isclose(out["net"], statlog.value(history[-1], "score") - statlog.value(history[-2], "score"), abs_tol=1e-6)


def test_a_stat_with_no_honest_breakdown_gets_none(game_env):
    history, report, effects = _history_and_report(game_env)
    assert explain.explain("equity", history, report, effects) is None
    assert explain.explain("not-a-column", history, report, effects) is None
    assert explain.explain("food", history[:1], report, effects) is None
    assert explain.explain("food", [], report, effects) is None
    assert explain.delta(history, "nope") is None


def test_a_mismatched_season_report_falls_back_to_one_honest_line(game_env):
    history, report, effects = _history_and_report(game_env)
    stale = dict(report, season=report["season"] - 10)
    out = explain.explain("food", history, stale, effects)
    assert [label for label, _ in out["factors"]] in ([], ["Other changes"])
    assert explain.explain("food", history, None, effects) is not None


def test_junk_report_values_never_raise(game_env):
    history, report, effects = _history_and_report(game_env)
    junk = {k: ("x" if i % 2 else float("nan")) for i, k in enumerate(report)}
    junk["season"] = report["season"]
    for key in explain.EXPLAINABLE:
        explain.explain(key, history, junk, effects)


def test_waterfall_geometry_stays_inside_the_track_and_ends_with_the_net(game_env):
    history, report, effects = _history_and_report(game_env)
    for key in explain.EXPLAINABLE:
        out = explain.explain(key, history, report, effects)
        steps = explain.waterfall_geometry(out)
        assert steps[-1]["kind"] == "net"
        for step in steps:
            assert 0 <= step["left"] <= 100 and 0 < step["width"] <= 100
            assert step["left"] + step["width"] <= 100.1
    assert explain.waterfall_geometry(None) == []
    assert explain.waterfall_lines(None) == []


def test_text_lines_state_the_sign_in_words(game_env):
    history, report, effects = _history_and_report(game_env)
    lines = explain.waterfall_lines(explain.explain("food", history, report, effects))
    assert lines[-1].startswith("Net change")
    assert any("+" in line or "−" in line for line in lines)


def test_population_change_is_births_minus_deaths():
    c = save.Campaign()
    c.state.population = 10
    row_a = statlog._row_from(statlog.snapshot(c.state, c.tree.effects(), {"season": 1}))
    c.state.population = 12
    report = {"season": 2, "births": 3, "deaths": 1}
    row_b = statlog._row_from(statlog.snapshot(c.state, c.tree.effects(), report))
    out = explain.explain("population", [row_a, row_b], report, c.tree.effects())
    assert dict(out["factors"]) == {"Born": 3.0, "Lost": -1.0}
    assert out["net"] == 2.0 and out["other"] == 0.0


def test_land_health_names_the_overharvest():
    c = save.Campaign()
    row_a = statlog._row_from(statlog.snapshot(c.state, c.tree.effects(), {"season": 1}))
    c.state.land_health -= 0.06
    report = {"season": 2, "extraction": 20.0, "sustainable_yield": 10.0}
    row_b = statlog._row_from(statlog.snapshot(c.state, c.tree.effects(), report))
    out = explain.explain("land", [row_a, row_b], report, c.tree.effects())
    assert out["factors"][0][1] < 0
    assert "beyond" in out["factors"][0][0]
