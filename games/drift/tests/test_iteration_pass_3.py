"""Iteration Pass 3 (Fun/Teaching Balance): a legible "turning point"
moment for the net-positive integration mechanic. Previously,
integration_contribution() only ever showed up as a background number
inside the funds total and the composite dashboard -- there was no
called-out moment where the player notices the shift from strain to
contribution. This adds a durable milestone: once integrated arrivals'
contributions have paid back the services investment that enabled
their integration, the region has crossed from net strain to net
contribution, and that crossing gets its own callout.
"""

import pytest


def test_cumulative_services_investment_starts_at_zero(game_env):
    assert game_env.region.cumulative_services_investment == 0.0


def test_invest_services_increases_cumulative_services_investment(game_env):
    game_env.region.invest("services")
    assert game_env.region.cumulative_services_investment == pytest.approx(20.0)


def test_invest_housing_does_not_increase_cumulative_services_investment(game_env):
    game_env.region.invest("housing")
    assert game_env.region.cumulative_services_investment == 0.0


def test_not_net_positive_by_default(game_env):
    assert game_env.region.has_crossed_to_net_positive() is False
    assert game_env.region.net_positive_round is None


def test_not_yet_net_positive_before_contribution_catches_up(game_env):
    game_env.region.invest("services")  # cumulative_services_investment = 20
    game_env.region.total_arrivals = 50.0  # plenty of pending, never the cap
    for _ in range(3):
        game_env.advance_round()
    # cumulative contribution after 3 rounds: 0 + 3.6 + 7.2 = 10.8 < 20
    assert game_env.region.has_crossed_to_net_positive() is False


def test_turning_point_reached_after_contribution_covers_investment(game_env):
    game_env.region.invest("services")  # cumulative_services_investment = 20
    game_env.region.total_arrivals = 50.0
    for _ in range(4):
        game_env.advance_round()
    # cumulative contribution after 4 rounds: 0 + 3.6 + 7.2 + 10.8 = 21.6 >= 20
    assert game_env.region.has_crossed_to_net_positive() is True
    assert game_env.region.net_positive_round == 4


def test_turning_point_persists_after_additional_services_investment(game_env):
    """Once reached, the milestone shouldn't flicker off just because a
    later services investment temporarily raises the payback bar --
    it's a durable state, not a live instantaneous ratio."""
    game_env.region.invest("services")
    game_env.region.total_arrivals = 50.0
    for _ in range(4):
        game_env.advance_round()
    assert game_env.region.has_crossed_to_net_positive() is True

    game_env.region.invest("services")  # raises cumulative_services_investment further
    assert game_env.region.has_crossed_to_net_positive() is True
    assert game_env.region.net_positive_round == 4


def test_turning_point_message_none_before_crossing(game_env):
    assert game_env.module.integration_turning_point_message(game_env.region) is None


def test_turning_point_message_after_crossing(game_env):
    game_env.region.invest("services")
    game_env.region.total_arrivals = 50.0
    for _ in range(4):
        game_env.advance_round()
    message = game_env.module.integration_turning_point_message(game_env.region)
    assert message is not None
    assert "4" in message


def test_turning_point_message_is_institutional_not_personal(game_env):
    """Preserve this game's sensitivity framing: institutional/systems
    language (region, capacity, services), not individual dramatization."""
    game_env.region.invest("services")
    game_env.region.total_arrivals = 50.0
    for _ in range(4):
        game_env.advance_round()
    message = game_env.module.integration_turning_point_message(game_env.region)
    assert "region" in message.lower()


def test_turning_point_display_hidden_by_default(game_env):
    game_env.module.render()
    assert game_env.elements["integration-turning-point-display"].hidden is True


def test_turning_point_display_visible_after_crossing(game_env):
    game_env.region.invest("services")
    game_env.region.total_arrivals = 50.0
    for _ in range(4):
        game_env.advance_round()
    display = game_env.elements["integration-turning-point-display"]
    assert display.hidden is False
    assert len(display.innerText) > 0
