"""Iteration Pass 3 (Fun/Teaching Balance), from
`climate-games-fun-teaching-balance.md`.

Risk: Thaw was already the most doom-prone game in the hub (Pass 1). This
pass adds the research-backed version of that concern — a feedback-loop
mechanic without a legible efficacy payoff risks "fuelling fear" rather
than "strengthening trust" (Klim:S21). Pre-fix, investing in preserve/
monitor silently incremented feedback_dampening_fraction() with zero
perceptible effect on anything else until melt actually started, which
could be many rounds away (or never, in a short session).

Fix: an immediate, visible positive signal the moment the intervention
lever is used — a one-tick "dampening-flash" cue plus an explicit
intervention_feedback_message() that's true (and reassuring) from the
very first preserve/monitor investment, not just once melt begins.

Note: game_env.invest(category) dispatches the button click, which (via
_make_invest_handler) calls region.invest() and render() in the same
step — that render call would itself consume the one-tick
just_invested_intervention flag before a test could inspect the
pre-render state. So flag-level assertions call region.invest()
directly, bypassing the auto-render, matching the pattern already used
in test_iteration_pass.py for just_started_melting.
"""


def test_just_invested_intervention_false_initially(game_env):
    assert game_env.region.just_invested_intervention is False


def test_preserve_investment_sets_the_flag(game_env):
    game_env.region.invest("preserve")
    assert game_env.region.just_invested_intervention is True


def test_monitor_investment_sets_the_flag(game_env):
    game_env.region.invest("monitor")
    assert game_env.region.just_invested_intervention is True


def test_output_investment_does_not_set_the_flag(game_env):
    # Output isn't the intervention lever — only preserve/monitor should
    # trigger the immediate-feedback cue.
    game_env.region.invest("output")
    assert game_env.region.just_invested_intervention is False


def test_failed_investment_does_not_set_the_flag(game_env):
    game_env.region.funds = 5
    game_env.region.invest("preserve")
    assert game_env.region.just_invested_intervention is False


def test_flag_cleared_by_render_and_stays_false(game_env):
    game_env.region.invest("preserve")
    assert game_env.region.just_invested_intervention is True

    game_env.module.render()  # consumes the one-tick flag, as the real app does
    assert game_env.region.just_invested_intervention is False

    game_env.module.render()  # a second render shouldn't re-trigger
    assert game_env.region.just_invested_intervention is False


def test_render_applies_dampening_flash_class_once(game_env):
    game_env.invest("preserve")  # dispatches click -> invest() + render() together
    assert game_env.elements["dampening-display"].className == "status-line dampening-flash"

    game_env.module.render()  # a second render shouldn't re-flash
    assert game_env.elements["dampening-display"].className == "status-line"


def test_render_dampening_class_empty_of_flash_before_any_investment(game_env):
    game_env.module.render()
    assert game_env.elements["dampening-display"].className == "status-line"


def test_advance_round_does_not_trigger_the_flash(game_env):
    # The cue is specifically for the intervention lever being used, not
    # for every render — a plain round advance shouldn't flash it.
    game_env.advance_round()
    assert "dampening-flash" not in game_env.elements["dampening-display"].className


def test_intervention_feedback_message_before_any_investment(game_env):
    msg = game_env.region.intervention_feedback_message()
    assert "no preservation or monitoring" in msg.lower()


def test_intervention_feedback_message_after_preserve_investment(game_env):
    game_env.region.invest("preserve")
    msg = game_env.region.intervention_feedback_message()
    assert "8%" in msg


def test_intervention_feedback_message_reflects_stacked_investment(game_env):
    game_env.region.invest("preserve")
    game_env.region.invest("monitor")
    msg = game_env.region.intervention_feedback_message()
    assert "12%" in msg


def test_intervention_feedback_message_is_meaningful_before_melt_starts(game_env):
    # The core Pass 3 fix: unlike trajectory_message()/acceleration_message(),
    # which stay generic until melt actually begins, this message is true
    # and specific the instant an investment is made.
    game_env.region.invest("preserve")
    assert game_env.region.temperature < 10.0  # still well below MELT_THRESHOLD
    assert game_env.region.is_melting() is False
    msg = game_env.region.intervention_feedback_message()
    assert "8%" in msg
    assert "now" in msg.lower()


def test_render_shows_intervention_feedback_message(game_env):
    game_env.invest("preserve")
    assert "8%" in game_env.elements["intervention-feedback-display"].innerText


def test_render_shows_default_intervention_feedback_message_before_investment(game_env):
    game_env.module.render()
    text = game_env.elements["intervention-feedback-display"].innerText.lower()
    assert "no preservation or monitoring" in text
