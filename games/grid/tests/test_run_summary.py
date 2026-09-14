"""C5 (on-demand Run Summary panel) and C17 (the closing "grid vs.
business-as-usual" counterfactual). The summary panel is a pure read of
score/funds-breakdown/BAU state already covered by other test files --
these tests focus on the panel's own toggle/render wiring and on the new
BAU counterfactual math and messaging it surfaces.
"""

import pytest

NEVER_TRIGGER = lambda: 0.999999


def test_bau_emissions_starts_at_zero(game_env):
    assert game_env.state.bau_emissions == 0.0


def test_bau_emissions_accumulates_each_round(game_env):
    game_env.build("solar")
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.bau_emissions > 0.0


def test_bau_emissions_tracks_installed_capacity_not_demand(game_env):
    """The counterfactual holds installed capacity constant and only
    swaps the fuel mix -- a player who builds nothing at all gets no BAU
    accumulation either, since there's no capacity for the counterfactual
    to have built as coal instead."""
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.bau_emissions == 0.0

    game_env.build("solar")
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    expected = game_env.state.total_capacity() * game_env.module.BAU_EMISSIONS_FACTOR
    assert game_env.state.bau_emissions == pytest.approx(expected)


def test_emissions_avoided_is_zero_for_an_all_coal_grid(game_env):
    """A grid that only ever builds coal should track ~the same
    trajectory as its own business-as-usual counterfactual -- no
    avoided emissions to show for it."""
    game_env.build("coal")
    for _ in range(3):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.emissions_avoided() == 0.0


def test_emissions_avoided_is_positive_for_a_clean_grid(game_env):
    game_env.build("solar")
    game_env.build("wind")
    for _ in range(3):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.emissions_avoided() > 0.0


def test_business_as_usual_message_before_any_rounds(game_env):
    msg = game_env.module.business_as_usual_message(0.0, 0.0)
    assert "Not enough rounds" in msg


def test_business_as_usual_message_shows_avoided_emissions(game_env):
    msg = game_env.module.business_as_usual_message(50.0, 200.0)
    assert "150" in msg
    assert "avoided" in msg


def test_business_as_usual_message_handles_no_improvement(game_env):
    msg = game_env.module.business_as_usual_message(200.0, 200.0)
    assert "no better than staying all-coal" in msg


def test_summary_panel_hidden_by_default(game_env):
    game_env.module.render()
    assert game_env.elements["summary-panel"].hidden is True


def test_toggling_summary_panel_shows_it(game_env):
    game_env.toggle_summary_panel()
    assert game_env.elements["summary-panel"].hidden is False


def test_toggling_summary_panel_twice_hides_it_again(game_env):
    game_env.toggle_summary_panel()
    game_env.toggle_summary_panel()
    assert game_env.elements["summary-panel"].hidden is True


def test_summary_panel_button_label_reflects_open_state(game_env):
    game_env.toggle_summary_panel()
    assert "Hide" in game_env.elements["summary-toggle-button"].innerText


def test_summary_panel_content_includes_score_and_bau_message(game_env):
    game_env.build("solar")
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.toggle_summary_panel()
    html = game_env.elements["summary-panel"].innerHTML
    assert "sustained clean-grid score" in html
    assert "Funds so far" in html
    assert "business-as-usual" in html


def test_summary_panel_not_rebuilt_while_hidden(game_env):
    """update_summary_panel() should short-circuit while hidden, same as
    the achievements panel does -- render() runs every action, so it
    would be wasted work to rebuild the panel's innerHTML every single
    time when it isn't even visible."""
    game_env.module.render()
    assert game_env.elements["summary-panel"].innerHTML == ""
