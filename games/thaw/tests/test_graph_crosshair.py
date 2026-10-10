"""G-16: the mini-graph crosshair data (the hover and key handling itself is the page script)."""

import json
import re


def _points(svg):
    return json.loads(re.search(r"data-pts='([^']*)'", svg).group(1).replace("&quot;", '"'))


def test_named_graph_carries_points_and_a_cross(game_env):
    for _ in range(4):
        game_env.advance_round()
    svg = game_env.elements["graph"].innerHTML
    pts = _points(svg)
    assert len(pts) == 4
    assert pts[0][2].startswith("Round 1: +1.0°, dampening 0%")
    assert pts[-1][2].startswith("Round 4:")
    assert 'tabindex="0"' in svg and "mini-cross" in svg and "mini-dot" in svg
    assert "arrow keys" in svg


def test_unnamed_graph_has_no_crosshair(game_env):
    svg = game_env.module.mini_temp_graph_svg([1.0, 2.0, 3.0])
    assert "data-pts" not in svg and "mini-cross" not in svg and "tabindex" not in svg


def test_dampening_is_recorded_per_round(game_env):
    m = game_env.module
    game_env.advance_round()
    for _ in range(3):
        game_env.invest("preserve")
    game_env.advance_round()
    assert m.region.dampening_history == [0.0, 0.24]
    pts = _points(game_env.elements["graph"].innerHTML)
    assert "dampening 24%" in pts[1][2]


def test_labels_follow_the_unit(game_env):
    for _ in range(3):
        game_env.advance_round()
    game_env.module.set_temp_unit("f")
    game_env.module.render()
    assert "°F" in _points(game_env.elements["graph"].innerHTML)[0][2]


def test_old_saves_without_a_dampening_history_say_not_recorded(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.advance_round()
    state = m.get_state()
    for key in ("region", "region_b", "region_c", "region_d"):
        state[key].pop("dampening_history")
    m.load_state(state)
    assert m.region.dampening_history == []
    labels = [p[2] for p in _points(game_env.elements["graph"].innerHTML)]
    assert all("dampening not recorded" in label for label in labels)


def test_history_round_trips_and_new_rounds_append_after_a_load(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.advance_round()
    state = m.get_state()
    assert state["region"]["dampening_history"] == [0.0, 0.0, 0.0]
    m.load_state(state)
    game_env.invest("monitor")
    game_env.advance_round()
    assert m.region.dampening_history == [0.0, 0.0, 0.0, 0.04]


def test_fresh_game_state_has_no_history_key(game_env):
    assert "dampening_history" not in game_env.module.get_state()["region"]


def test_bad_histories_are_dropped_and_reported(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.advance_round()
    state = m.get_state()
    state["region"]["dampening_history"] = [0.1, "x", 5, None]
    m.load_state(state)
    assert m.region.dampening_history == []
    state["region"]["dampening_history"] = [0.0] * 9  # longer than the temperature history
    m.load_state(state)
    assert m.region.dampening_history == []
    state["region"]["dampening_history"] = "nope"
    m.load_state(state)
    assert "Region A dampening history" in game_env.elements["load-notice-text"].innerText


def test_many_rounds_are_thinned_to_a_bounded_number_of_points(game_env):
    m = game_env.module
    history = [float(i) for i in range(400)]
    svg = m.mini_temp_graph_svg(history, "Region A", [0.0] * 400)
    pts = _points(svg)
    assert len(pts) <= m.CROSSHAIR_MAX_POINTS + 1
    assert pts[-1][2].startswith("Round 400:")
    assert pts[0][2].startswith("Round 1:")


def test_page_script_is_wired_into_both_pages():
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent
    for name in ("index.html", "pc.html"):
        page = (base / name).read_text(encoding="utf-8")
        assert 'const SELECTOR = ".mini-temp-graph-svg[data-pts]"' in page, name
