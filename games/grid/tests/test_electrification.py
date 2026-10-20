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
