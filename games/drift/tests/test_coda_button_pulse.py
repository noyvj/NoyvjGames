"""Addendum I15: a one-time highlight/pulse on the coda button the
moment its long-horizon story first becomes available
(has_long_horizon_story() flips from False to True), since previously
there was no cue that a new option just appeared. Same
flag-set-in-advance_round/consumed-in-render pattern as Thaw's
just_started_melting.

Note: game_env.advance_round() dispatches the button click, which also
calls render() (see on_advance_round()) -- that would immediately
consume the flag before a test could observe it. Tests that need to
inspect the flag *before* it's consumed call region.advance_round()
directly instead.
"""


def test_coda_just_became_available_false_initially(game_env):
    assert game_env.region.coda_just_became_available is False


def test_flag_set_when_first_integration_happens(game_env):
    region = game_env.region
    # Round 1: no services capacity yet, and integration_this_round() is
    # capped by pending_population() (arrivals accrued so far), which is
    # still zero at the very start of round 1 -- so this round only
    # accrues arrivals, it can't integrate anyone yet.
    game_env.advance_round()
    region.capacity["services"] = 100.0
    region.advance_round()  # direct state call -- flag observable before render() resets it
    assert region.integrated_population > 0
    assert region.coda_just_became_available is True


def test_flag_not_set_again_on_a_later_round(game_env):
    region = game_env.region
    game_env.advance_round()
    region.capacity["services"] = 100.0
    region.advance_round()
    assert region.coda_just_became_available is True
    region.coda_just_became_available = False  # simulate render() having consumed it
    region.advance_round()
    assert region.coda_just_became_available is False


def test_render_consumes_the_flag_and_adds_pulse_class(game_env):
    region = game_env.region
    game_env.advance_round()
    region.capacity["services"] = 100.0
    region.advance_round()
    assert region.coda_just_became_available is True

    game_env.module.render()
    assert region.coda_just_became_available is False
    assert "coda-button--pulse" in game_env.elements["coda-button"].classList


def test_render_does_not_pulse_without_the_flag(game_env):
    game_env.module.render()
    assert "coda-button--pulse" not in game_env.elements["coda-button"].classList
