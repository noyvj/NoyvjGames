"""Progressive question format (2026-10-08): a plot that has never been watered
always starts with multiple choice; typed answers appear more and more as the
plot's stage, correct streak and ease factor grow; deterministic; an "Always
multiple choice" setting switches it off."""


import pytest


@pytest.fixture
def game_env(progressive_env):
    """This file tests the real schedule, so it uses the unpatched module."""
    return progressive_env


def _grown(module, plot, stage, streak=None, ease=None):
    plot.stage = stage
    plot.last_reviewed = 3
    plot.correct_streak = {module.STAGE_SPROUT: 1, module.STAGE_BUDDING: 2, module.STAGE_BLOOMING: 3, module.STAGE_AUTOMATED: 5}[stage] if streak is None else streak
    if ease is not None:
        plot.ease_factor = ease
    return plot


def _vocab_plot(module, state, index=0):
    typed_capable = [
        p for p in state.plots
        if p.topic_type == "vocab" and module.V_FR_EN_TYPED in module.variants_for(p) and module.V_FR_EN_CHOICE in module.variants_for(p)
    ]
    return typed_capable[index]


# --- the schedule -----------------------------------------------------------------------


def test_a_plot_that_was_never_watered_is_always_multiple_choice(game_env):
    module, state = game_env.module, game_env.state
    rng = module.random.Random(1)
    for plot in state.plots[::7]:
        assert module.question_format_percent(plot) == 0
        assert not module.wants_typed(plot)
        for _ in range(3):
            assert module.generate_question(plot, rng)["mode"] == "choice"


def test_a_plot_answered_only_wrongly_is_still_a_seed_and_stays_multiple_choice(game_env):
    module, state = game_env.module, game_env.state
    plot = _vocab_plot(module, state)
    state.review(plot.plot_id, False)
    assert plot.stage == module.STAGE_SEED and plot.last_reviewed is not None
    assert module.question_format_percent(plot) == 0


def test_the_typed_share_rises_with_the_stage(game_env):
    module, state = game_env.module, game_env.state
    plot = _vocab_plot(module, state)
    shares = []
    for stage in module.STAGE_ORDER:
        if stage == module.STAGE_SEED:
            shares.append(module.question_format_percent(plot))
            continue
        _grown(module, plot, stage, ease=module.DEFAULT_EASE)
        shares.append(module.question_format_percent(plot))
    assert shares[0] == 0
    assert shares == sorted(shares) and len(set(shares)) == len(shares)
    assert shares[-1] <= module.FORMAT_MAX_PERCENT
    assert 15 <= shares[1] <= 35 and shares[-1] >= 85  # sprout mostly choice, mastered mostly typed


def test_streak_and_ease_move_the_share_and_a_miss_leans_back_toward_choice(game_env):
    module, state = game_env.module, game_env.state
    plot = _vocab_plot(module, state)
    _grown(module, plot, module.STAGE_BUDDING, streak=2, ease=module.DEFAULT_EASE)
    base = module.question_format_percent(plot)
    plot.correct_streak = 6
    assert module.question_format_percent(plot) > base
    plot.correct_streak = 2
    plot.ease_factor = 3.0
    assert module.question_format_percent(plot) > base
    plot.ease_factor = 1.3
    assert module.question_format_percent(plot) < base
    plot.ease_factor = module.DEFAULT_EASE
    plot.correct_streak = 0  # just missed
    assert module.question_format_percent(plot) < base


def test_the_share_is_capped_below_one_hundred_percent(game_env):
    module, state = game_env.module, game_env.state
    plot = _grown(module, _vocab_plot(module, state), module.STAGE_AUTOMATED, streak=40, ease=3.0)
    assert module.question_format_percent(plot) == module.FORMAT_MAX_PERCENT


# --- deterministic and observable --------------------------------------------------------------


def test_the_choice_is_a_fixed_function_of_the_plots_state(game_env):
    module, state = game_env.module, game_env.state
    plot = _grown(module, _vocab_plot(module, state), module.STAGE_BLOOMING)
    first = [module.wants_typed(plot) for _ in range(5)]
    assert len(set(first)) == 1
    other = _vocab_plot(module, state, 1)
    _grown(module, other, module.STAGE_BLOOMING)
    # Different plots / states land on different sides of the same share.
    results = set()
    for streak in range(1, 30):
        plot.correct_streak = streak
        results.add(module.wants_typed(plot))
    assert results == {True, False} or module.question_format_percent(plot) >= 70


def test_over_many_grown_plots_the_observed_typed_share_follows_the_schedule(game_env):
    module, state = game_env.module, game_env.state
    candidates = [
        p for p in state.plots
        if p.topic_type in ("vocab", "phrase") and module.V_FR_EN_TYPED in module.variants_for(p) and module.V_EN_FR_TYPED in module.variants_for(p)
    ][:150]
    observed = {}
    for stage in (module.STAGE_SPROUT, module.STAGE_BUDDING, module.STAGE_BLOOMING, module.STAGE_AUTOMATED):
        typed = 0
        for index, plot in enumerate(candidates):
            _grown(module, plot, stage, ease=module.DEFAULT_EASE)
            plot.interval_days = index  # varies the hash input like real play does
            question = module.generate_question(plot, module.random.Random(index))
            typed += question["mode"] == "typed"
        observed[stage] = typed / len(candidates)
    ordered = [observed[s] for s in (module.STAGE_SPROUT, module.STAGE_BUDDING, module.STAGE_BLOOMING, module.STAGE_AUTOMATED)]
    assert ordered == sorted(ordered)
    assert observed[module.STAGE_SPROUT] < 0.4 and observed[module.STAGE_AUTOMATED] > 0.75


def test_a_choice_question_for_a_grown_plot_becomes_its_typed_twin(game_env):
    module, state = game_env.module, game_env.state
    plot = _grown(module, _vocab_plot(module, state), module.STAGE_AUTOMATED, streak=40, ease=3.0)
    module.wants_typed = lambda p: True
    question = module.generate_question(plot, module.random.Random(0), variant=module.V_FR_EN_CHOICE)
    assert question["variant"] == module.V_FR_EN_TYPED and question["mode"] == "typed"


def test_format_argument_forces_choice_or_typed(game_env):
    module, state = game_env.module, game_env.state
    plot = _grown(module, _vocab_plot(module, state), module.STAGE_AUTOMATED, streak=40, ease=3.0)
    for seed in range(10):
        assert module.generate_question(plot, module.random.Random(seed), format="choice")["mode"] == "choice"
        assert module.generate_question(plot, module.random.Random(seed), format="typed")["mode"] == "typed"
    seed_plot = state.plots[200]
    assert module.generate_question(seed_plot, module.random.Random(0), format="typed")["mode"] in ("typed", "choice")


def test_a_fill_the_gap_question_can_be_typed_and_is_graded_as_typed(game_env):
    module, state = game_env.module, game_env.state
    grammar = next(
        p for p in state.plots
        if p.topic_type == "grammar" and module.V_CONJUGATION_SWAP in module.variants_for(p)
    )
    question = module.generate_question(grammar, module.random.Random(3), variant=module.V_CONJUGATION_SWAP, format="typed")
    assert question["mode"] == "typed" and question["choices"] == []
    assert question["instruction"] == "Type the form that goes with this pronoun."
    assert module.check_question_answer(question, question["answer"]) is True
    assert module.check_question_answer(question, "definitely wrong") is False
    # And through the farm: a typed gap is graded like any typed answer.
    module.wants_typed = lambda p: True
    module.open_practice(grammar.plot_id, variant=module.V_CONJUGATION_SWAP)
    assert module.current_question["mode"] == "typed"
    assert module.submit_answer(module.current_question["answer"]) is True
    assert grammar.stage == module.STAGE_SPROUT


def test_typed_blank_instructions_come_from_the_instruction_table(game_env):
    module = game_env.module
    assert "blank_word_typed" in module.INSTRUCTIONS and "conjugation_swap_typed" in module.INSTRUCTIONS


# --- the setting ------------------------------------------------------------------------------


def test_always_multiple_choice_switches_the_schedule_off(game_env):
    module, state = game_env.module, game_env.state
    plot = _grown(module, _vocab_plot(module, state), module.STAGE_AUTOMATED, streak=40, ease=3.0)
    assert module.question_format_percent(plot) > 0
    stored = {}
    module.pref_set = lambda key, value: stored.__setitem__(key, value)
    game_env.elements["always-mc-checkbox"].dispatch("click", None)
    assert module.ALWAYS_MULTIPLE_CHOICE is True and game_env.elements["always-mc-checkbox"].checked is True
    assert stored == {module.PREF_ALWAYS_MC: "1"}
    assert module.question_format_percent(plot) == 0
    for seed in range(20):
        assert module.generate_question(plot, module.random.Random(seed))["mode"] == "choice"
    game_env.elements["always-mc-checkbox"].dispatch("click", None)
    assert module.ALWAYS_MULTIPLE_CHOICE is False and stored[module.PREF_ALWAYS_MC] == "0"


def test_settings_panel_explains_the_schedule_in_words(game_env):
    module = game_env.module
    text = game_env.elements["format-schedule-note"].innerText
    assert "Seed" in text and "multiple choice only" in text and "typed" in text
    assert text == " ".join(module.format_schedule_lines())


def test_minigames_use_the_same_schedule_and_can_take_a_typed_answer(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    module.wants_typed = lambda p: True
    # Blitz: a typed translation is graded by the farm's grader
    mg.start_blitz()
    for _ in range(40):
        if mg.blitz_question["mode"] == "typed":
            break
        mg._roll_blitz_question()
    assert mg.blitz_question["mode"] == "typed"
    module.render()
    assert game_env.elements["blitz-typed-input"] is not None
    plot = state.plots_by_id[mg.blitz_question["plot_id"]]
    assert mg.submit_blitz_choice(mg.blitz_question["answer"]) is True
    assert plot.stage == module.STAGE_SPROUT
