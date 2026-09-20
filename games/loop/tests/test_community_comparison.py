"""H5 (planning/TODO.md, needs Z1): a live cross-player comparison for
lifetime circular share, via the optional window.loopCompare() JS hook
that index.html defines -- same Python-side-hook-call/JS-side-fetch
architecture as Grid's own C15 (games/grid/game.py's _request_comparison()
+ window.gridCompare), including the same safe-no-op-under-test shape.
Mirrors games/grid/tests/test_round2_items.py::test_c15_summary_has_fallback_and_calls_hook."""

import sys
from pathlib import Path


def test_render_calls_loop_compare_hook_with_lifetime_circular_fraction(game_env):
    game_env.chain.total_produced = 100.0
    game_env.chain.total_extracted = 40.0
    expected = game_env.chain.lifetime_circular_fraction()
    assert expected == 0.6

    calls = []

    class W:
        loopCompare = staticmethod(lambda frac: calls.append(frac))

    sys.modules["js"].window = W()
    try:
        game_env.module.render()
    finally:
        del sys.modules["js"].window

    assert calls == [expected]


def test_render_recomputes_the_hook_argument_on_every_call(game_env):
    """Not a stale/cached value -- a later render() with different lifetime
    state passes the freshly-recomputed fraction, not the first call's."""
    calls = []

    class W:
        loopCompare = staticmethod(lambda frac: calls.append(frac))

    sys.modules["js"].window = W()
    try:
        game_env.chain.total_produced, game_env.chain.total_extracted = 100.0, 100.0
        game_env.module.render()
        game_env.chain.total_produced, game_env.chain.total_extracted = 100.0, 0.0
        game_env.module.render()
    finally:
        del sys.modules["js"].window

    assert calls == [0.0, 1.0]


def test_render_is_a_safe_no_op_without_the_hook(game_env):
    """The pytest fake-DOM harness's `js` module never fakes `window` at
    all (tests/conftest.py), so `from js import window` raises ImportError
    inside _request_community_comparison() -- render() must not raise."""
    assert not hasattr(sys.modules["js"], "window")
    game_env.module.render()


def test_render_is_a_safe_no_op_when_window_has_no_loop_compare(game_env):
    class W:
        pass

    sys.modules["js"].window = W()
    try:
        game_env.module.render()  # must not raise (getattr default is None)
    finally:
        del sys.modules["js"].window


def test_community_comparison_display_element_ships_with_a_graceful_fallback():
    """game.py never writes into #community-comparison-display itself --
    only window.loopCompare() does -- so the static HTML fallback text is
    what a player sees until/unless that fetch succeeds. Same division of
    labor as Grid's own COMPARE_FALLBACK, just baked into static markup
    here instead of Python-generated panel HTML."""
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text()
    assert 'id="community-comparison-display"' in html
    assert "isn't available yet" in html
    assert "window.loopCompare" in html
    assert "/stats/games/loop/percentile" in html
    assert "lifetime_circular_fraction" in html
