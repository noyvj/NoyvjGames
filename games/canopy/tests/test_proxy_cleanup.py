"""Audit fix: render_grid() rebuilds every plot tile (and re-registers a
fresh click listener on it) on every render() call — which fires at least
once per tick, i.e. once a second for the life of a session. Each
`create_proxy(...)` call allocates a persistent Python<->JS bridge object
that Pyodide never garbage-collects on its own; without an explicit
`.destroy()` the old proxy from the previous render leaks, growing without
bound over a long play session even though the DOM node it was attached to
is long gone.

These tests assert render_grid() tracks one proxy per plot index and
destroys the previous one before creating its replacement, rather than
letting them accumulate.
"""


def test_rerender_destroys_previous_plot_click_proxy(game_env):
    game_env.module.render()
    first_proxy = game_env.module._plot_click_proxies[0]

    game_env.module.render()
    second_proxy = game_env.module._plot_click_proxies[0]

    assert second_proxy is not first_proxy
    assert first_proxy.destroyed is True


def test_repeated_renders_do_not_accumulate_proxies(game_env):
    for _ in range(5):
        game_env.module.render()

    assert len(game_env.module._plot_click_proxies) == len(game_env.module.plots)


def test_rerendered_tile_click_still_works(game_env):
    """The replacement proxy must still be a live, working click handler —
    destroying the old one must not accidentally break the new one."""
    game_env.module.render()
    game_env.select_tile_click(3)
    assert game_env.module.selected_index == 3
