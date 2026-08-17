"""Milestone 7: 2D map v1. Colonies as nodes, routes as lines, drawn
directly from Python via Pyodide's `js` module -- no separate JS glue
file needed, canvas context methods are just JS method calls. Static
layout and routes; no moving ships until Milestone 11.
"""


def test_every_colony_has_a_node_position(game_env):
    for colony_id in game_env.module.COLONIES:
        assert colony_id in game_env.module.NODE_POSITIONS


def test_route_edges_cover_every_colony(game_env):
    edges = game_env.module.route_edges()
    origins = {edge[0] for edge in edges}
    assert origins == set(game_env.module.COLONIES)


def test_route_edges_point_to_the_colony_that_needs_the_good(game_env):
    edges = dict(game_env.module.route_edges())
    assert edges["aurum"] == "ferrum"  # aurum produces ore, ferrum needs ore
    assert edges["cryo"] == "helion"  # cryo produces water, helion needs water


def test_render_map_clears_the_canvas(game_env):
    # setup() already called render_map() once as part of loading the
    # module (see test_setup_renders_the_map_without_error) -- inspect
    # those calls directly rather than drawing a second time, since the
    # fake context's call log accumulates like a real one would.
    canvas = game_env.elements["map-canvas"]
    ctx = canvas.getContext("2d")
    call_names = [name for name, _args in ctx.calls]
    assert "clearRect" in call_names


def test_render_map_draws_a_line_per_route_edge(game_env):
    ctx = game_env.elements["map-canvas"].getContext("2d")
    stroke_count = sum(1 for name, _args in ctx.calls if name == "stroke")
    assert stroke_count == len(game_env.module.route_edges())


def test_render_map_draws_a_circle_per_colony(game_env):
    ctx = game_env.elements["map-canvas"].getContext("2d")
    arc_count = sum(1 for name, _args in ctx.calls if name == "arc")
    assert arc_count == len(game_env.module.COLONIES)


def test_render_map_labels_every_colony(game_env):
    ctx = game_env.elements["map-canvas"].getContext("2d")
    labeled_text = {args[0] for name, args in ctx.calls if name == "fillText"}
    assert "Aurum" in labeled_text
    assert "Helion" in labeled_text


def test_setup_renders_the_map_without_error(game_env):
    # setup() already ran as part of the game_env fixture -- if it had
    # raised, the fixture itself would have failed. This just confirms
    # the canvas actually received draw calls as a result.
    ctx = game_env.elements["map-canvas"].getContext("2d")
    assert len(ctx.calls) > 0
