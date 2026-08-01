"""Milestone 1: single-run core loop — scheduled events, resilience/growth
investment between them, and damage resolution. No scoring or skill tree
yet.
"""


def test_initial_state(game_env):
    assert game_env.run.event_index == 0
    assert game_env.run.resources == 200.0
    assert game_env.run.resilience_capacity == 0
    assert game_env.run.growth_capacity == 0


def test_next_event_type_starts_with_first_scheduled_event(game_env):
    assert game_env.run.next_event_type() == "flood"


def test_invest_resilience_deducts_cost_and_increments_capacity(game_env):
    game_env.invest_resilience()
    assert game_env.run.resilience_capacity == 1
    assert game_env.run.resources == 200 - 25


def test_invest_growth_deducts_cost_and_increments_capacity(game_env):
    game_env.invest_growth()
    assert game_env.run.growth_capacity == 1
    assert game_env.run.resources == 200 - 20


def test_invest_fails_when_insufficient_resources(game_env):
    game_env.run.resources = 5
    game_env.invest_resilience()
    assert game_env.run.resilience_capacity == 0
    assert game_env.run.resources == 5


def test_resolve_event_applies_damage_and_advances_index(game_env):
    game_env.resolve_event()
    assert game_env.run.event_index == 1
    assert game_env.run.resources == 200 - 40  # flood, no mitigation
    assert game_env.run.damage_taken == 40


def test_resolve_event_applies_growth_income_before_damage(game_env):
    game_env.invest_growth()  # resources = 180, growth_capacity = 1
    game_env.resolve_event()
    # income (+8) then flood damage (-40): 180 + 8 - 40 = 148
    assert game_env.run.resources == 148


def test_resilience_mitigates_event_damage(game_env):
    for _ in range(4):
        game_env.invest_resilience()  # 4 units = 20% mitigation, cost 100
    resources_before = game_env.run.resources
    game_env.resolve_event()
    expected_damage = 40 * (1 - 0.20)
    assert game_env.run.resources == resources_before - expected_damage


def test_mitigation_caps_at_maximum(game_env):
    game_env.run.resilience_capacity = 1000
    assert game_env.run.mitigation_fraction() == 0.85


def test_resources_never_go_negative(game_env):
    game_env.run.resources = 10
    game_env.resolve_event()  # flood damage 40 > 10
    assert game_env.run.resources == 0.0


def test_event_log_records_each_event(game_env):
    game_env.resolve_event()
    game_env.resolve_event()
    assert len(game_env.run.event_log) == 2
    assert game_env.run.event_log[0]["type"] == "flood"
    assert game_env.run.event_log[1]["type"] == "heatwave"


def test_run_is_not_complete_initially(game_env):
    assert game_env.run.is_complete() is False


def test_run_completes_after_all_scheduled_events(game_env):
    for _ in range(5):
        game_env.resolve_event()
    assert game_env.run.is_complete() is True
    assert game_env.run.next_event_type() is None


def test_resolve_event_is_a_noop_after_run_completes(game_env):
    for _ in range(5):
        game_env.resolve_event()
    resources_before = game_env.run.resources
    game_env.resolve_event()
    assert game_env.run.event_index == 5
    assert game_env.run.resources == resources_before


def test_invest_disabled_after_run_completes(game_env):
    for _ in range(5):
        game_env.resolve_event()
    assert game_env.elements["resilience-invest-button"].disabled is True
    assert game_env.elements["growth-invest-button"].disabled is True
    assert game_env.elements["resolve-event-button"].disabled is True


def test_render_shows_progress_and_next_event(game_env):
    assert game_env.elements["progress-display"].innerText == "Event 1 of 5"
    assert "Flood" in game_env.elements["next-event-display"].innerText


def test_render_shows_run_complete_message(game_env):
    for _ in range(5):
        game_env.resolve_event()
    assert game_env.elements["progress-display"].innerText == "Run complete"
