"""L3 -- a weak-spot drill from flagged material, and Review answers that count as watering."""


def test_nothing_flagged_on_a_fresh_farm_gives_a_gentle_empty_state(game_env):
    module = game_env.module
    assert module.weak_spot_candidates() == []
    module.start_review(module.WEAK_SPOT_MODE)
    assert module.review_question is None
    assert game_env.elements["review-empty-message"].hidden is False
    assert "Nothing is flagged" in game_env.elements["review-empty-message"].innerText


def test_weeds_are_included_first(game_env):
    module = game_env.module
    a, b = game_env.state.plots[3], game_env.state.plots[70]
    a.in_weeds = b.in_weeds = True
    picked = [p.plot_id for p in module.weak_spot_candidates()]
    assert picked[:2] == [a.plot_id, b.plot_id]


def test_weakest_touched_topics_contribute_their_shaky_plots(game_env):
    module = game_env.module
    plot = game_env.state.plots[10]
    plot.last_reviewed, plot.stage, plot.ease_factor = 1, module.STAGE_SPROUT, 1.5
    fine = game_env.state.plots[200]
    fine.last_reviewed, fine.stage = 1, module.STAGE_AUTOMATED
    picked = [p.plot_id for p in module.weak_spot_candidates()]
    assert plot.plot_id in picked
    assert fine.plot_id not in picked  # Automated is not shaky


def test_no_duplicates_and_the_session_is_capped(game_env):
    module = game_env.module
    for plot in game_env.state.plots[:80]:
        plot.in_weeds = True
    picked = module.weak_spot_candidates()
    assert len(picked) == module.WEAK_SPOT_SESSION_MAX
    assert len({p.plot_id for p in picked}) == len(picked)


def test_button_starts_a_session_over_only_flagged_plots(game_env):
    module = game_env.module
    flagged = [game_env.state.plots[i] for i in (4, 9, 33)]
    for plot in flagged:
        plot.in_weeds = True
    game_env.elements["review-weakspots-button"].dispatch("click", None)
    assert module.review_mode == module.WEAK_SPOT_MODE
    assert sorted(module.review_queue) == sorted(p.plot_id for p in flagged)
    assert game_env.elements["review-panel"].hidden is False


# --- Review answers count as watering -----------------------------------


def test_the_first_correct_review_answer_of_the_day_is_a_real_watering(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[5]
    assert plot.last_reviewed is None
    assert module.water_from_review(plot) is True
    assert plot.last_reviewed == state.current_day and plot.correct_streak == 1


def test_a_second_review_the_same_day_is_only_a_nudge(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[5]
    module.water_from_review(plot)
    interval, streak = plot.interval_days, plot.correct_streak
    assert module.water_from_review(plot) is False
    assert plot.correct_streak == streak and plot.interval_days > interval


def test_a_new_day_makes_the_next_review_a_watering_again(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[5]
    module.water_from_review(plot)
    state.advance_day(1)
    assert module.water_from_review(plot) is True
    assert plot.correct_streak == 2


def test_wrong_review_answers_still_never_touch_srs(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[5]
    module.start_review("word")
    target = state.plots_by_id[module.review_question["plot_id"]]
    before = (target.stage, target.interval_days, target.last_reviewed, target.correct_streak)
    question = module.review_question
    wrong = next(c for c in question["choices"] if c != question["answer"]) if question["mode"] == "choice" else "zzz"
    module.submit_review_answer(wrong)
    assert before == (target.stage, target.interval_days, target.last_reviewed, target.correct_streak)
    assert plot is not None
