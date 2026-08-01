"""Milestone 2: run scoring and skill-tree currency generation. The
knowledge-points floor of 1 is the hope-angle mechanic — no run is ever
wasted, even a bad one.
"""


def test_run_score_equals_current_resources(game_env):
    game_env.run.resources = 123.0
    assert game_env.run.run_score() == 123.0


def test_higher_resilience_leads_to_higher_final_score(game_env):
    # Set resilience directly (rather than paying its resource cost) so
    # this isolates the mitigation effect on score from the investment cost.
    game_env.run.resilience_capacity = 10
    for _ in range(5):
        game_env.run.resolve_next_event()
    good_score = game_env.run.run_score()

    bad_run = game_env.module.RunState()
    for _ in range(5):
        bad_run.resolve_next_event()
    bad_score = bad_run.run_score()

    assert good_score > bad_score


def test_knowledge_points_floor_at_one_even_with_zero_resources(game_env):
    game_env.run.resources = 0.0
    assert game_env.run.knowledge_points_earned() == 1


def test_knowledge_points_scale_with_score(game_env):
    game_env.run.resources = 100.0
    assert game_env.run.knowledge_points_earned() == 5  # 100 / 20


def test_knowledge_points_round_to_nearest(game_env):
    game_env.run.resources = 95.0
    assert game_env.run.knowledge_points_earned() == round(95 / 20)


def test_render_shows_no_summary_mid_run(game_env):
    assert game_env.elements["run-summary-display"].innerText == ""


def test_render_shows_summary_after_run_completes(game_env):
    for _ in range(5):
        game_env.resolve_event()
    text = game_env.elements["run-summary-display"].innerText
    assert "Score" in text
    assert "resilience knowledge point" in text


def test_render_summary_pluralizes_correctly(game_env):
    game_env.run.resources = 20.0  # exactly 1 knowledge point
    game_env.run.event_index = len(game_env.module.EVENT_SCHEDULE)  # mark run complete directly
    game_env.module.render()
    text = game_env.elements["run-summary-display"].innerText
    assert "1 resilience knowledge point." in text
