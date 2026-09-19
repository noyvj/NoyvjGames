"""I17: a passive "unmanaged control region" for contrast -- same
background arrival pressure as the player's own region, but never
invested in, so the wellbeing gap makes the value of institutional
preparedness legible without narrating any individual's story.
"""


def test_hidden_before_any_round_completes(game_env):
    assert game_env.elements["control-region-contrast-display"].hidden is True


def test_shown_after_the_first_round(game_env):
    game_env.advance_round()
    display = game_env.elements["control-region-contrast-display"]
    assert display.hidden is False
    assert "wellbeing" in display.innerText.lower()
    assert "contrast" in display.innerText.lower()


def test_unmanaged_region_reaches_critical_strain(game_env):
    control = game_env.module._simulate_control_region(6, False)
    assert control.strain_level() == "critical"


def test_unmanaged_region_never_integrates_anyone(game_env):
    control = game_env.module._simulate_control_region(10, False)
    assert control.integrated_population == 0.0
    assert control.social_cohesion() == 0.0


def test_unmanaged_region_never_invests(game_env):
    control = game_env.module._simulate_control_region(10, False)
    assert control.total_capacity() == 0.0


def test_respects_the_accelerated_severity_setting(game_env):
    slow = game_env.module._simulate_control_region(11, False)
    fast = game_env.module._simulate_control_region(11, True)
    # Faster background severity means more arrivals by the same round,
    # which (with capacity fixed at zero either way) shows up as more
    # total arrivals accumulated.
    assert fast.total_arrivals > slow.total_arrivals


def test_contrast_message_reflects_player_difficulty_toggle(game_env):
    game_env.elements["accelerated-severity-toggle-button"].dispatch("click", None)
    assert game_env.region.accelerated_severity_enabled is True
    game_env.advance_round()
    display = game_env.elements["control-region-contrast-display"]
    expected_control = game_env.module._simulate_control_region(game_env.region.round_number, True)
    assert game_env.module.control_region_contrast_message(expected_control) == display.innerText
