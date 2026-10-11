"""G-11: long histories are drawn as summary points; saves and shorter games are untouched."""
import json
import re


def _points(svg, css_class="mini-temp-line"):
    match = re.search(rf'<polyline points="([^"]+)" class="{css_class}"', svg)
    return match.group(1).split() if match else []


def test_short_history_is_drawn_whole(game_env):
    game = game_env.module
    values = [i * 0.5 for i in range(120)]
    assert game.graph_indexes(values) == list(range(120))
    assert len(_points(game.mini_temp_graph_svg(values))) == 120


def test_long_history_is_capped_and_keeps_ends_and_recent_rounds(game_env):
    game = game_env.module
    values = [i * 0.1 for i in range(1000)]
    keep = game.graph_indexes(values)
    assert len(keep) <= game.GRAPH_MAX_POINTS
    assert keep[0] == 0 and keep[-1] == 999
    assert keep == sorted(set(keep))
    assert keep[-game.GRAPH_RECENT_FULL:] == list(range(1000 - game.GRAPH_RECENT_FULL, 1000))


def test_summary_points_keep_a_peak(game_env):
    game = game_env.module
    values = [1.0] * 800
    values[311] = 9.0  # one spike far in the past
    keep = game.graph_indexes(values)
    assert 311 in keep


def test_every_graph_uses_the_cap(game_env):
    game = game_env.module
    values = [i * 0.05 for i in range(900)]
    assert len(_points(game.mini_temp_graph_svg(values, name="Region A"))) <= game.GRAPH_MAX_POINTS
    assert len(_points(game.focus_graph_svg(values, "Region A", "a"))) <= game.GRAPH_MAX_POINTS
    spark = game.tiny_line_svg(values, "A")
    assert len(re.search(r'points="([^"]+)"', spark).group(1).split()) <= game.GRAPH_MAX_POINTS


def test_long_history_graph_keeps_its_x_positions(game_env):
    game = game_env.module
    values = [i * 0.05 for i in range(900)]
    pts = _points(game.mini_temp_graph_svg(values))
    assert pts[0].startswith("0.0,")
    assert pts[-1].startswith(f"{game.MINI_GRAPH_WIDTH:.1f},")


def test_saves_keep_the_full_history(game_env):
    game = game_env.module
    game.region.temperature_history = [i * 0.01 for i in range(500)]
    state = json.loads(json.dumps(game.get_state()))
    assert len(state["region"]["temperature_history"]) == 500


def test_readout_text_is_measured_only_while_shown(game_env):
    game = game_env.module
    element = game_env.elements["history-readout"]
    element.hidden = True
    element.innerText = ""
    game.render()
    assert element.innerText == ""
    element.hidden = False
    game.region.temperature_history = [0.1 * i for i in range(300)]
    game.render()
    assert "300 rounds stored" in element.innerText
    assert f"draw {len(game.graph_indexes(game.region.temperature_history))} points" in element.innerText
    assert "KB" in element.innerText


def test_render_stays_quick_with_a_very_long_run(game_env):
    game = game_env.module
    for r in (game.region, game.region_b, game.region_c, game.region_d):
        r.temperature_history = [0.02 * i for i in range(3000)]
        r.dampening_history = [0.5] * 3000
    game.render()
    svg = game.mini_temp_graph_svg(game.region.temperature_history, "Region A", game.region.dampening_history)
    assert len(svg) < 20000
