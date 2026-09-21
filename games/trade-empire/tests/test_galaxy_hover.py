"""J16 — hover tooltip on the endgame galaxy canvas."""

from types import SimpleNamespace


def test_dot_positions_are_stable_and_inside_the_canvas(game_env):
    game = game_env.module
    first = game.endgame_galaxy_dot_position(0)
    assert first == game.endgame_galaxy_dot_position(0)
    size = game.ENDGAME_GALAXY_CANVAS_SIZE
    for i in range(game.ENDGAME_GALAXY_DOT_CAP):
        position = game.endgame_galaxy_dot_position(i)
        if position is not None:
            assert 0 <= position[0] <= size and 0 <= position[1] <= size


def test_hover_names_the_nearest_dot(game_env):
    game = game_env.module
    x, y = game.endgame_galaxy_dot_position(3)
    text = game.endgame_galaxy_hover_text(x + 1, y - 1, 50)
    assert "world #4 of 50" in text


def test_hover_away_from_every_dot_gives_the_default_text(game_env):
    game = game_env.module
    assert game.endgame_galaxy_hover_text(-50, -50, 50) == game.ENDGAME_GALAXY_DEFAULT_TITLE


def test_hover_ignores_dots_beyond_the_world_count(game_env):
    game = game_env.module
    x, y = game.endgame_galaxy_dot_position(10)
    assert game.endgame_galaxy_hover_text(x, y, 5) == game.ENDGAME_GALAXY_DEFAULT_TITLE


def test_mousemove_updates_the_canvas_title_and_wiring_happens_once(game_env):
    game = game_env.module
    game.background_world_count = lambda: 50
    canvas = game_env.elements["endgame-galaxy-canvas"]
    game.render_endgame_galaxy(50)
    game.render_endgame_galaxy(50)
    assert len(canvas._listeners["mousemove"]) == 1
    x, y = game.endgame_galaxy_dot_position(0)
    canvas.dispatch("mousemove", SimpleNamespace(offsetX=x, offsetY=y))
    assert "world #1 of 50" in canvas.title
    canvas.dispatch("mousemove", SimpleNamespace(offsetX=-40, offsetY=-40))
    assert canvas.title == game.ENDGAME_GALAXY_DEFAULT_TITLE
