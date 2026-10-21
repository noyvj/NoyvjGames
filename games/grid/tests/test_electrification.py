from grid_rules import SCENARIOS, ELECTRIFICATION_EVENTS


def test_electrified_scenario_data():
    assert SCENARIOS["electrified"]["label"] == "Electrified city"
    assert SCENARIOS["electrified"]["funds"] == 500
    assert SCENARIOS["electrified"]["plants"] == {}
    assert SCENARIOS["electrified"]["electrification"] is True


def test_electrification_events_data():
    rounds = [e["round"] for e in ELECTRIFICATION_EVENTS]
    demands = [e["demand"] for e in ELECTRIFICATION_EVENTS]
    assert rounds == [6, 12, 18, 24]
    assert demands == [12, 18, 20, 25]


def test_apply_electrified_scenario(game_env):
    state = game_env.module.GridState()
    result = state.apply_scenario("electrified")
    assert result is True
    assert state.scenario == "electrified"
    assert state.funds == 500


def _advance_n(state, n):
    for _ in range(n):
        state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)


def test_standard_scenario_after_5_rounds(game_env):
    state = game_env.module.GridState()
    _advance_n(state, 5)
    assert state.round_number == 6
    assert state.demand == 150
    assert state.electrification_notice() is None


def test_electrified_demand_after_5_rounds(game_env):
    state = game_env.module.GridState()
    state.apply_scenario("electrified")
    _advance_n(state, 5)
    assert state.demand == 162


def test_electrification_notice_values(game_env):
    state = game_env.module.GridState()
    state.apply_scenario("electrified")

    assert state.electrification_notice() is None

    _advance_n(state, 2)
    event, away = state.electrification_notice()
    assert event["round"] == 6
    assert away == 3

    _advance_n(state, 3)
    event, away = state.electrification_notice()
    assert away == 0


def test_scenario_button_cycles_to_electrified(game_env):
    btn = game_env.elements["scenario-toggle-button"]
    for _ in range(4):
        btn.dispatch("click", None)
    assert game_env.state.scenario == "electrified"
    assert btn.innerText == "Scenario: Electrified city"


def _electrified_env(game_env):
    for _ in range(4):
        game_env.elements["scenario-toggle-button"].dispatch("click", None)
    assert game_env.state.scenario == "electrified"
    return game_env


def test_notice_is_hidden_at_the_start_of_the_electrified_city(game_env):
    _electrified_env(game_env)
    game_env.module.render()
    assert game_env.elements["electrification-display"].hidden is True


def test_notice_counts_down_to_the_bus_fleet_jump(game_env):
    _electrified_env(game_env)
    for _ in range(2):
        game_env.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    game_env.module.render()
    element = game_env.elements["electrification-display"]
    assert element.hidden is False
    assert element.innerText == (
        "In 3 rounds: Bus fleets go electric (+12 demand). Clean power now covers more than lights."
    )
    for _ in range(2):
        game_env.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    game_env.module.render()
    assert element.innerText.startswith("In 1 round: ")
    game_env.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    game_env.module.render()
    assert element.innerText.startswith("This round: ")


def test_standard_scenario_never_shows_the_notice(game_env):
    for _ in range(4):
        game_env.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    game_env.module.render()
    assert game_env.elements["electrification-display"].hidden is True
