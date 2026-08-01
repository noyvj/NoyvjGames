"""Milestone 5: hope-angle payoff — "look how far you've come," comparing
the first completed run to the most recent one, same event schedule.
"""


def test_run_history_starts_empty(game_env):
    assert game_env.run_history == []


def test_completing_a_run_appends_its_score_to_history(game_env):
    for _ in range(5):
        game_env.resolve_event()
    assert game_env.run_history == [game_env.run.run_score()]


def test_run_history_accumulates_across_runs(game_env):
    for _ in range(5):
        game_env.resolve_event()
    game_env.start_new_run()
    for _ in range(5):
        game_env.resolve_event()
    assert len(game_env.run_history) == 2


def test_progress_comparison_is_none_with_fewer_than_two_runs(game_env):
    for _ in range(5):
        game_env.resolve_event()
    assert game_env.module.progress_comparison() is None


def test_progress_comparison_compares_first_and_latest_run(game_env):
    game_env.run_history.extend([10.0, 40.0, 90.0])
    assert game_env.module.progress_comparison() == (10.0, 90.0)


def test_progress_message_with_no_history(game_env):
    message = game_env.module.progress_message(None)
    assert "Play more runs" in message


def test_progress_message_when_improved(game_env):
    message = game_env.module.progress_message((10.0, 90.0))
    assert "how far you've come" in message.lower()
    assert "10" in message
    assert "90" in message


def test_progress_message_when_declined(game_env):
    message = game_env.module.progress_message((90.0, 10.0))
    assert "lower" in message.lower()


def test_progress_message_when_steady(game_env):
    message = game_env.module.progress_message((50.0, 50.0))
    assert "steady" in message.lower()


def test_render_shows_progress_comparison(game_env):
    game_env.run_history.extend([10.0, 90.0])
    game_env.module.render()
    text = game_env.elements["progress-comparison-display"].innerText
    assert "10" in text
    assert "90" in text


def test_skill_investment_produces_a_real_improving_trend(game_env):
    # An end-to-end sanity check of the whole hope-angle loop: play a weak
    # first run, bank the knowledge, unlock a bonus, and confirm a second
    # run (same event schedule) genuinely scores higher.
    for _ in range(5):
        game_env.resolve_event()
    first_score = game_env.run_history[0]

    game_env.skill_tree.add_knowledge(50)  # simulate several runs' worth of currency
    game_env.unlock_skill("community_reserves")
    game_env.unlock_skill("reinforced_infrastructure")
    game_env.unlock_skill("early_warning")
    game_env.start_new_run()
    for _ in range(5):
        game_env.resolve_event()
    latest_score = game_env.run_history[-1]

    assert latest_score > first_score
