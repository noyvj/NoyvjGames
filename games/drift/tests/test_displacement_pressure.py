"""Milestone 2: displacement pressure schedule — background climate
severity rises steadily and largely outside the player's control, and
arrival numbers scale with it. Deterministic and testable: the player
can't reduce arrivals, only prepare capacity ahead of them.
"""

import pytest


def test_background_severity_starts_at_zero(game_env):
    assert game_env.region.background_severity == 0.0


def test_arrivals_this_round_starts_at_base(game_env):
    assert game_env.region.arrivals_this_round() == pytest.approx(5.0)


def test_total_arrivals_zero_before_any_round(game_env):
    assert game_env.region.total_arrivals == 0.0


def test_advance_round_raises_background_severity(game_env):
    game_env.advance_round()
    assert game_env.region.background_severity == pytest.approx(0.5)


def test_advance_round_accumulates_arrivals(game_env):
    game_env.advance_round()
    assert game_env.region.total_arrivals == pytest.approx(5.0)


def test_arrivals_rise_with_severity_across_rounds(game_env):
    game_env.advance_round()  # severity 0 -> 0.5, arrivals this round used 0
    first_round_arrivals = game_env.region.arrivals_log[0]
    game_env.advance_round()  # severity 0.5 -> 1.0
    second_round_arrivals = game_env.region.arrivals_log[1]
    assert second_round_arrivals > first_round_arrivals


def test_arrivals_log_records_each_round(game_env):
    game_env.advance_round()
    game_env.advance_round()
    assert len(game_env.region.arrivals_log) == 2


def test_multiple_rounds_compound_total_arrivals(game_env):
    for _ in range(5):
        game_env.advance_round()
    # arrivals this round each time used the severity *before* it rose
    # that round: 5, 6.5, 8, 9.5, 11 -> sum 40
    assert game_env.region.total_arrivals == pytest.approx(40.0)


def test_investment_does_not_affect_arrivals(game_env):
    game_env.region.invest("housing")
    game_env.region.invest("infrastructure")
    assert game_env.region.arrivals_this_round() == pytest.approx(5.0)


def test_render_shows_arrivals_display(game_env):
    game_env.module.render()
    assert "5" in game_env.elements["arrivals-display"].innerText


def test_render_shows_total_arrivals_display(game_env):
    game_env.advance_round()
    game_env.module.render()
    assert "5" in game_env.elements["total-arrivals-display"].innerText
