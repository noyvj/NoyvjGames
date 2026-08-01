"""Milestone 7: visual pass — per-state tile icons (so state doesn't rely
on color alone) and a grid-level state-count summary.
"""

BARE = "bare"
REPLANTING = "replanting"
RECOVERED = "recovered"


def test_state_breakdown_starts_all_preserved(game_env):
    counts = game_env.module.state_breakdown()
    assert counts["preserved"] == 36
    assert counts["bare"] == 0
    assert counts["replanting"] == 0
    assert counts["recovered"] == 0


def test_state_breakdown_updates_after_clear(game_env):
    game_env.select(0)
    game_env.clear()
    counts = game_env.module.state_breakdown()
    assert counts["preserved"] == 35
    assert counts["bare"] == 1


def test_state_breakdown_updates_after_replant(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    plot.replant()
    counts = game_env.module.state_breakdown()
    assert counts["replanting"] == 1
    assert counts["bare"] == 0


def test_state_breakdown_text_matches_counts(game_env):
    game_env.select(0)
    game_env.clear()
    text = game_env.module.state_breakdown_text()
    assert "35 preserved" in text
    assert "1 bare" in text
    assert "0 replanting" in text
    assert "0 recovered" in text


def test_render_updates_breakdown_display(game_env):
    game_env.select(0)
    game_env.clear()
    displayed = game_env.elements["state-breakdown-display"].innerText
    assert "1 bare" in displayed


def test_preserved_tile_shows_tree_icon(game_env):
    tile = game_env.elements["plot-0"]
    assert tile.innerText == game_env.module.STATE_ICON["preserved"]
    assert tile.innerText != ""


def test_bare_tile_shows_no_icon(game_env):
    game_env.select(0)
    game_env.clear()
    tile = game_env.elements["plot-0"]
    assert tile.innerText == ""


def test_replanting_tile_shows_seedling_icon(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    plot.replant()
    game_env.module.render()
    tile = game_env.elements["plot-0"]
    assert tile.innerText == game_env.module.STATE_ICON["replanting"]


def test_recovered_tile_shows_deciduous_icon(game_env):
    plot = game_env.plot(0)
    plot.state = RECOVERED
    game_env.module.render()
    tile = game_env.elements["plot-0"]
    assert tile.innerText == game_env.module.STATE_ICON["recovered"]
