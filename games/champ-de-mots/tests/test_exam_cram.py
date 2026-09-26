"""L25 -- exam cram: a dense session over a chosen range of weeks."""


def _select(game_env, name, value):
    game_env.elements[name].value = str(value)


def test_selects_list_every_week_and_default_to_the_whole_course(game_env):
    module = game_env.module
    rows = game_env.state.rows
    frm, to = game_env.elements["review-cram-from-select"], game_env.elements["review-cram-to-select"]
    assert len(frm.children) == len(rows) == len(to.children)
    assert frm.value == str(rows[0].sequence) and to.value == str(rows[-1].sequence)
    assert frm.children[0].innerText.startswith("Week 1")
    assert module.CRAM_MODE == "cram"


def test_cram_range_is_ordered_and_clamped(game_env):
    module = game_env.module
    last = game_env.state.rows[-1].sequence
    assert module.cram_range(5, 3) == (3, 5)
    assert module.cram_range(-10, 9999) == (1, last)
    assert module.cram_range("x", None) == (1, last)


def test_candidates_stay_inside_the_chosen_weeks_and_are_capped(game_env):
    module = game_env.module
    picked = module.cram_candidates(4, 6)
    assert picked and all(4 <= p.sequence <= 6 for p in picked)
    assert len(picked) <= module.CRAM_SESSION_MAX
    everything = module.cram_candidates(1, game_env.state.rows[-1].sequence)
    assert len(everything) == module.CRAM_SESSION_MAX


def test_weakest_material_is_chosen_first_when_the_range_is_bigger_than_the_cap(game_env):
    module = game_env.module
    strong = [p for p in game_env.state.plots if p.sequence <= 3]
    for plot in strong:
        plot.stage = module.STAGE_AUTOMATED
    picked = module.cram_candidates(1, 3)
    assert len(strong) > module.CRAM_SESSION_MAX
    # Every plot is automated in that range, so all picks are; now weaken a few.
    weak_ids = {p.plot_id for p in strong[:5]}
    for plot in strong[:5]:
        plot.stage = module.STAGE_SEED
    picked_ids = {p.plot_id for p in module.cram_candidates(1, 3)}
    assert weak_ids <= picked_ids
    assert picked  # sanity


def test_button_starts_a_review_session_over_the_range(game_env):
    module = game_env.module
    _select(game_env, "review-cram-from-select", 2)
    _select(game_env, "review-cram-to-select", 3)
    game_env.elements["review-cram-button"].dispatch("click", None)
    assert module.review_mode == module.CRAM_MODE
    assert module.review_queue
    assert all(2 <= game_env.state.plots_by_id[i].sequence <= 3 for i in module.review_queue)
    assert module.review_question is not None
    assert game_env.elements["review-panel"].hidden is False


def test_a_reversed_range_still_works(game_env):
    module = game_env.module
    _select(game_env, "review-cram-from-select", 5)
    _select(game_env, "review-cram-to-select", 2)
    game_env.elements["review-cram-button"].dispatch("click", None)
    assert all(2 <= game_env.state.plots_by_id[i].sequence <= 5 for i in module.review_queue)


def test_cram_answers_follow_the_review_watering_rule(game_env):
    """A cram answer is an ordinary Review answer: the first correct one for a
    plot that day counts as its watering (L3); it never grows a plot twice."""
    module = game_env.module
    game_env.elements["review-cram-button"].dispatch("click", None)
    plot = game_env.state.plots_by_id[module.review_question["plot_id"]]
    assert plot.last_reviewed is None
    module.submit_review_answer(module.review_question["answer"])
    assert plot.last_reviewed == game_env.state.current_day and plot.correct_streak == 1


def test_ties_sample_across_the_whole_range_not_just_its_first_weeks(game_env):
    module = game_env.module
    last = game_env.state.rows[-1].sequence
    weeks = {p.sequence for p in module.cram_candidates(1, last)}
    assert len(weeks) > 5  # a fresh all-Seed farm must not fill the cap from weeks 1-3
