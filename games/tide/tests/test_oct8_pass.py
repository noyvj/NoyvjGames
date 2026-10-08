"""2026-10-08 TODO pass: D-21 crosshair data, D-22 range selector, D-23 series markers, D-4 season
scrubber, D-2 session library, D-9 Harbor Almanac (and the D-25 line it feeds), D-6 season planner,
D-7 per-column tile labels. The browser-only parts (pointer handling in ui.js) are file checks."""

import copy
import html
import json
import re
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def storage(game_env, monkeypatch):
    """A dict standing in for this browser's localStorage."""
    store = {}
    monkeypatch.setattr(game_env.module, "_read_local_storage_item", lambda key: store.get(key))
    monkeypatch.setattr(game_env.module, "_write_local_storage_item", lambda key, value: store.__setitem__(key, value))
    return store


def play(env, seasons=3, invest_output=2):
    for _ in range(invest_output):
        env.invest("output")
    for _ in range(seasons):
        env.advance_season()


def crosshair(svg):
    match = re.search(r'data-crosshair="([^"]*)"', svg)
    assert match, "graph carries no crosshair data"
    return json.loads(html.unescape(match.group(1)))


def click(env, element_id):
    env.elements[element_id].dispatch("click", None)


def type_into(env, element_id, value):
    element = env.elements[element_id]
    element.value = str(value)

    class _Event:
        pass

    event = _Event()
    event.target = element
    for name in ("input", "change"):
        element.dispatch(name, event)


# ---- D-21 crosshair data -----------------------------------------------------------------------
def test_main_graph_carries_one_readout_per_season(game_env):
    play(game_env, seasons=5)
    lines = crosshair(game_env.module.acidity_fish_history_svg())
    assert len(lines) == 5
    assert lines[0].startswith("Season 1: acidity ") and "fishing yield" in lines[0] and "damage" in lines[0]
    assert "funds" in lines[0]


def test_delayed_graph_and_sparkline_carry_readouts_too(game_env):
    play(game_env, seasons=4)
    module = game_env.module
    lines = crosshair(module.delayed_consequence_svg())
    assert len(lines) == 4 + module.state._effective_fish_lag()
    assert "not yet played" in lines[-1]
    assert len(crosshair(module.then_vs_now_sparkline_svg())) == 4


def test_graph_svg_stays_focusable_and_mentions_the_arrow_keys(game_env):
    play(game_env, seasons=3)
    svg = game_env.module.acidity_fish_history_svg()
    assert 'tabindex="0"' in svg and "arrow keys" in svg


def test_ui_js_wires_pointer_and_keyboard_crosshair():
    js = (GAME_DIR / "ui.js").read_text(encoding="utf-8")
    for needle in ("data-crosshair", "pointermove", "pointerdown", "ArrowLeft", "graph-readout", "getScreenCTM"):
        assert needle in js
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert ".graph-crosshair" in css and ".graph-readout" in css


# ---- D-22 range selector -----------------------------------------------------------------------
def points_in(svg, colour):
    match = re.search(r'<polyline points="([^"]*)" fill="none" stroke="%s"' % colour, svg)
    return len(match.group(1).split()) if match else 0


def test_range_buttons_limit_the_graphs(game_env, storage):
    play(game_env, seasons=14)
    module = game_env.module
    assert points_in(module.acidity_fish_history_svg(), module.SPARKLINE_ACIDITY_COLOR) == 14
    click(game_env, "graph-range-10")
    assert module.graph_range == "10"
    assert points_in(module.acidity_fish_history_svg(), module.SPARKLINE_ACIDITY_COLOR) == 10
    assert len(crosshair(module.acidity_fish_history_svg())) == 10
    assert crosshair(module.acidity_fish_history_svg())[0].startswith("Season 5:")
    # The delayed-consequence timeline follows the same range (10 seasons + the lag).
    assert len(crosshair(module.delayed_consequence_svg())) == 10 + module.state._effective_fish_lag()
    click(game_env, "graph-range-20")
    assert points_in(module.acidity_fish_history_svg(), module.SPARKLINE_ACIDITY_COLOR) == 14
    click(game_env, "graph-range-all")
    assert game_env.elements["graph-range-all"].getAttribute("aria-pressed") == "true"
    assert game_env.elements["graph-range-10"].getAttribute("aria-pressed") == "false"


def test_range_and_markers_are_remembered_in_this_browser(game_env, storage):
    click(game_env, "graph-range-20")
    click(game_env, "graph-markers-toggle")
    saved = json.loads(storage[game_env.module.GRAPH_PREFS_KEY])
    assert saved == {"range": "20", "markers": True}
    game_env.module.graph_range, game_env.module.graph_markers = "all", False
    game_env.module._load_graph_prefs()
    assert (game_env.module.graph_range, game_env.module.graph_markers) == ("20", True)


def test_damaged_graph_prefs_are_ignored(game_env, storage):
    storage[game_env.module.GRAPH_PREFS_KEY] = json.dumps({"range": "999", "markers": "yes"})
    game_env.module._load_graph_prefs()
    assert (game_env.module.graph_range, game_env.module.graph_markers) == ("all", False)
    storage[game_env.module.GRAPH_PREFS_KEY] = "not json"
    game_env.module._load_graph_prefs()
    assert game_env.module.graph_range == "all"


def test_baseline_marker_only_shows_when_in_range(game_env):
    play(game_env, seasons=3)
    game_env.set_baseline()
    play(game_env, seasons=14, invest_output=0)
    module = game_env.module
    assert "Baseline set here" in module.acidity_fish_history_svg()
    module.graph_range = "10"
    assert "Baseline set here" not in module.acidity_fish_history_svg()


# ---- D-23 series markers -----------------------------------------------------------------------
def test_markers_add_shapes_and_dashes_only_when_on(game_env):
    play(game_env, seasons=4)
    module = game_env.module
    plain = module.acidity_fish_history_svg()
    assert "<circle" not in plain and "<rect" not in plain
    click(game_env, "graph-markers-toggle")
    marked = module.acidity_fish_history_svg()
    assert "<circle" in marked and "<rect" in marked
    assert 'stroke-dasharray="6 3"' in marked
    assert "<polygon" in module.then_vs_now_sparkline_svg()
    assert game_env.elements["graph-markers-toggle"].innerText == "Series markers: On"


def test_markers_are_thinned_on_long_sessions(game_env):
    play(game_env, seasons=60, invest_output=2)
    module = game_env.module
    module.graph_markers = True
    svg = module.acidity_fish_history_svg()
    assert svg.count("<circle") <= module.GRAPH_MARKER_LIMIT + 1


# ---- D-4 season scrubber -----------------------------------------------------------------------
def test_one_compact_snapshot_per_season_and_it_round_trips(game_env):
    play(game_env, seasons=4)
    state = game_env.state
    assert [x[0] for x in state.season_snapshots] == [1, 2, 3, 4]
    assert all(len(json.dumps(x)) < 60 for x in state.season_snapshots)
    saved = game_env.module.get_state()
    state.season_snapshots = []
    game_env.module.load_state(saved)
    assert game_env.state.season_snapshots == saved["season_snapshots"]


def test_snapshots_are_capped_and_damaged_ones_dropped(game_env):
    play(game_env, seasons=3)
    module = game_env.module
    saved = module.get_state()
    saved["season_snapshots"] = [
        [1, 5.0, "up", []], [2, "x", "up", []], [3, 5.0, "zz", []], [4, 5.0, "up", [99]], "junk", [5, 5.0, "up"],
        [6, float("nan"), "up", []], [7, 5.0, "upl", []],
    ]
    module.load_state(saved)
    assert game_env.state.season_snapshots == [[1, 5.0, "up", []]]
    saved["season_snapshots"] = "nope"
    module.load_state(saved)
    assert game_env.state.season_snapshots == []


def test_scrub_snapshot_matches_what_the_player_saw(game_env):
    play(game_env, seasons=5)
    state = game_env.state
    first = state.scrub_snapshot(1)
    assert first["funds"] == 300 and first["sea_level"] == 0 and first["rows_dry"] == 6
    third = state.scrub_snapshot(3)
    ledger = {e["season"]: e for e in state.season_ledger}
    assert third["funds"] == ledger[2]["funds"] and third["tier"] == ledger[2]["tier"]
    assert third["sea_level"] == pytest.approx(2 * state.sea_rise_per_season())
    assert state.scrub_snapshot(state.season) is None and state.scrub_snapshot(0) is None
    assert state.scrub_snapshot("3") is None
    assert state.scrub_positions() == [1, 2, 3, 4, 5]


def test_scrub_positions_skip_seasons_an_old_save_has_no_record_of(game_env):
    play(game_env, seasons=5)
    game_env.state.season_snapshots = [x for x in game_env.state.season_snapshots if x[0] >= 3]
    assert game_env.state.scrub_positions() == [1, 4, 5]


def test_slider_is_hidden_until_there_is_something_to_look_back_at(game_env):
    assert game_env.elements["scrub-section"].hidden is True
    play(game_env, seasons=3)
    section = game_env.elements["scrub-section"]
    slider = game_env.elements["scrub-slider"]
    assert section.hidden is False
    assert slider.getAttribute("min") == "1" and slider.getAttribute("max") == "4"
    assert slider.value == "4"
    assert "live" in game_env.elements["scrub-readout"].innerText


def test_scrubbing_draws_the_earlier_coastline_without_touching_the_run(game_env):
    play(game_env, seasons=14, invest_output=2)
    module = game_env.module
    before = copy.deepcopy(module.get_state())
    flooded_now = sum(1 for t in game_env.elements["coastline-grid"].children if "coastline-flooded" in t.className)
    type_into(game_env, "scrub-slider", 2)
    grid = game_env.elements["coastline-grid"]
    flooded_then = sum(1 for t in grid.children if "coastline-flooded" in t.className)
    assert flooded_then < flooded_now
    assert "coastline-grid--scrubbed" in grid.className
    assert "Start of Season 2" in game_env.elements["scrub-readout"].innerText
    assert game_env.elements["scrub-live-button"].hidden is False
    assert "read-only" in game_env.elements["coastline-description"].innerText
    assert module.get_state() == before
    assert not any("coastline-flash" in t.className for t in grid.children)


def test_scrub_view_shows_the_tier_and_heritage_of_that_season(game_env):
    module = game_env.module
    for _ in range(3):
        game_env.invest("adaptation")
    game_env.state.funds = 1000
    module.state.protect_heritage("lighthouse")
    game_env.advance_season()
    play(game_env, seasons=3, invest_output=0)
    type_into(game_env, "scrub-slider", 2)
    snap = game_env.state.scrub_snapshot(2)
    assert snap["tier"] == 1 and snap["heritage"]["lighthouse"] == "protected"
    text = game_env.elements["scrub-readout"].innerText
    assert "Sandbag berms" in text and "lighthouse protected" in text


def test_back_to_live_and_any_player_action_end_the_look_back(game_env):
    play(game_env, seasons=4)
    type_into(game_env, "scrub-slider", 2)
    click(game_env, "scrub-live-button")
    assert game_env.module.scrub_season is None
    assert "coastline-grid--scrubbed" not in game_env.elements["coastline-grid"].className
    type_into(game_env, "scrub-slider", 2)
    assert game_env.module.scrub_season == 2
    game_env.invest("output")
    assert game_env.module.scrub_season is None
    type_into(game_env, "scrub-slider", 1)
    game_env.advance_season()
    assert game_env.module.scrub_season is None


def test_scrubbing_to_the_live_season_or_garbage_changes_nothing(game_env):
    play(game_env, seasons=3)
    type_into(game_env, "scrub-slider", 4)
    assert game_env.module.scrub_season is None
    type_into(game_env, "scrub-slider", "abc")
    assert game_env.module.scrub_season is None


def test_replay_from_checkpoint_truncates_snapshots(game_env):
    play(game_env, seasons=3)
    game_env.state.set_checkpoint()
    play(game_env, seasons=3, invest_output=0)
    assert game_env.module.replay_from_checkpoint()
    assert [x[0] for x in game_env.state.season_snapshots] == [1, 2, 3]
    assert "season_snapshots" not in game_env.state.checkpoint


# ---- D-7 per-column tile labels ----------------------------------------------------------------
def test_every_tile_names_its_row_and_column(game_env):
    grid = game_env.elements["coastline-grid"]
    labels = [t.getAttribute("aria-label") for t in grid.children]
    assert labels[0].startswith("Row 1: ") and labels[1].startswith("Row 1, column 2: ")
    heritage_column = [lab for lab in labels if lab.startswith("Row 5, column 4:")]
    assert heritage_column and "lighthouse" in heritage_column[0]
    other_column = [lab for lab in labels if lab.startswith("Row 5, column 3:")]
    assert "lighthouse" not in other_column[0]


def test_ui_js_walks_columns_with_left_and_right():
    js = (GAME_DIR / "ui.js").read_text(encoding="utf-8")
    assert "ArrowLeft: [0, -1]" in js and "ArrowRight: [0, 1]" in js and "Home" in js


# ---- D-2 session library -----------------------------------------------------------------------
def test_library_needs_a_few_seasons(game_env, storage):
    play(game_env, seasons=2)
    assert game_env.module.library_save_current() is False
    assert game_env.module.LIBRARY_KEY not in storage
    assert "at least" in game_env.module._library_status


def test_library_saves_settings_outcome_and_series(game_env, storage):
    module = game_env.module
    game_env.state.set_settlement_name("Saltmarsh")
    game_env.state.set_storm_mode(True)
    game_env.toggle_hard_lag()
    play(game_env, seasons=5)
    assert module.library_save_current()
    [record] = module.library_records()
    assert record["name"] == "Saltmarsh" and record["seasons"] == 5
    assert record["lag"] == "hard" and record["storms"] is True and record["scenario"] == "moderate"
    assert len(record["acidity"]) == 5 and len(record["fish"]) == 5
    assert record["score"] == round(game_env.state.damage_saved(), 1)
    assert "harder lag" in module.library_summary_text(record) and "storm seasons on" in module.library_summary_text(record)


def test_library_is_capped_and_ids_keep_counting(game_env, storage):
    module = game_env.module
    play(game_env, seasons=3)
    for _ in range(module.LIBRARY_LIMIT + 3):
        assert module.library_save_current()
    records = module.library_records()
    assert len(records) == module.LIBRARY_LIMIT
    assert records[-1]["id"] == module.LIBRARY_LIMIT + 3
    assert "dropped" in module._library_status


def test_library_ignores_damaged_entries(game_env, storage):
    module = game_env.module
    play(game_env, seasons=3)
    module.library_save_current()
    good = json.loads(storage[module.LIBRARY_KEY])
    bad_series = dict(good[0], id=2, acidity=[5])
    bad_scenario = dict(good[0], id=3, scenario="apocalypse")
    storage[module.LIBRARY_KEY] = json.dumps(good + [bad_series, bad_scenario, "junk", {"id": 9}])
    assert [r["id"] for r in module.library_records()] == [1]
    storage[module.LIBRARY_KEY] = "{not json"
    assert module.library_records() == []


def test_library_panel_lists_sessions_and_deletes(game_env, storage):
    module = game_env.module
    play(game_env, seasons=4)
    click(game_env, "library-toggle-button")
    assert game_env.elements["library-panel"].hidden is False
    click(game_env, "library-save-button")
    listing = game_env.elements["library-list"]
    assert len(listing.children) == 1
    assert "Session 1" in listing.children[0].children[0].innerText
    assert "Session 1" in game_env.elements["library-select-b"].innerHTML
    assert "Current session" in game_env.elements["library-select-a"].innerHTML
    listing.children[0].children[1].dispatch("click", None)
    assert module.library_records() == []
    assert "Nothing saved" in game_env.elements["library-list"].innerText


def test_two_sessions_overlay_as_solid_and_dashed(game_env, storage):
    module = game_env.module
    play(game_env, seasons=4)
    module.library_save_current()
    play(game_env, seasons=3, invest_output=0)
    click(game_env, "library-toggle-button")
    graph = game_env.elements["library-compare-graph"].innerHTML
    assert graph.startswith("<svg") and 'stroke-dasharray="4 3"' in graph
    lines = crosshair(graph)
    assert len(lines) == 7 and "A " in lines[6] and "B " not in lines[6]
    assert "B Session 1" in lines[0] and "A Your settlement" in lines[0]
    assert "Session A" in graph and "(solid)" in graph and "(dashed)" in graph
    assert "Session 1" in game_env.elements["library-compare-caption"].innerText


def test_a_saved_session_can_be_drawn_dashed_on_the_main_graph(game_env, storage):
    module = game_env.module
    play(game_env, seasons=4)
    module.library_save_current()
    click(game_env, "library-toggle-button")
    assert 'stroke-dasharray="3 3"' not in module.acidity_fish_history_svg()
    type_into(game_env, "library-overlay-select", "1")
    svg = module.acidity_fish_history_svg()
    assert 'stroke-dasharray="3 3"' in svg and "Dashed lines: the saved session Session 1" in svg
    assert "Session 1: acidity" in crosshair(svg)[0]
    assert 'stroke-dasharray="3 3"' in game_env.elements["acidity-fish-graph"].innerHTML
    # Deleting the overlaid session removes the overlay.
    module.library_delete(1)
    module.render()
    assert module.library_overlay_id == ""
    assert 'stroke-dasharray="3 3"' not in module.acidity_fish_history_svg()


def test_library_is_not_part_of_a_save(game_env, storage):
    play(game_env, seasons=3)
    game_env.module.library_save_current()
    saved = game_env.module.get_state()
    assert "library" not in json.dumps(saved).lower()


# ---- D-9 Harbor Almanac (and D-25) -------------------------------------------------------------
def test_almanac_counts_seasons_rows_and_storms(game_env, storage):
    module = game_env.module
    game_env.state.set_storm_mode(True)
    play(game_env, seasons=10, invest_output=2)
    assert module.almanac["seasons"] == 10
    expected_rows = sum(e["rows_dry"] for e in game_env.state.season_ledger)
    assert module.almanac["rows_kept"] == expected_rows
    assert module.almanac["storms"] == 2
    assert json.loads(storage[module.ALMANAC_KEY])["seasons"] == 10


def test_almanac_counts_each_protected_heritage_site_once(game_env, storage):
    module = game_env.module
    game_env.state.funds = 1000
    game_env.state.protect_heritage("lighthouse")
    module.render()
    module.render()
    assert module.almanac["heritage"] == 1
    game_env.state.protect_heritage("reef")
    module.render()
    assert module.almanac["heritage"] == 2


def test_loading_a_save_never_counts_old_seasons_again(game_env, storage):
    module = game_env.module
    play(game_env, seasons=4)
    saved = module.get_state()
    counted = module.almanac["seasons"]
    module.load_state(saved)
    module.load_state(saved)
    assert module.almanac["seasons"] == counted
    game_env.advance_season()
    assert module.almanac["seasons"] == counted + 1


def test_rewinding_to_a_checkpoint_counts_only_seasons_actually_replayed(game_env, storage):
    module = game_env.module
    play(game_env, seasons=3)
    game_env.state.set_checkpoint()
    play(game_env, seasons=3, invest_output=0)
    assert module.almanac["seasons"] == 6
    module.replay_from_checkpoint()
    game_env.advance_season()
    assert module.almanac["seasons"] == 7


def test_almanac_keeps_the_best_run_per_scenario_and_lag(game_env, storage):
    module = game_env.module
    for _ in range(4):
        game_env.invest("adaptation")
    play(game_env, seasons=6, invest_output=0)
    key = "moderate|standard"
    first = module.almanac["best"][key]
    assert first["seasons"] == 6 and first["score"] == round(game_env.state.damage_saved(), 1)
    assert first["tier"] == game_env.state.current_tier_index() == 1
    # A worse run on the same key does not replace it; another lag mode gets its own entry.
    module.almanac["best"][key]["score"] = 9999.0
    game_env.advance_season()
    assert module.almanac["best"][key]["score"] == 9999.0
    game_env.toggle_hard_lag()
    game_env.advance_season()
    assert "moderate|hard" in module.almanac["best"]


def test_almanac_reloads_from_storage_and_ignores_damage(game_env, storage):
    module = game_env.module
    play(game_env, seasons=3)
    raw = storage[module.ALMANAC_KEY]
    reloaded = module._load_almanac()
    assert reloaded["seasons"] == 3 and reloaded["best"].keys() == json.loads(raw)["best"].keys()
    storage[module.ALMANAC_KEY] = json.dumps(
        {"seasons": -4, "storms": "many", "rows_kept": 7, "best": {"nonsense": {}, "severe|hard": {"score": "x"}}}
    )
    damaged = module._load_almanac()
    assert damaged["seasons"] == 0 and damaged["storms"] == 0 and damaged["rows_kept"] == 7 and damaged["best"] == {}
    storage[module.ALMANAC_KEY] = "[]"
    assert module._load_almanac()["seasons"] == 0


def test_almanac_panel_shows_totals_and_every_scenario_lag_row(game_env, storage):
    play(game_env, seasons=3)
    click(game_env, "almanac-toggle-button")
    assert game_env.elements["almanac-panel"].hidden is False
    assert "<strong>3</strong> seasons played" in game_env.elements["almanac-lifetime"].innerHTML
    body = game_env.elements["almanac-best-body"].innerHTML
    assert body.count("<tr>") == 6 and "(this session)" in body and "No run yet" in body
    click(game_env, "almanac-toggle-button")
    assert game_env.elements["almanac-panel"].hidden is True


def test_session_summary_gains_a_personal_best_line(game_env, storage):
    module = game_env.module
    assert module.almanac_best_line() == ""
    play(game_env, seasons=4)
    game_env.toggle_session_summary()
    text = game_env.elements["session-summary-text"].innerText
    assert "Best for the moderate sea with standard lag" in text and "This session:" in text


def test_almanac_is_not_part_of_a_save(game_env, storage):
    play(game_env, seasons=3)
    assert "almanac" not in json.dumps(game_env.module.get_state()).lower()


# ---- D-6 season planner -------------------------------------------------------------------------
def test_planner_projection_matches_what_real_play_would_do(game_env):
    module = game_env.module
    game_env.invest("output")
    plan = [
        {"output": 1, "reduction": 0, "adaptation": 1},
        {"output": 0, "reduction": 1, "adaptation": 0},
        {"output": 0, "reduction": 0, "adaptation": 2},
    ] + [{"output": 0, "reduction": 0, "adaptation": 0}] * 2
    points = module.project_plan(plan, 3)
    assert [p["step"] for p in points] == [0, 1, 2, 3]
    twin = copy.deepcopy(game_env.state)
    for index in range(3):
        for category in module.CATEGORIES:
            for _ in range(plan[index][category]):
                twin.invest(category)
        twin.advance_season()
    last = points[-1]
    assert last["funds"] == pytest.approx(twin.funds) and last["acidity"] == pytest.approx(twin.acidity)
    assert last["fish_yield"] == pytest.approx(twin.fish_yield_multiplier()) and last["rows_dry"] == twin.rows_dry_count()
    assert last["season"] == twin.season == game_env.state.season + 3


def test_planner_never_touches_the_real_game(game_env):
    module = game_env.module
    play(game_env, seasons=3)
    before = copy.deepcopy(module.get_state())
    real = module.state
    plan = [{"output": 3, "reduction": 2, "adaptation": 4}] * 5
    module.project_plan(plan, 5)
    assert module.state is real and module.get_state() == before


def test_planner_state_is_restored_even_if_the_projection_fails(game_env, monkeypatch):
    module = game_env.module
    real = module.state

    def boom(self):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(module.SettlementState, "advance_season", boom)
    with pytest.raises(RuntimeError):
        module.project_plan([{"output": 1, "reduction": 0, "adaptation": 0}] * 5, 3)
    assert module.state is real


def test_planner_skips_what_you_cannot_afford_and_says_so(game_env):
    module = game_env.module
    plan = [{"output": 9, "reduction": 9, "adaptation": 9}] + [{"output": 0, "reduction": 0, "adaptation": 0}] * 4
    points = module.project_plan(plan, 3)
    assert points[1]["skipped"] > 0
    assert "not affordable" in module.planner_summary_text(points)
    assert "nothing has been spent" in module.planner_summary_text(points)


def test_planner_panel_reads_inputs_and_draws_the_projection(game_env):
    module = game_env.module
    click(game_env, "planner-toggle-button")
    assert game_env.elements["planner-panel"].hidden is False
    assert game_env.elements["planner-row-3"].hidden is False and game_env.elements["planner-row-4"].hidden is True
    type_into(game_env, "planner-s1-output", 2)
    type_into(game_env, "planner-s2-adaptation", 3)
    assert module.planner_plan[0]["output"] == 2 and module.planner_plan[1]["adaptation"] == 3
    assert game_env.elements["planner-body"].innerHTML.count("<tr>") == 3
    assert game_env.elements["planner-chart"].innerHTML.startswith("<svg")
    assert len(crosshair(game_env.elements["planner-chart"].innerHTML)) == 4
    assert "projection only" in game_env.elements["planner-summary"].innerText
    type_into(game_env, "planner-length", 5)
    assert game_env.elements["planner-row-5"].hidden is False
    assert game_env.elements["planner-body"].innerHTML.count("<tr>") == 5
    # Nothing was spent or advanced by any of that.
    assert game_env.state.season == 1 and game_env.state.funds == 300


def test_planner_inputs_are_clamped(game_env):
    module = game_env.module
    type_into(game_env, "planner-s1-output", 99)
    type_into(game_env, "planner-s1-reduction", -5)
    type_into(game_env, "planner-s1-adaptation", "x")
    assert module.planner_plan[0] == {"output": 9, "reduction": 0, "adaptation": 0}
    type_into(game_env, "planner-length", 99)
    assert module.planner_length == 5
    type_into(game_env, "planner-length", 1)
    assert module.planner_length == 3


def test_commit_applies_only_the_first_season_and_slides_the_plan(game_env):
    module = game_env.module
    click(game_env, "planner-toggle-button")
    type_into(game_env, "planner-s1-output", 2)
    type_into(game_env, "planner-s2-output", 1)
    click(game_env, "planner-commit-button")
    assert game_env.state.season == 2 and game_env.state.capacity["output"] == 2
    assert module.planner_plan[0]["output"] == 1
    assert module.planner_plan[-1] == {"output": 0, "reduction": 0, "adaptation": 0}
    assert len(module.planner_plan) == module.PLANNER_MAX_SEASONS
    assert "Committed" in game_env.elements["season-announcer"].innerText
    click(game_env, "planner-clear-button")
    assert all(not any(entry.values()) for entry in module.planner_plan)


def test_planner_follows_the_season_on_the_commit_button(game_env):
    click(game_env, "planner-toggle-button")
    assert "season 1" in game_env.elements["planner-commit-button"].innerText
    game_env.advance_season()
    assert "season 2" in game_env.elements["planner-commit-button"].innerText


# ---- files and panels --------------------------------------------------------------------------
def test_new_panels_are_in_both_pages_and_the_desktop_menu():
    config = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    windows = {panel: toggle for panel, toggle, _title in config["windows"]}
    for panel, toggle in (
        ("planner-panel", "planner-toggle-button"),
        ("library-panel", "library-toggle-button"),
        ("almanac-panel", "almanac-toggle-button"),
    ):
        assert windows[panel] == toggle
        for page in ("index.html", "pc.html"):
            assert f'id="{panel}"' in (GAME_DIR / page).read_text(encoding="utf-8")
    menu_ids = [i for group in config["toolbar"]["menu"] for i in group["ids"]]
    for toggle in ("planner-toggle-button", "library-toggle-button", "almanac-toggle-button"):
        assert toggle in menu_ids


# ---- a browser that already holds saved data when the page loads --------------------------------
def test_game_boots_with_existing_local_storage_data():
    """The almanac, graph options and library are read while game.py is being imported, so
    every helper they use must already exist by then (a NameError here blanks the whole game)."""
    import importlib.util
    import sys
    import types

    from .conftest import ELEMENT_IDS, GAME_PY, INITIALLY_DISABLED_IDS, _install_pyodide_fakes, _remove_pyodide_fakes
    from .fakes import FakeElement, FakeTimers

    elements = {}
    for id_ in ELEMENT_IDS:
        FakeElement(id_, registry=elements)
    for id_ in INITIALLY_DISABLED_IDS:
        elements[id_].disabled = True
    _install_pyodide_fakes(elements, FakeTimers())
    store = {
        "tide_almanac_v1": json.dumps({
            "seasons": 12, "rows_kept": 40, "heritage": 1, "storms": 2,
            "best": {"severe|hard": {"score": 55.5, "seasons": 14, "tier": 2, "rows_dry": 1}},
        }),
        "tide_graph_prefs_v1": json.dumps({"range": "10", "markers": True}),
    }
    sys.modules["js"].localStorage = types.SimpleNamespace(
        getItem=lambda key: store.get(key), setItem=lambda key, value: store.__setitem__(key, value)
    )
    try:
        spec = importlib.util.spec_from_file_location("game", GAME_PY)
        module = importlib.util.module_from_spec(spec)
        sys.modules["game"] = module
        spec.loader.exec_module(module)
        assert module.almanac["seasons"] == 12 and module.almanac["best"]["severe|hard"]["score"] == 55.5
        assert (module.graph_range, module.graph_markers) == ("10", True)
    finally:
        _remove_pyodide_fakes()
