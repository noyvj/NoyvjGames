"""Addendum I5: a one-time callout the first time wellbeing crosses into
the "thriving" band (>=70), mirroring the existing net-positive
turning-point pattern (integration_turning_point_message) for a second
explicit milestone. thriving_round itself was already tracked (for the
"thriving_region" achievement) but never surfaced as a message before
this addendum.
"""


def test_thriving_callout_message_none_before_threshold(game_env):
    assert game_env.module.thriving_callout_message(game_env.region) is None


def test_thriving_callout_message_after_crossing_threshold(game_env):
    region = game_env.region
    region.thriving_round = 12
    message = game_env.module.thriving_callout_message(region)
    assert "round 12" in message
    assert "thriving" in message


def test_render_hides_thriving_callout_before_threshold(game_env):
    game_env.module.render()
    assert game_env.elements["thriving-callout-display"].hidden is True


def test_render_shows_thriving_callout_after_threshold(game_env):
    game_env.region.thriving_round = 5
    game_env.module.render()
    el = game_env.elements["thriving-callout-display"]
    assert el.hidden is False
    assert "round 5" in el.innerText


def test_thriving_round_recorded_once_advance_round_crosses_threshold(game_env):
    region = game_env.region
    # Force a state that clears THRIVING_WELLBEING_SCORE (70) on the next
    # advance_round -- pump funds/integration directly rather than
    # grinding out dozens of real rounds.
    region.funds = 2000.0
    region.total_arrivals = 10.0
    region.integrated_population = 10.0
    region.capacity["housing"] = 100.0  # keeps this round's strain at 0
    game_env.advance_round()
    assert region.thriving_round is not None
    assert region.wellbeing_score() >= game_env.module.THRIVING_WELLBEING_SCORE
