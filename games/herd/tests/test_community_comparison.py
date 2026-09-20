"""F7 (planning/TODO.md, "farm cooperative" comparison): a cross-player
percentile comparison against the shared aggregate-stats endpoint (Z1,
now built and deployed -- app/stats.py registers "methane" as one of
Herd's whitelisted STATS_FIELDS). Byte-for-byte the same optional-hook
architecture as Grid's own C15 (`window.gridCompare`/`_request_comparison`
in games/grid/game.py + games/grid/tests/test_round2_items.py's own
`test_c15_summary_has_fallback_and_calls_hook`), the reference
integration for this exact feature in this hub.

The real `fetch()` call itself lives in index.html's plain-JS
`window.herdCompare` definition and can't be exercised from these Python
tests (same limitation Grid's own C15 test suite has) -- these tests only
cover the Python side: the optional-hook call fires with the right value,
it's a safe no-op when the hook doesn't exist (the fake-DOM harness's `js`
module never provides `window` by default -- see conftest.py's
`_install_pyodide_fakes`), and the report card panel always carries the
fallback-text element for the hook to fill in."""

import sys


def test_report_card_has_compare_fallback_before_any_hook_runs(game_env):
    game_env.toggle_report_card()
    assert "isn't available yet" in game_env.elements["report-card-panel"].innerHTML
    assert "report-card-compare" in game_env.elements["report-card-panel"].innerHTML


def test_opening_report_card_is_a_safe_no_op_without_a_hook(game_env):
    # No js.window at all by default -- from js import window raises
    # ImportError inside _request_comparison(), which must be swallowed
    # rather than crashing the whole render.
    game_env.toggle_report_card()
    assert "isn't available yet" in game_env.elements["report-card-panel"].innerHTML


def test_opening_report_card_calls_the_hook_with_methane_and_round(game_env):
    calls = []

    class W:
        herdCompare = staticmethod(lambda methane, round_number: calls.append((methane, round_number)))

    sys.modules["js"].window = W()
    try:
        game_env.toggle_report_card()
    finally:
        del sys.modules["js"].window
    assert calls == [(0.0, game_env.farm.round_number)]


def test_hook_receives_current_methane_after_rounds_advance(game_env):
    game_env.grow_herd()
    game_env.advance_round()
    game_env.advance_round()
    expected_methane = float(game_env.farm.methane)
    assert expected_methane > 0.0

    calls = []

    class W:
        herdCompare = staticmethod(lambda methane, round_number: calls.append((methane, round_number)))

    sys.modules["js"].window = W()
    try:
        game_env.toggle_report_card()
    finally:
        del sys.modules["js"].window
    assert calls == [(expected_methane, game_env.farm.round_number)]


def test_hook_is_re_asked_on_a_later_render_while_panel_stays_open(game_env):
    game_env.toggle_report_card()  # opens with no hook installed -- fine

    calls = []

    class W:
        herdCompare = staticmethod(lambda methane, round_number: calls.append((methane, round_number)))

    sys.modules["js"].window = W()
    try:
        game_env.grow_herd()  # triggers a render(); report_card_open stays True
    finally:
        del sys.modules["js"].window
    assert len(calls) == 1
    assert calls[0] == (float(game_env.farm.methane), game_env.farm.round_number)


def test_hook_is_not_called_while_report_card_is_closed(game_env):
    calls = []

    class W:
        herdCompare = staticmethod(lambda methane, round_number: calls.append((methane, round_number)))

    sys.modules["js"].window = W()
    try:
        game_env.grow_herd()  # report card starts closed -- render() shouldn't ask
    finally:
        del sys.modules["js"].window
    assert calls == []


def test_compare_fallback_constant_matches_panel_text(game_env):
    assert game_env.module.COMPARE_FALLBACK in game_env.module.report_card_html()
