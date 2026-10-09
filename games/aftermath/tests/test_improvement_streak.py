"""GE-22: the run-improvement streak."""


def test_record_flags_and_streak_basics(game_env):
    m = game_env.module
    assert m.record_flags([]) == []
    assert m.record_flags([10, 20, 15, 30, 40]) == [False, True, False, True, True]
    assert m.improvement_streak([]) == 0
    assert m.improvement_streak([10]) == 0
    assert m.improvement_streak([10, 20]) == 1
    assert m.improvement_streak([10, 20, 15, 30, 40]) == 2
    assert m.improvement_streak([10, 20, 30, 40, 50]) == 4
    assert m.improvement_streak([50, 20, 30, 40]) == 0
    assert m.improvement_streak([10, 20, 20]) == 0  # a tie is not an improvement


def test_text_appears_from_two_in_a_row_only(game_env):
    m = game_env.module
    assert m.streak_text([10, 20]) == ""
    text = m.streak_text([10, 20, 30])
    assert text.startswith("\U0001F525") and "2 runs in a row" in text


def test_display_follows_the_run_history(game_env):
    m = game_env.module
    el = game_env.elements["improvement-streak-display"]
    m.render()
    assert el.hidden is True
    m.run_history[:] = [10.0, 20.0, 30.0, 45.0]
    m.render()
    assert el.hidden is False and "3 runs in a row" in el.innerText
    m.run_history[:] = [10.0, 20.0, 5.0]
    m.render()
    assert el.hidden is True


def test_past_run_cards_in_the_streak_get_a_flame_and_a_glow_class(game_env):
    m = game_env.module
    log = [{"type": "flood", "damage": 5.0, "severity": 1.0}]
    scores = [10.0, 5.0, 20.0, 30.0]
    m.run_log_history[:] = [
        {"run_number": i + 1, "score": sc, "resilience_capacity": 0, "growth_capacity": 0,
         "knowledge_earned": 1, "damage_taken": 5.0, "event_log": log}
        for i, sc in enumerate(scores)
    ]
    game_env.toggle_past_runs()
    cards = game_env.elements["past-runs-list"].children  # newest first: runs 4, 3, 2, 1
    assert "past-run-card--streak" in cards[0].className and "past-run-card--streak" in cards[1].className
    assert "past-run-card--streak" not in cards[2].className and "past-run-card--streak" not in cards[3].className
    assert "\U0001F525" in cards[0].children[0].innerText and "\U0001F525" not in cards[3].children[0].innerText
