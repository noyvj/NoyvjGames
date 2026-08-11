"""Iteration pass: a one-tick visual cue at the exact moment the
feedback loop crosses its tipping threshold, plus an ongoing visually
alarming state for the melt-status line once it has.

Note: game_env.advance_round() dispatches the button click, which
(via on_advance_round) calls render() immediately — that render call
would itself consume the one-tick just_started_melting flag before the
test gets a chance to inspect it. So state-level assertions here call
region.advance_round() directly, bypassing the auto-render, and only
call render() explicitly where the render behavior itself is under
test.
"""

import pytest


def test_just_started_melting_false_initially(game_env):
    assert game_env.region.just_started_melting is False


def test_just_started_melting_true_the_round_threshold_is_crossed(game_env):
    # base rise 1.0/round -> crosses MELT_THRESHOLD (10.0) on round 10
    for _ in range(10):
        game_env.region.advance_round()
    assert game_env.region.just_started_melting is True


def test_just_started_melting_cleared_by_render_and_stays_false(game_env):
    for _ in range(10):
        game_env.region.advance_round()
    assert game_env.region.just_started_melting is True

    game_env.module.render()  # consumes the one-tick flag, as the real app does
    assert game_env.region.just_started_melting is False

    game_env.region.advance_round()  # threshold already crossed -> no re-trigger
    assert game_env.region.just_started_melting is False


def test_render_applies_tipping_flash_class_once(game_env):
    for _ in range(10):
        game_env.region.advance_round()
    game_env.module.render()
    assert game_env.elements["game"].className == "tipping-flash"

    game_env.module.render()  # a second render shouldn't re-flash
    assert game_env.elements["game"].className == ""


def test_render_game_class_empty_before_tipping_point(game_env):
    game_env.module.render()
    assert game_env.elements["game"].className == ""


def test_render_melt_status_gets_active_class_once_melting(game_env):
    for _ in range(10):
        game_env.region.advance_round()
    game_env.module.render()
    assert "melt-status--active" in game_env.elements["melt-status-display"].className


def test_render_melt_status_no_active_class_before_melting(game_env):
    game_env.module.render()
    assert "melt-status--active" not in game_env.elements["melt-status-display"].className
