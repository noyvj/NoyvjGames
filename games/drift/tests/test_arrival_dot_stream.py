"""Addendum I16: tie the decorative arrival-dot stream's density/speed
to real arrivals-per-round, previously a fixed seven dots animating at
a fixed speed regardless of state.
"""

import pytest


def test_dot_count_at_minimum_with_zero_arrivals(game_env):
    assert game_env.module.arrival_stream_dot_count(0.0) == 1


def test_dot_count_grows_with_arrivals(game_env):
    per_dot = game_env.module.ARRIVAL_STREAM_ARRIVALS_PER_DOT
    assert game_env.module.arrival_stream_dot_count(per_dot) == 2
    assert game_env.module.arrival_stream_dot_count(per_dot * 2) == 3


def test_dot_count_caps_at_seven(game_env):
    assert (
        game_env.module.arrival_stream_dot_count(10_000.0)
        == game_env.module.ARRIVAL_STREAM_MAX_DOTS
    )


def test_animation_duration_at_max_with_zero_arrivals(game_env):
    assert (
        game_env.module.arrival_stream_animation_duration(0.0)
        == game_env.module.ARRIVAL_STREAM_MAX_DURATION_S
    )


def test_animation_duration_at_min_beyond_reference_level(game_env):
    reference = game_env.module.ARRIVAL_STREAM_DURATION_REFERENCE_ARRIVALS
    assert game_env.module.arrival_stream_animation_duration(reference * 10) == pytest.approx(
        game_env.module.ARRIVAL_STREAM_MIN_DURATION_S
    )


def test_animation_duration_shrinks_as_arrivals_rise(game_env):
    module = game_env.module
    slow = module.arrival_stream_animation_duration(1.0)
    fast = module.arrival_stream_animation_duration(30.0)
    assert fast < slow


def test_render_hides_dots_beyond_current_arrivals_tier(game_env):
    game_env.module.render()
    # Fresh region: BASE_ARRIVALS_PER_ROUND (5.0) -> dot count = 1 + 5//5 = 2.
    assert game_env.elements["arrival-dot-1"].hidden is False
    assert game_env.elements["arrival-dot-2"].hidden is False
    assert game_env.elements["arrival-dot-3"].hidden is True


def test_render_sets_animation_duration_on_every_dot(game_env):
    game_env.module.render()
    for i in range(1, game_env.module.ARRIVAL_STREAM_MAX_DOTS + 1):
        el = game_env.elements[f"arrival-dot-{i}"]
        assert el.style.animationDuration.endswith("s")
