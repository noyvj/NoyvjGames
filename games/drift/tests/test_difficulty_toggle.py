"""Addendum I13: an opt-in "accelerated background severity" difficulty
variant, same off-by-default/persisted-across-save pattern as Grid's
C16 steeper-demand-growth toggle. Only ever changes how fast
background_severity itself rises -- arrivals_this_round()/strain math
already scale off background_severity, so this one knob is enough.
"""

import pytest


def test_accelerated_severity_off_by_default(game_env):
    assert game_env.region.accelerated_severity_enabled is False


def test_toggle_flips_the_flag(game_env):
    game_env.elements["accelerated-severity-toggle-button"].dispatch("click", None)
    assert game_env.region.accelerated_severity_enabled is True
    game_env.elements["accelerated-severity-toggle-button"].dispatch("click", None)
    assert game_env.region.accelerated_severity_enabled is False


def test_severity_rises_normally_when_disabled(game_env):
    region = game_env.region
    starting = region.background_severity
    game_env.advance_round()
    assert region.background_severity == pytest.approx(
        starting + game_env.module.BACKGROUND_SEVERITY_RISE_PER_ROUND
    )


def test_severity_rises_faster_when_enabled(game_env):
    region = game_env.region
    region.accelerated_severity_enabled = True
    starting = region.background_severity
    game_env.advance_round()
    expected_rise = (
        game_env.module.BACKGROUND_SEVERITY_RISE_PER_ROUND
        * game_env.module.ACCELERATED_SEVERITY_MULTIPLIER
    )
    assert region.background_severity == pytest.approx(starting + expected_rise)


def test_render_reflects_toggle_state_in_button_text(game_env):
    game_env.module.render()
    button = game_env.elements["accelerated-severity-toggle-button"]
    assert "OFF" in button.innerText
    assert "active" not in button.classList

    game_env.region.accelerated_severity_enabled = True
    game_env.module.render()
    assert "ON" in button.innerText
    assert "active" in button.classList


def test_accelerated_severity_persists_through_save_load(game_env):
    game_env.region.accelerated_severity_enabled = True
    data = game_env.module.get_state()
    assert data["accelerated_severity_enabled"] is True

    game_env.region.accelerated_severity_enabled = False
    game_env.module.load_state(data)
    assert game_env.region.accelerated_severity_enabled is True
