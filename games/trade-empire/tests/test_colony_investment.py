"""J7 -- colony investment: spend credits to push an undeveloped colony
toward Level 2 development (the same progress deliveries build)."""


def test_investing_spends_credits_and_adds_development_progress(game_env):
    game = game_env.module
    game.total_profit = 500
    colony = game.colony_states["aurum"]
    before = colony.cumulative_delivered
    assert game.invest_in_colony("aurum")
    assert game.total_profit == 500 - game.COLONY_INVEST_COST
    assert colony.cumulative_delivered == before + game.COLONY_INVEST_UNITS


def test_cannot_invest_without_enough_credits(game_env):
    game = game_env.module
    game.total_profit = game.COLONY_INVEST_COST - 1
    assert game.can_invest_in_colony("aurum") is False
    assert game.invest_in_colony("aurum") is False
    assert game.total_profit == game.COLONY_INVEST_COST - 1


def test_repeated_investment_develops_the_colony_and_then_stops(game_env):
    game = game_env.module
    game.total_profit = 10_000
    colony = game.colony_states["aurum"]
    needed = int(game.DEVELOPMENT_THRESHOLD // game.COLONY_INVEST_UNITS)
    for _ in range(needed):
        assert game.invest_in_colony("aurum")
    assert colony.is_developed()
    spent = game.total_profit
    assert game.can_invest_in_colony("aurum") is False
    assert game.invest_in_colony("aurum") is False
    assert game.total_profit == spent


def test_locked_system_colonies_cannot_be_invested_in(game_env):
    game = game_env.module
    game.total_profit = 10_000
    assert game.can_invest_in_colony("kepler_a") is False
    assert game.invest_in_colony("kepler_a") is False
    assert game.can_invest_in_colony("not-a-colony") is False


def test_deliveries_still_develop_a_colony_the_same_way(game_env):
    game = game_env.module
    colony = game.colony_states["aurum"]
    colony.deliver(game.DEVELOPMENT_THRESHOLD)
    assert colony.is_developed()
    assert colony.need_satisfaction > game.STARTING_NEED_SATISFACTION or colony.need_satisfaction == 1.0


def test_the_button_invests_and_hides_once_developed(game_env):
    game = game_env.module
    game.total_profit = 10_000
    game.render()
    button = game_env.elements["colony-aurum-invest-button"]
    assert button.hidden is False and button.disabled is False
    assert f"{game.COLONY_INVEST_COST}" in button.innerText
    button.dispatch("click", None)
    assert game.colony_states["aurum"].cumulative_delivered == game.COLONY_INVEST_UNITS
    for _ in range(20):
        button.dispatch("click", None)
    assert game.colony_states["aurum"].is_developed()
    assert button.hidden is True


def test_the_button_is_disabled_when_broke(game_env):
    game = game_env.module
    game.total_profit = 0
    game.render()
    assert game_env.elements["colony-aurum-invest-button"].disabled is True
