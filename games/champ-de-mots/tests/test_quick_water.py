"""L29 -- "quick water": one question on the most overdue plot, feeding the
headline practice score and the study streak."""


def _watered(state, plot, days_overdue):
    plot.last_reviewed = state.current_day - days_overdue - 1
    plot.next_due = state.current_day - days_overdue
    plot.correct_streak = 1
    plot.interval_days = 1


def test_it_is_a_practice_mode_so_it_counts_toward_the_headline_score(game_env):
    module = game_env.module
    assert "quick" in module.PRACTICE_MODES
    assert set(module.practice_ledger) == set(module.PRACTICE_MODES)


def test_the_session_is_exactly_the_single_most_overdue_plot(game_env):
    module, state = game_env.module, game_env.state
    state.current_day = 30
    _watered(state, state.plots[10], days_overdue=2)
    _watered(state, state.plots[20], days_overdue=9)
    module.start_review(module.QUICK_WATER_MODE)
    assert module.review_queue == [state.plots[20].plot_id]
    assert module.review_question is not None


def test_button_starts_it(game_env):
    module = game_env.module
    game_env.elements["quick-water-button"].dispatch("click", None)
    assert module.review_mode == module.QUICK_WATER_MODE and len(module.review_queue) == 1


def test_a_correct_answer_waters_the_plot_and_scores_a_practice_point(game_env):
    module, state = game_env.module, game_env.state
    state.current_day = 30
    _watered(state, state.plots[5], days_overdue=4)
    plot = state.plots[5]
    before_points = module.practice_score()
    module.start_review(module.QUICK_WATER_MODE)
    q = module.review_question
    assert module.submit_review_answer(q["answer"]) is True
    assert plot.last_reviewed == state.current_day  # a real watering
    assert module.practice_ledger["quick"]["total"] == 1
    assert module.practice_ledger["quick"]["correct"] == 1
    assert module.practice_score() == before_points + 1


def test_a_wrong_answer_still_counts_as_an_attempt_but_scores_nothing(game_env):
    module, state = game_env.module, game_env.state
    state.current_day = 30
    _watered(state, state.plots[5], days_overdue=4)
    module.start_review(module.QUICK_WATER_MODE)
    assert module.submit_review_answer("zzzz-not-an-answer") is False
    assert module.practice_ledger["quick"]["total"] == 1
    assert module.practice_ledger["quick"]["correct"] == 0
    assert module.practice_ledger["quick"]["points"] == 0


def test_it_also_counts_the_study_day(game_env):
    module, state = game_env.module, game_env.state
    state.current_day = 30
    _watered(state, state.plots[5], days_overdue=4)
    module.start_review(module.QUICK_WATER_MODE)
    module.study_today = lambda: "2026-09-26"
    module.submit_review_answer("zzzz")
    assert module.study_days == {"2026-09-26": 1}


def test_nothing_due_shows_the_quick_water_message(game_env):
    module, state = game_env.module, game_env.state
    state.current_day = 10
    for plot in state.plots:
        plot.last_reviewed = 9
        plot.next_due = 50
        plot.correct_streak = 1
    module.start_review(module.QUICK_WATER_MODE)
    empty = game_env.elements["review-empty-message"]
    assert empty.hidden is False and empty.innerText == module.QUICK_WATER_EMPTY_MESSAGE


def test_the_ledger_round_trips_through_a_save(game_env):
    module, state = game_env.module, game_env.state
    state.current_day = 30
    _watered(state, state.plots[5], days_overdue=4)
    module.start_review(module.QUICK_WATER_MODE)
    module.submit_review_answer("zzzz")
    saved = module.get_state()
    module.practice_ledger["quick"]["total"] = 0
    module.load_state(saved)
    assert module.practice_ledger["quick"]["total"] == 1
