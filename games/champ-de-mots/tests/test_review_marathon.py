"""L17 -- the mixed review marathon: a long Review-tab session over due
plots from the whole farm, most overdue first, never-watered plots last."""


def _watered(state, module, plot, days_overdue):
    plot.last_reviewed = state.current_day - days_overdue - 1
    plot.next_due = state.current_day - days_overdue
    plot.correct_streak = 1
    plot.interval_days = 1


def test_marathon_on_a_fresh_farm_takes_never_watered_plots_up_to_the_cap(game_env):
    module = game_env.module
    queue = module.marathon_candidates()
    assert len(queue) == module.MARATHON_COUNT
    assert all(p.last_reviewed is None for p in queue)


def test_marathon_puts_watered_overdue_plots_first_most_overdue_at_the_top(game_env):
    module, state = game_env.module, game_env.state
    state.current_day = 30
    _watered(state, module, state.plots[10], days_overdue=2)
    _watered(state, module, state.plots[20], days_overdue=9)
    _watered(state, module, state.plots[30], days_overdue=5)
    queue = module.marathon_candidates()
    assert [p.plot_id for p in queue[:3]] == [
        state.plots[20].plot_id, state.plots[30].plot_id, state.plots[10].plot_id,
    ]
    assert all(p.last_reviewed is None for p in queue[3:])


def test_marathon_skips_plots_that_are_not_due(game_env):
    module, state = game_env.module, game_env.state
    state.current_day = 10
    future = state.plots[0]
    future.last_reviewed = 9
    future.next_due = 20
    future.correct_streak = 1
    assert future.plot_id not in [p.plot_id for p in module.marathon_candidates()]


def test_marathon_draws_from_every_topic_type_and_row(game_env):
    module, state = game_env.module, game_env.state
    state.current_day = 40
    for plot in state.plots[::20]:
        _watered(state, module, plot, days_overdue=3)
    original_count = module.MARATHON_COUNT
    module.MARATHON_COUNT = 100
    try:
        queue = module.marathon_candidates()
    finally:
        module.MARATHON_COUNT = original_count
    assert len({p.topic_type for p in queue}) >= 3
    assert len({p.sequence for p in queue}) > 5


def test_start_marathon_review_builds_the_session_and_ignores_the_count_input(game_env):
    module, game_env_elements = game_env.module, game_env.elements
    game_env_elements["review-count-input"].value = "3"
    module.start_review(module.MARATHON_MODE)
    assert module.review_mode == module.MARATHON_MODE
    assert len(module.review_queue) == module.MARATHON_COUNT
    assert module.review_question is not None


def test_marathon_button_starts_a_marathon(game_env):
    module = game_env.module
    game_env.elements["review-marathon-button"].dispatch("click", None)
    assert module.review_mode == module.MARATHON_MODE and module.review_queue


def test_a_marathon_with_nothing_due_shows_the_marathon_specific_message(game_env):
    module, state = game_env.module, game_env.state
    state.current_day = 10
    for plot in state.plots:
        plot.last_reviewed = 9
        plot.next_due = 50
        plot.correct_streak = 1
    module.start_review(module.MARATHON_MODE)
    empty = game_env.elements["review-empty-message"]
    assert empty.hidden is False
    assert empty.innerText == module.MARATHON_EMPTY_MESSAGE


def test_grammar_plots_in_a_marathon_get_the_grammar_variant_bias(game_env):
    module, state = game_env.module, game_env.state
    plot = next(p for p in state.plots if p.topic_type == "grammar" and any(
        v in module.GRAMMAR_REVIEW_PREFERRED_VARIANTS for v in module.variants_for(p)))
    variant = module._review_variant_for(plot, module.MARATHON_MODE)
    assert variant in module.GRAMMAR_REVIEW_PREFERRED_VARIANTS
    word_plot = next(p for p in state.plots if p.topic_type == "vocab")
    assert module._review_variant_for(word_plot, module.MARATHON_MODE) is None
