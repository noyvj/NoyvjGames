"""The watering rule (2026-10-08): the FIRST correct answer for a plot on an
in-game day, from ANY plot-linked activity, is a full watering; a later correct
answer the same day is a nudge (at most one nudge per plot per day); a wrong
answer in the new flows changes nothing; a stage never goes down; a plot that
was never watered can be watered by any of them."""

import json


def _snapshot(plot):
    return (plot.ease_factor, plot.interval_days, plot.last_reviewed, plot.next_due, plot.correct_streak, plot.stage)


def _answer_on_the_farm(module, plot_id):
    module.open_practice(plot_id)
    return module.submit_answer(module.current_question["answer"])


# --- the rule itself ---------------------------------------------------------------------


def test_first_correct_answer_waters_then_one_nudge_then_nothing(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[3]
    assert _answer_on_the_farm(module, plot.plot_id) is True
    assert plot.stage == module.STAGE_SPROUT and plot.correct_streak == 1 and plot.interval_days == 1
    assert plot.last_watered == state.current_day
    assert module.current_water_kind == module.WATER_FULL

    stage, streak, ease, interval = plot.stage, plot.correct_streak, plot.ease_factor, plot.interval_days
    _answer_on_the_farm(module, plot.plot_id)  # same day: a nudge
    assert module.current_water_kind == module.WATER_NUDGE
    assert (plot.stage, plot.correct_streak, plot.ease_factor) == (stage, streak, ease)
    assert plot.interval_days == interval + module.REVIEW_NUDGE_DAYS

    after_nudge = _snapshot(plot)
    _answer_on_the_farm(module, plot.plot_id)  # a third one: nothing more to add
    assert module.current_water_kind is None
    assert _snapshot(plot) == after_nudge

    state.advance_day(plot.interval_days)
    _answer_on_the_farm(module, plot.plot_id)  # a new day waters again
    assert module.current_water_kind == module.WATER_FULL
    assert plot.correct_streak == 2


def test_repeating_a_plot_on_the_farm_no_longer_stacks_growth_in_one_day(game_env):
    """Before 2026-10-08 four correct answers in a row on the farm took a plot
    from Seed to Blooming in a single day; now it takes four days."""
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    for _ in range(4):
        _answer_on_the_farm(module, plot.plot_id)
    assert plot.correct_streak == 1 and plot.stage == module.STAGE_SPROUT


def test_a_wrong_answer_on_the_farm_still_reschedules_but_never_lowers_the_stage(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[5]
    _answer_on_the_farm(module, plot.plot_id)
    state.advance_day(plot.interval_days)
    _answer_on_the_farm(module, plot.plot_id)
    assert plot.correct_streak == 2
    stage = plot.stage
    state.advance_day(plot.interval_days)
    module.open_practice(plot.plot_id)
    question = module.current_question
    wrong = next((c for c in question["choices"] if c != question["answer"]), "zzzz") if question["mode"] == "choice" else "zzzz"
    module.submit_answer(wrong)
    assert plot.correct_streak == 0 and plot.interval_days == module.RESET_INTERVAL_DAYS
    assert plot.stage == stage and plot.last_watered != state.current_day


def test_a_wrong_answer_then_a_right_one_the_same_day_still_waters(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[7]
    module.open_practice(plot.plot_id)
    question = module.current_question
    wrong = next((c for c in question["choices"] if c != question["answer"]), "zzzz") if question["mode"] == "choice" else "zzzz"
    module.submit_answer(wrong)
    assert plot.last_watered is None
    _answer_on_the_farm(module, plot.plot_id)
    assert module.current_water_kind == module.WATER_FULL and plot.stage == module.STAGE_SPROUT


# --- the same rule everywhere ---------------------------------------------------------------


def test_every_surface_waters_a_never_watered_plot_the_first_time(game_env):
    module, state = game_env.module, game_env.state
    for index, surface in enumerate(
        ("review", "proficiency", "blitz", "racer", "sprint", "boutique", "cafe", "pairs", "gaps", "listenpick", "wordorder")
    ):
        plot = state.plots[10 + index]
        assert plot.stage == module.STAGE_SEED
        assert module.credit_correct(plot, surface) == module.WATER_FULL, surface
        assert plot.stage == module.STAGE_SPROUT
        assert module.growth_credit[surface]["full"] == 1


def test_watering_on_the_farm_means_a_later_review_answer_the_same_day_only_nudges(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[12]
    _answer_on_the_farm(module, plot.plot_id)
    assert module.credit_review_plot(plot, "review") == module.WATER_NUDGE
    assert plot.correct_streak == 1  # no second rung of the ladder
    assert module.growth_credit["review"] == {"full": 0, "nudge": 1}


def test_a_game_watering_blocks_a_second_watering_from_review_the_same_day(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[13]
    assert module.credit_game_plot(plot, "blitz") == module.WATER_FULL
    assert module.credit_review_plot(plot, "review") == module.WATER_NUDGE
    state.advance_day(1)
    assert module.credit_review_plot(plot, "review") == module.WATER_FULL


def test_water_from_review_keeps_its_true_false_contract(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[14]
    assert module.water_from_review(plot) is True
    assert module.water_from_review(plot) is False


def test_a_correct_answer_clears_the_weeds(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[15]
    plot.in_weeds = True
    plot.fail_run = 3
    module.credit_correct(plot, "review")
    assert plot.in_weeds is False and plot.fail_run == 0


def test_stage_never_goes_down_under_any_amount_of_watering_or_nudging(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[16]
    best = 0
    for _ in range(12):
        module.credit_correct(plot, "review")
        module.credit_correct(plot, "blitz")
        state.advance_day(max(1, plot.interval_days))
        rank = module.STAGE_RANK[plot.stage]
        assert rank >= best
        best = rank


# --- the visible numbers --------------------------------------------------------------------


def test_credit_line_says_watered_n_plots_nudged_m(game_env):
    module, state = game_env.module, game_env.state
    first, second = state.plots[20], state.plots[21]
    module.water_plot(second)  # watered earlier in the day by something else
    module.credit_correct(first, "review")
    module.credit_correct(second, "review")  # only a nudge
    module.credit_correct(first, "review")  # the same plot again: counted once
    assert module.growth_credit_text("review") == "Plot growth credited: watered 1 plot, nudged 1."
    module.reset_growth_credit("review")
    assert module.growth_credit_text("review") == "Plot growth credited: none this session."
    third = state.plots[24]
    module.water_plot(third)
    module.credit_correct(third, "review")
    assert module.growth_credit_text("review") == "Plot growth credited: nudged 1 plot."
    module.reset_growth_credit("review")
    module.credit_correct(state.plots[22], "review")
    module.credit_correct(state.plots[23], "review")
    assert module.growth_credit_text("review") == "Plot growth credited: watered 2 plots."


def test_the_farm_says_what_a_correct_answer_just_did(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[30]
    _answer_on_the_farm(module, plot.plot_id)
    note = game_env.elements["practice-water-note"]
    assert not note.hidden and note.innerText.startswith("Watered:") and "Sprout" in note.innerText
    _answer_on_the_farm(module, plot.plot_id)
    note = game_env.elements["practice-water-note"]
    assert note.innerText.startswith("Nudged:")


def test_the_today_line_counts_distinct_plots(game_env):
    module, state = game_env.module, game_env.state
    assert module.water_today_text() == "Nothing watered yet today."
    module.water_plot(state.plots[1])
    module.water_plot(state.plots[1])  # a nudge
    module.water_plot(state.plots[2])
    assert module.water_today_text() == "Today: watered 2 plots, nudged 1."
    state.advance_day(1)
    assert module.water_today_text() == "Nothing watered yet today."


def test_review_shows_what_each_correct_answer_did(game_env):
    module, state = game_env.module, game_env.state
    module.start_review("word")
    question = module.review_question
    plot = state.plots_by_id[question["plot_id"]]
    module.submit_review_answer(question["answer"])
    note = game_env.elements["review-water-note"]
    assert not note.hidden and note.innerText.startswith("Watered:")
    assert plot.last_watered == state.current_day


# --- saving ---------------------------------------------------------------------------------


def test_last_watered_is_saved_and_survives_a_round_trip(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[40]
    module.water_plot(plot)
    saved = json.loads(json.dumps(module.get_state()))
    assert saved["plots"][plot.plot_id]["last_watered"] == state.current_day
    state.advance_day(3)
    module.load_state(saved)
    assert state.plots_by_id[plot.plot_id].last_watered == 0
    assert module.get_state() == saved


def test_a_save_from_before_the_rule_loads_with_no_watering_date(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[41]
    old = {
        "version": 1,
        "current_day": 4,
        "plots": {plot.plot_id: {
            "ease_factor": 2.6, "interval_days": 1, "last_reviewed": 4, "next_due": 5,
            "correct_streak": 1, "stage": "sprout", "in_weeds": False,
        }},
    }
    assert module.load_state(old) is True
    assert state.plots_by_id[plot.plot_id].last_watered is None
    for junk in (True, -3, "4", 2.5):
        old["plots"][plot.plot_id]["last_watered"] = junk
        module.load_state(old)
        assert state.plots_by_id[plot.plot_id].last_watered is None
    old["plots"][plot.plot_id]["last_watered"] = 4
    module.load_state(old)
    assert state.plots_by_id[plot.plot_id].last_watered == 4


def test_an_untouched_farm_still_saves_almost_nothing(game_env):
    assert len(json.dumps(game_env.module.get_state())) < 250


def test_slip_forgiveness_leaves_the_watering_date_alone(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[42]
    module.water_plot(plot)
    state.advance_day(1)
    record = module._plot_record(plot)
    assert record["last_watered"] == 0
    module._restore_plot(plot, record)
    assert plot.last_watered == 0
