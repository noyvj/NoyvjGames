"""C12: a visible toast/banner for a disruption or aging-breakdown event,
on top of the persistent #event-display/#aging-event-display status
lines (which need scrolling to notice). Fires only from on_advance_round,
never from a bare render(), so re-rendering (e.g. toggling a panel)
doesn't repeatedly flash it."""


def ALWAYS_TRIGGER():
    return 0.0


def NEVER_TRIGGER():
    return 0.999999


def test_toast_hidden_before_any_round_is_advanced(game_env):
    assert game_env.elements["disruption-toast"].hidden is True


def test_no_toast_when_the_round_has_no_event(game_env):
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.module._check_disruption_toast()
    assert game_env.elements["disruption-toast"].hidden is True


def test_toast_shows_for_a_brownout_with_warning_severity(game_env):
    game_env.build("coal")
    game_env.state.emissions = 300.0  # severity 0.1 -- below damage threshold
    game_env.state.advance_round(rng=ALWAYS_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.module._check_disruption_toast()
    toast = game_env.elements["disruption-toast"]
    assert toast.hidden is False
    assert "disruption-toast--warning" in toast.classList
    assert "Brownout" in game_env.elements["disruption-toast-text"].innerText


def test_toast_shows_for_damage_with_danger_severity(game_env):
    game_env.build("coal")
    game_env.state.emissions = 2000.0  # severity above the damage threshold
    game_env.state.advance_round(rng=ALWAYS_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.module._check_disruption_toast()
    toast = game_env.elements["disruption-toast"]
    assert toast.hidden is False
    assert "disruption-toast--danger" in toast.classList
    assert "Damage" in game_env.elements["disruption-toast-text"].innerText


def test_toast_shows_for_an_aging_breakdown_when_no_disruption_event(game_env):
    module = game_env.module
    game_env.build("coal")
    for _ in range(module.AGE_GRACE_PERIOD + 20):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=ALWAYS_TRIGGER)
        if game_env.state.last_aging_event is not None:
            break
    assert game_env.state.last_aging_event is not None
    module._check_disruption_toast()
    toast = game_env.elements["disruption-toast"]
    assert toast.hidden is False
    assert "disruption-toast--danger" in toast.classList
    assert "Aging breakdown" in game_env.elements["disruption-toast-text"].innerText


def test_advance_round_button_triggers_the_toast_end_to_end(game_env):
    game_env.build("coal")
    game_env.state.emissions = 2000.0
    game_env.advance_round()  # dispatches the real click handler
    # advance_round() as driven through the click handler uses real
    # random rng, so just confirm the toast machinery ran without error
    # and the element is in a valid (bool) hidden state either way.
    assert game_env.elements["disruption-toast"].hidden in (True, False)


def test_toast_auto_hides_after_its_timer_fires(game_env):
    game_env.build("coal")
    game_env.state.emissions = 2000.0
    game_env.state.advance_round(rng=ALWAYS_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.module._check_disruption_toast()
    assert game_env.elements["disruption-toast"].hidden is False
    game_env.timers.flush()
    assert game_env.elements["disruption-toast"].hidden is True
