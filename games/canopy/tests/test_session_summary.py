"""B1/B6/B18/B20 (planning/TODO.md "Per-game: Canopy"): a player-triggered
session-summary panel -- a closing counterfactual line (B20), a sparkline
of income vs. standing value over the session (B6), and a shareable text
snippet (B18), all gathered under one toggle (B1)."""

import math


def test_summary_panel_hidden_by_default(game_env):
    assert game_env.elements["session-summary-panel"].hidden is True


def test_toggling_opens_and_closes_the_panel(game_env):
    game_env.toggle_session_summary()
    assert game_env.elements["session-summary-panel"].hidden is False
    game_env.toggle_session_summary()
    assert game_env.elements["session-summary-panel"].hidden is True


def test_counterfactual_message_before_any_ticks(game_env):
    m = game_env.module
    assert m._session_ticks == 0
    assert "Not enough time" in m.counterfactual_message()


def test_counterfactual_matches_actual_when_nothing_ever_cleared(game_env):
    """If every plot stays PRESERVED the whole time (the default, no
    action taken), actual standing value should track the ideal exactly
    -- the counterfactual is a genuine "what if" only once a plot has been
    cleared or replanted."""
    m = game_env.module
    game_env.tick(10)
    ideal = m.counterfactual_standing_value()
    actual = m.standing_forest_value()
    assert math.isclose(actual, ideal, rel_tol=1e-9)
    assert "patience paid off" in m.counterfactual_message()


def test_counterfactual_shows_shortfall_after_clearing(game_env):
    m = game_env.module
    game_env.tick(10)
    game_env.select(0)
    game_env.clear()
    game_env.tick(5)
    message = m.counterfactual_message()
    assert "%" in message
    assert m.standing_forest_value() < m.counterfactual_standing_value()


def test_counterfactual_scales_with_current_grid_size(game_env):
    """A "large" (B13) session compares against its own larger ideal, not
    a hardcoded 36-plot one."""
    m = game_env.module
    game_env.change_grid_size("large")
    game_env.tick(5)
    ideal = m.counterfactual_standing_value()
    assert ideal == len(m.plots) * m._ideal_accrual_for_ticks(5)


def test_session_history_svg_empty_before_any_ticks(game_env):
    m = game_env.module
    assert m.session_history_svg() == ""


def test_session_history_svg_renders_after_ticks(game_env):
    m = game_env.module
    game_env.tick(3)
    svg = m.session_history_svg()
    assert svg.startswith("<svg")
    assert svg.count("<polyline") == 2


def test_value_history_is_capped(game_env):
    m = game_env.module
    game_env.tick(m.VALUE_HISTORY_MAX_POINTS + 20)
    assert len(m._value_history) == m.VALUE_HISTORY_MAX_POINTS


def test_reset_session_clears_history_and_tick_count(game_env):
    m = game_env.module
    game_env.tick(5)
    assert m._session_ticks == 5
    assert len(m._value_history) == 5
    game_env.reset_session()
    assert m._session_ticks == 0
    assert len(m._value_history) == 0


def test_share_snippet_contains_key_stats(game_env):
    m = game_env.module
    game_env.tick(5)
    game_env.select(0)
    game_env.clear()
    snippet = m.share_snippet()
    assert "Canopy" in snippet
    assert f"{m.total_income:.1f}" in snippet
    assert f"{m.standing_forest_value():.1f}" in snippet
    assert f"/{len(m.plots)} plots" in snippet


def test_opening_panel_populates_all_fields(game_env):
    m = game_env.module
    game_env.tick(5)
    game_env.toggle_session_summary()
    assert len(game_env.elements["session-summary-counterfactual"].innerText) > 0
    assert len(game_env.elements["session-summary-share-text"].innerText) > 0
    assert "<svg" in game_env.elements["session-summary-sparkline"].innerHTML


def test_toggle_button_label_reflects_open_state(game_env):
    toggle = game_env.elements["session-summary-toggle-button"]
    game_env.module.render()
    assert "Session Summary" in toggle.innerText
    game_env.toggle_session_summary()
    assert "Hide" in toggle.innerText
