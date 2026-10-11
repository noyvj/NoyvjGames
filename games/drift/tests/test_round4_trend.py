"""Round-4 trend graph (2026-10-11): event markers and toggleable layers (I-12), range chips and the
crosshair data (I-16)."""

import json
import re

import pytest


def _play(game_env, rounds, build_every=3):
    for i in range(rounds):
        if i % build_every == 0:
            game_env.invest("housing")
            game_env.invest("services")
        game_env.advance_round()


def _svg(game_env, **kwargs):
    region = game_env.region
    return game_env.module.trend_graph_svg(
        region.strain_log, region.wellbeing_log, None,
        first_round=region.round_number - len(region.strain_log), **kwargs,
    )


def _tips(svg):
    return re.findall(r'data-tip="([^"]*)"', svg)


# --- the graph itself ---------------------------------------------------------

def test_default_graph_is_unchanged_in_its_lines_and_markers(game_env):
    m = game_env.module
    svg = m.trend_graph_svg([0.1, 0.2, 0.3, 0.4], [70.0, 65.0, 60.0, 55.0])
    assert svg.count("<polyline") == 2 and svg.count("<circle") == 8
    assert "trend-event" not in svg


def test_every_round_gets_a_hit_column_with_its_exact_values(game_env):
    svg = game_env.module.trend_graph_svg([0.5, 0.25, 0.1], [42.0, 50.0, 61.0])
    assert _tips(svg) == [
        "Round 1; strain 50%, wellbeing 42",
        "Round 2; strain 25%, wellbeing 50",
        "Round 3; strain 10%, wellbeing 61",
    ]


def test_first_round_labels_a_capped_log_correctly(game_env):
    svg = game_env.module.trend_graph_svg([0.1, 0.2], [50.0, 60.0], first_round=201)
    assert _tips(svg)[0].startswith("Round 201;") and "Round 202 -- Strain: 20" in svg


# --- I-16: range chips --------------------------------------------------------

def test_view_rounds_shows_only_the_last_n_rounds(game_env):
    _play(game_env, 30)
    full = _svg(game_env)
    last10 = _svg(game_env, view_rounds=10)
    assert len(_tips(full)) == 30 and len(_tips(last10)) == 10
    assert _tips(last10)[0].startswith("Round 21;") and _tips(last10)[-1].startswith("Round 30;")
    assert last10.count("<circle") == 20


def test_a_range_longer_than_the_run_shows_everything(game_env):
    _play(game_env, 6)
    assert len(_tips(_svg(game_env, view_rounds=25))) == 6


def test_range_buttons_switch_the_graph_and_mark_the_pressed_chip(game_env):
    _play(game_env, 30)
    game_env.elements["trend-range-10-button"].dispatch("click", None)
    graph = game_env.elements["trend-graph"].innerHTML
    assert len(_tips(graph)) == 10
    assert game_env.elements["trend-range-10-button"].getAttribute("aria-pressed") == "true"
    assert game_env.elements["trend-range-all-button"].getAttribute("aria-pressed") == "false"
    game_env.elements["trend-range-25-button"].dispatch("click", None)
    assert len(_tips(game_env.elements["trend-graph"].innerHTML)) == 25
    game_env.elements["trend-range-all-button"].dispatch("click", None)
    assert len(_tips(game_env.elements["trend-graph"].innerHTML)) == 30


def test_the_range_survives_further_play_but_not_a_reload(game_env):
    _play(game_env, 12)
    game_env.elements["trend-range-10-button"].dispatch("click", None)
    game_env.advance_round()
    assert len(_tips(game_env.elements["trend-graph"].innerHTML)) == 10
    assert "trend_range" not in game_env.module.get_state()


def test_the_control_line_stays_aligned_when_the_range_cuts_the_start(game_env):
    m = game_env.module
    svg = m.trend_graph_svg([0.1] * 5, [50.0] * 5, [10.0, 20.0, 30.0, 40.0, 50.0], view_rounds=3)
    assert svg.count("<polyline") == 3
    control = re.search(r'points="([^"]*)" class="trend-line trend-line--control"', svg).group(1).split()
    assert len(control) == 3  # the last three control values, not the first three


# --- I-12: layers ---------------------------------------------------------------

def test_turning_a_layer_off_removes_its_line_and_markers(game_env):
    m = game_env.module
    base = m.trend_graph_svg([0.1, 0.2, 0.3], [50.0, 60.0, 70.0], [30.0, 30.0, 30.0])
    no_strain = m.trend_graph_svg([0.1, 0.2, 0.3], [50.0, 60.0, 70.0], [30.0, 30.0, 30.0], layers={"strain": False})
    assert "trend-line--strain" in base and "trend-line--strain" not in no_strain
    assert no_strain.count("<circle") == 3
    no_control = m.trend_graph_svg([0.1, 0.2, 0.3], [50.0, 60.0, 70.0], [30.0, 30.0, 30.0], layers={"control": False})
    assert "trend-line--control" not in no_control
    assert len(_tips(no_strain)) == 3  # the crosshair columns stay


def test_hit_tips_leave_out_layers_that_are_off(game_env):
    svg = game_env.module.trend_graph_svg([0.5, 0.4], [42.0, 50.0], layers={"strain": False})
    assert all("strain" not in tip for tip in _tips(svg))


def test_layer_buttons_toggle_and_the_legend_follows(game_env):
    _play(game_env, 5)
    assert "ROI" not in game_env.elements["trend-legend"].innerText
    game_env.elements["trend-layer-roi-button"].dispatch("click", None)
    assert "ROI" in game_env.elements["trend-legend"].innerText
    assert "trend-line--roi" in game_env.elements["trend-graph"].innerHTML
    assert game_env.elements["trend-layer-roi-button"].getAttribute("aria-pressed") == "true"
    game_env.elements["trend-layer-wellbeing-button"].dispatch("click", None)
    assert "Dashed: your wellbeing" not in game_env.elements["trend-legend"].innerText
    assert "trend-line--wellbeing" not in game_env.elements["trend-graph"].innerHTML
    game_env.elements["trend-layer-events-button"].dispatch("click", None)
    assert "Markers along the top" not in game_env.elements["trend-legend"].innerText
    assert "trend-event" not in game_env.elements["trend-graph"].innerHTML


def test_the_roi_layer_is_off_by_default(game_env):
    _play(game_env, 5)
    assert "trend-line--roi" not in game_env.elements["trend-graph"].innerHTML


def test_the_roi_line_never_leaves_the_graph_even_for_a_huge_return(game_env):
    svg = game_env.module.trend_graph_svg(
        [0.1, 0.1, 0.1], [50.0, 50.0, 50.0], roi_history=[1.0, 40.0, 100.0], layers={"roi": True}
    )
    points = re.search(r'points="([^"]*)" class="trend-line trend-line--roi"', svg).group(1).split()
    ys = [float(p.split(",")[1]) for p in points]
    assert all(0.0 <= y <= game_env.module.TREND_GRAPH_HEIGHT for y in ys) and min(ys) == pytest.approx(0.0)


def test_a_short_roi_history_is_right_aligned_to_the_latest_rounds(game_env):
    svg = game_env.module.trend_graph_svg(
        [0.1] * 4, [50.0] * 4, roi_history=[2.0, 4.0], layers={"roi": True}
    )
    tips = _tips(svg)
    assert "ROI" not in tips[0] and "ROI" not in tips[1]
    assert "ROI 2.0" in tips[2] and "ROI 4.0" in tips[3]


def test_roi_is_logged_every_round_and_capped(game_env):
    m = game_env.module
    _play(game_env, 4)
    assert len(game_env.region.roi_log) == 4 and all(v >= 0 for v in game_env.region.roi_log)
    game_env.region.roi_log = [1.0] * (m.DRIFT_LOG_MAX_ENTRIES + 20)
    game_env.advance_round()
    assert len(game_env.region.roi_log) == m.DRIFT_LOG_MAX_ENTRIES


# --- I-12: events ---------------------------------------------------------------

def test_a_fresh_region_has_no_events(game_env):
    assert game_env.module.trend_events(game_env.region) == []


def test_band_changes_are_found_from_the_wellbeing_log(game_env):
    region = game_env.region
    region.round_number = 7
    region.wellbeing_log = [20.0, 30.0, 45.0, 50.0, 75.0, 60.0]
    events = [e for e in game_env.module.trend_events(region) if e["kind"] == "band"]
    assert [(e["round"], e["text"]) for e in events] == [
        (3, "wellbeing moved from Struggling to Managing (45)"),
        (5, "wellbeing moved from Managing to Thriving (75)"),
        (6, "wellbeing moved from Thriving to Managing (60)"),
    ]


def test_net_positive_peak_move_and_second_wave_events(game_env):
    region = game_env.region
    region.round_number = 9
    region.strain_log = [0.0, 0.3, 0.7, 0.4, 0.1, 0.0, 0.0, 0.0]
    region.wellbeing_log = [50.0] * 8
    region.net_positive_round = 6
    region.second_wave_start_round = 4
    region.ledger = [{"round": 5, "realloc": 10.0}, {"round": 6, "realloc": 0.0}]
    events = game_env.module.trend_events(region)
    by_kind = {e["kind"]: e["round"] for e in events}
    assert by_kind == {"strain_peak": 3, "second_wave": 4, "realloc": 5, "net_positive": 6}
    assert [e["round"] for e in events] == sorted(e["round"] for e in events)


def test_no_strain_peak_while_strain_stays_stable(game_env):
    region = game_env.region
    region.round_number = 4
    region.strain_log = [0.0, 0.1, 0.05]
    assert all(e["kind"] != "strain_peak" for e in game_env.module.trend_events(region))


def test_events_draw_a_shape_per_kind_in_the_top_strip(game_env):
    m = game_env.module
    events = [
        {"round": 2, "kind": "net_positive", "text": "a"}, {"round": 3, "kind": "band", "text": "b"},
        {"round": 4, "kind": "strain_peak", "text": "c"}, {"round": 5, "kind": "realloc", "text": "d"},
        {"round": 5, "kind": "second_wave", "text": "e"},
    ]
    svg = m.trend_graph_svg([0.1] * 6, [50.0] * 6, events=events)
    for kind in m.TREND_EVENT_KINDS:
        assert f"trend-event--{kind}" in svg
    paths = re.findall(r'<g class="trend-event[^>]*>.*?<path d="([^"]*)"', svg)
    assert len(set(paths)) == len(paths)  # different shapes/positions
    tips = _tips(svg)
    assert "e" in tips[4].split(", ")  # both round-5 events are in that round's tooltip
    assert "d" in tips[4].split(", ")


def test_events_outside_the_visible_range_are_left_out(game_env):
    events = [{"round": 1, "kind": "band", "text": "early"}, {"round": 28, "kind": "band", "text": "late"}]
    svg = game_env.module.trend_graph_svg([0.1] * 30, [50.0] * 30, events=events, view_rounds=10)
    assert svg.count('class="trend-event') == 1 and "late" in svg and "early" not in svg


def test_the_rendered_graph_marks_the_real_run(game_env):
    _play(game_env, 25)
    html = game_env.elements["trend-graph"].innerHTML
    region = game_env.region
    if region.net_positive_round is not None:
        assert f"Round {region.net_positive_round}: integration became a net gain" in html
    assert "trend-event" in html


# --- saving ---------------------------------------------------------------------

def test_roi_log_rides_the_save_and_loads_back(game_env):
    _play(game_env, 5)
    state = json.loads(json.dumps(game_env.module.get_state()))
    assert state["roi_log"] == game_env.region.roi_log
    game_env.region.roi_log = []
    game_env.module.load_state(state)
    assert len(game_env.region.roi_log) == 5


def test_a_fresh_save_has_no_new_keys(game_env):
    state = game_env.module.get_state()
    assert "roi_log" not in state
    assert "second_wave" not in state


def test_bad_roi_logs_load_clean(game_env):
    m = game_env.module
    base = m.get_state()
    for bad in ("junk", 7, {"a": 1}, None):
        assert m.load_state(dict(base, roi_log=bad))
        assert game_env.region.roi_log == []
    mixed = [None, "x", float("nan"), -3, 1e12, True, 2.5]
    assert m.load_state(dict(base, roi_log=mixed))
    assert game_env.region.roi_log == [0.0, 2.5]  # a negative becomes 0; junk, NaN, bools and absurd values drop


def test_an_old_save_without_roi_loads_unchanged(game_env):
    _play(game_env, 4)
    state = json.loads(json.dumps(game_env.module.get_state()))
    del state["roi_log"]
    assert game_env.module.load_state(state)
    assert game_env.region.roi_log == []
    game_env.module.render()
    assert "<svg" in game_env.elements["trend-graph"].innerHTML


def test_second_wave_start_round_is_saved_only_when_known_and_validated(game_env):
    region = game_env.region
    region.second_wave_status = "active"
    region.second_wave_rounds_left = 3
    region.second_wave_start_round = 12
    state = json.loads(json.dumps(game_env.module.get_state()))
    assert state["second_wave"]["start_round"] == 12
    game_env.module.load_state(state)
    assert region.second_wave_start_round == 12
    for bad in ("x", -1, 0, True, 2.5, None):
        state["second_wave"]["start_round"] = bad
        game_env.module.load_state(state)
        assert region.second_wave_start_round is None
    del state["second_wave"]["start_round"]  # an older save
    game_env.module.load_state(state)
    assert region.second_wave_start_round is None


def test_the_wave_start_is_recorded_when_the_wave_begins(game_env):
    region = game_env.region
    region.second_wave_status = "warned"
    region.round_number = 15
    region.advance_round()
    assert region.second_wave_status == "active" and region.second_wave_start_round == 15


# --- markup ---------------------------------------------------------------------

def test_markup_has_the_chips_the_crosshair_host_and_the_tooltip():
    from pathlib import Path

    html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    for key in ("10", "25", "all"):
        assert f'id="trend-range-{key}-button"' in html
    for key in ("strain", "wellbeing", "control", "roi", "events"):
        assert f'id="trend-layer-{key}-button"' in html
    assert 'id="trend-graph" class="trend-graph" tabindex="0"' in html
    assert 'id="trend-tooltip"' in html and 'id="trend-sr"' in html and 'id="trend-legend"' in html
