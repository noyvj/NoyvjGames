"""G11 (planning/TODO.md, needs Z1): the community "average acceleration
factor" comparison. Follows Grid's C15 architecture exactly
(games/grid/game.py's test_c15_summary_has_fallback_and_calls_hook in
tests/test_round2_items.py) -- a Python-side optional JS hook call, safe
no-op absent the hook, and the real fetch()/wording living entirely in
index.html's own inline <script> (untestable from here, same limitation
Grid's own suite documents).

Also covers the new average_acceleration_factor/acceleration_samples
RegionState fields the comparison metric rides on -- genuinely new
tracked state, not derivable from anything already in game.py, so it
needs its own coverage the same way Grid's maintenance_actions_count/
current_clean_streak needed dedicated tests when they were added.
"""

import sys


def test_average_acceleration_factor_starts_at_steady_state(game_env):
    region = game_env.region
    assert region.average_acceleration_factor == 1.0
    assert region.acceleration_samples == 0


def test_average_stays_at_steady_state_before_melt_starts(game_env):
    region = game_env.region
    module = game_env.module
    # MELT_THRESHOLD is 10.0 and the background rise is 1.0/round with no
    # investment, so 9 rounds keeps temperature at 9.0 -- still pre-melt.
    for _ in range(9):
        game_env.advance_round()
    assert region.temperature < module.MELT_THRESHOLD
    assert region.average_acceleration_factor == 1.0
    assert region.acceleration_samples == 9


def test_average_is_diluted_by_earlier_steady_rounds_once_melting(game_env):
    """Once melt kicks in, acceleration_factor() rises above 1.0x -- but
    the lifetime average, having also averaged in every earlier
    steady-state (1.0x) round, must sit strictly between 1.0 and the
    current instantaneous reading. A fragile exact-float assertion here
    would just be re-deriving the feedback formula in the test; this
    relative bound is the real invariant the running-average is supposed
    to satisfy."""
    region = game_env.region
    module = game_env.module
    for _ in range(15):
        game_env.advance_round()
    assert region.temperature > module.MELT_THRESHOLD  # confirms melt actually started
    assert region.acceleration_factor() > 1.0
    assert 1.0 < region.average_acceleration_factor < region.acceleration_factor()
    assert region.acceleration_samples == 15


def test_average_acceleration_factor_round_trips_through_save_load(game_env):
    module = game_env.module
    for _ in range(12):
        game_env.advance_round()
    snapshot = module.get_state()
    average_at_snapshot = region_average = module.region.average_acceleration_factor
    samples_at_snapshot = module.region.acceleration_samples

    for _ in range(5):
        game_env.advance_round()
    assert module.region.average_acceleration_factor != average_at_snapshot
    assert module.region.acceleration_samples != samples_at_snapshot

    module.load_state(snapshot)
    assert module.region.average_acceleration_factor == region_average
    assert module.region.acceleration_samples == samples_at_snapshot


def test_load_state_with_missing_acceleration_fields_does_not_crash(game_env):
    """An older save made before G11 existed won't have these two keys at
    all -- same per-field fallback-to-current-value contract every other
    field in _apply_region_state() already honors."""
    module = game_env.module
    for _ in range(3):
        game_env.advance_round()
    snapshot = module.get_state()
    del snapshot["region"]["average_acceleration_factor"]
    del snapshot["region"]["acceleration_samples"]

    live_average = module.region.average_acceleration_factor
    live_samples = module.region.acceleration_samples
    result = module.load_state(snapshot)
    assert result is True
    assert module.region.average_acceleration_factor == live_average
    assert module.region.acceleration_samples == live_samples


def test_community_compare_panel_is_hidden_by_default(game_env):
    assert game_env.elements["community-compare-panel"].hidden is True


def test_toggle_opens_and_closes_the_panel(game_env):
    game_env.toggle_community_compare()
    assert game_env.elements["community-compare-panel"].hidden is False
    game_env.toggle_community_compare()
    assert game_env.elements["community-compare-panel"].hidden is True


def test_toggle_button_label_reflects_open_state(game_env):
    game_env.toggle_community_compare()
    assert "Hide" in game_env.elements["community-compare-toggle-button"].innerText
    game_env.toggle_community_compare()
    assert "Community Comparison" in game_env.elements["community-compare-toggle-button"].innerText


def test_panel_shows_fallback_text_absent_the_js_hook(game_env):
    """Mirrors Grid's own C15 test: with no window.thawCompare hook
    present (the normal pytest fake-DOM case), the panel must show the
    plain-English "not available yet" fallback, never raw JSON or an
    error, and must not raise."""
    game_env.toggle_community_compare()
    panel = game_env.elements["community-compare-panel"]
    assert game_env.module.COMMUNITY_COMPARE_FALLBACK in panel.innerHTML


def test_panel_does_not_render_while_closed(game_env):
    panel = game_env.elements["community-compare-panel"]
    assert panel.innerHTML == ""


def test_opening_the_panel_calls_the_hook_with_average_acceleration_factor(game_env):
    """Mirrors games/grid/tests/test_round2_items.py's
    test_c15_summary_has_fallback_and_calls_hook exactly: the fake-DOM
    harness's `js` module never provides `window` by default, so the
    fake hook is installed and torn down manually around the call."""
    module = game_env.module
    for _ in range(15):
        game_env.advance_round()
    expected = module.region.average_acceleration_factor
    calls = []

    class W:
        thawCompare = staticmethod(lambda accel: calls.append(accel))

    sys.modules["js"].window = W()
    try:
        game_env.toggle_community_compare()
    finally:
        del sys.modules["js"].window
    assert calls == [expected]


def test_hook_is_called_again_on_every_render_while_panel_stays_open(game_env):
    """render() re-drives every open panel every action (matches Grid's
    own summary panel and this game's achievements/changelog panels) --
    confirms _request_community_comparison() is wired into render(), not
    only into the toggle handler itself."""
    calls = []

    class W:
        thawCompare = staticmethod(lambda accel: calls.append(accel))

    sys.modules["js"].window = W()
    try:
        game_env.toggle_community_compare()
        assert len(calls) == 1
        game_env.advance_round()
        assert len(calls) == 2
    finally:
        del sys.modules["js"].window


def test_hook_is_a_safe_no_op_when_absent(game_env):
    """No js.window at all (the normal pytest case) -- opening the panel
    and advancing a round must not raise."""
    game_env.toggle_community_compare()
    game_env.advance_round()  # would raise if _request_community_comparison() ever assumed a hook


def test_checking_community_compare_never_mutates_game_state(game_env):
    module = game_env.module
    game_env.invest("output")
    before = module.get_state()
    game_env.toggle_community_compare()
    game_env.toggle_community_compare()
    after = module.get_state()
    assert before == after
