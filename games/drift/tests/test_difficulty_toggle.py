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


# I20: a one-time callout the first time the arrival-dot stream's density
# visibly changes because of the severity toggle, distinct from ordinary
# background growth (which never sets a baseline at all).


def test_baseline_captured_the_moment_the_toggle_is_switched_on(game_env):
    region = game_env.region
    module = game_env.module
    assert region.severity_toggle_dot_baseline is None
    expected = module.arrival_stream_dot_count(region.arrivals_this_round())
    game_env.elements["accelerated-severity-toggle-button"].dispatch("click", None)
    assert region.severity_toggle_dot_baseline == expected


def test_baseline_not_captured_by_turning_the_toggle_off(game_env):
    region = game_env.region
    assert region.severity_toggle_dot_baseline is None
    game_env.elements["accelerated-severity-toggle-button"].dispatch("click", None)
    game_env.elements["accelerated-severity-toggle-button"].dispatch("click", None)
    assert region.accelerated_severity_enabled is False
    # Turning it off doesn't erase the baseline captured when it was
    # switched on -- it's a permanent "here's where we started" marker.
    assert region.severity_toggle_dot_baseline is not None


def test_baseline_never_set_without_ever_toggling(game_env):
    game_env.advance_round()
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.region.severity_toggle_dot_baseline is None


def test_callout_hidden_before_density_actually_changes(game_env):
    game_env.elements["accelerated-severity-toggle-button"].dispatch("click", None)
    assert game_env.region.severity_density_callout_shown is False
    assert game_env.elements["severity-density-callout"].hidden is True


def test_callout_fires_once_density_moves_away_from_baseline(game_env):
    region = game_env.region
    module = game_env.module
    game_env.elements["accelerated-severity-toggle-button"].dispatch("click", None)
    baseline = region.severity_toggle_dot_baseline
    for _ in range(20):
        game_env.advance_round()
        current = module.arrival_stream_dot_count(region.arrivals_this_round())
        if current != baseline:
            break
    assert current != baseline, "expected the dot count to move within 20 rounds"
    assert region.severity_density_callout_shown is True
    callout = game_env.elements["severity-density-callout"]
    assert callout.hidden is False
    assert callout.innerText == module.SEVERITY_DENSITY_CALLOUT_TEXT

    # Stays shown and doesn't error on further rounds; the flag is sticky.
    game_env.advance_round()
    assert region.severity_density_callout_shown is True
    assert game_env.elements["severity-density-callout"].hidden is False


def test_density_never_changing_without_a_toggle_never_fires_the_callout(game_env):
    # Never toggled -- no baseline exists, so even though arrivals/density
    # rise naturally over many rounds, the I20 callout must never fire.
    for _ in range(20):
        game_env.advance_round()
    assert game_env.region.severity_density_callout_shown is False
    assert game_env.elements["severity-density-callout"].hidden is True


def test_i20_fields_persist_through_save_load(game_env):
    region = game_env.region
    region.severity_toggle_dot_baseline = 3
    region.severity_density_callout_shown = True
    data = game_env.module.get_state()
    assert data["severity_toggle_dot_baseline"] == 3
    assert data["severity_density_callout_shown"] is True

    region.severity_toggle_dot_baseline = None
    region.severity_density_callout_shown = False
    game_env.module.load_state(data)
    assert region.severity_toggle_dot_baseline == 3
    assert region.severity_density_callout_shown is True


def test_i20_fields_default_safely_on_an_old_save_missing_the_keys(game_env):
    region = game_env.region
    old_save = game_env.module.get_state()
    del old_save["severity_toggle_dot_baseline"]
    del old_save["severity_density_callout_shown"]

    # Simulates a fresh module (both fields at their __init__ defaults)
    # loading a save that predates I20 -- the missing keys must not error
    # and must leave the fields at their safe defaults.
    region.severity_toggle_dot_baseline = None
    region.severity_density_callout_shown = False
    game_env.module.load_state(old_save)
    assert region.severity_toggle_dot_baseline is None
    assert region.severity_density_callout_shown is False
