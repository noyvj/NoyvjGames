"""Milestone 4: the static farm grid UI (design doc §3 and §8).

Rows are sequence numbers 1-23 running continuously across both courses with
nothing but a chapter label marking the join, plots carry a sprite per growth
stage, and overdue plots wilt. Static and screenshot-friendly — no animation,
and nowhere in the interface is there a failure state.
"""


def cell(game_env, plot_id):
    return game_env.elements[f"plot-{plot_id}"]


def open_plot(game_env, plot_id):
    cell(game_env, plot_id).dispatch("click", None)


def answer(game_env, text):
    game_env.elements["practice-answer-input"].value = text
    game_env.elements["practice-submit-button"].dispatch("click", None)


def answer_current_correctly(game_env):
    question = game_env.module.current_question
    if question["mode"] == "choice":
        index = question["choices"].index(question["answer"])
        game_env.elements[f"practice-choice-{index}"].dispatch("click", None)
    else:
        answer(game_env, question["answer"])


def answer_current_incorrectly(game_env):
    question = game_env.module.current_question
    if question["mode"] == "choice":
        index = next(
            i for i, c in enumerate(question["choices"]) if c != question["answer"]
        )
        game_env.elements[f"practice-choice-{index}"].dispatch("click", None)
    else:
        answer(game_env, "definitely not the answer at all")


# --- the grid --------------------------------------------------------------


def test_farm_renders_one_row_per_sequence_number(game_env):
    farm = game_env.elements["farm"]
    assert len(farm.children) == 23
    for index, row in enumerate(game_env.state.rows):
        assert game_env.elements[f"row-{row.sequence}"] is farm.children[index]


def test_rows_are_labelled_by_sequence_course_and_week(game_env):
    label = game_env.elements["row-label-1"].innerText
    assert "1" in label and "FREN151" in label and "wk 1" in label

    later = game_env.elements["row-label-13"].innerText
    assert "FREN152" in later and "wk 3" in later


def test_the_only_marker_at_the_course_boundary_is_the_chapter_label(game_env):
    """§4: FREN151 flows straight into FREN152 with no season break — row 12
    must look like every other row apart from what chapter it names."""
    eleven = game_env.elements["row-11"]
    twelve = game_env.elements["row-12"]
    assert eleven.className == twelve.className
    assert "Bridge" in game_env.elements["row-chapter-12"].innerText
    assert "Ch. 4" in game_env.elements["row-chapter-11"].innerText


def test_every_chapter_label_names_its_chapter(game_env):
    for row in game_env.state.rows:
        text = game_env.elements[f"row-chapter-{row.sequence}"].innerText
        assert text == row.chapter_label
        assert text.strip()


def test_each_row_holds_a_cell_for_every_one_of_its_plots(game_env):
    total = 0
    for row in game_env.state.rows:
        cells = game_env.elements[f"row-plots-{row.sequence}"].children
        assert len(cells) == len(row.plot_ids)
        total += len(cells)
    assert total == 722


def test_plot_cells_start_as_seeds(game_env):
    module = game_env.module
    for plot in game_env.state.plots:
        element = cell(game_env, plot.plot_id)
        assert "plot--seed" in element.className
        assert element.innerText == module.STAGE_ICON[module.STAGE_SEED]


def test_plot_cell_tooltip_names_the_fact_and_its_topic(game_env):
    plot = game_env.state.plots[0]
    title = cell(game_env, plot.plot_id).title
    assert plot.label in title
    assert plot.topic_title in title


# --- growth stages ---------------------------------------------------------


def test_a_watered_plot_advances_through_the_stage_sprites(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    expected = [
        module.STAGE_SPROUT,
        module.STAGE_BUDDING,
        module.STAGE_BLOOMING,
        module.STAGE_AUTOMATED,
    ]
    for stage in expected:
        state.review(plot.plot_id, True)
        state.advance_day(plot.interval_days)
        module.render()
        element = cell(game_env, plot.plot_id)
        assert f"plot--{stage}" in element.className
        assert element.innerText == module.STAGE_ICON[stage]


def test_an_automated_plot_is_marked_as_auto_watered(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    for _ in range(4):
        state.review(plot.plot_id, True)
        state.advance_day(plot.interval_days)
    module.render()
    element = cell(game_env, plot.plot_id)
    assert "plot--automated" in element.className
    assert module.AUTOMATED_TOOLTIP_NOTE in element.title


def test_an_overdue_plot_wilts_and_recovers_with_one_watering(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    state.review(plot.plot_id, True)
    state.advance_day(2)
    module.render()
    assert "plot--wilting" in cell(game_env, plot.plot_id).className

    state.review(plot.plot_id, True)
    module.render()
    assert "plot--wilting" not in cell(game_env, plot.plot_id).className
    # Nothing was lost — §3's "no plant death".
    assert plot.stage != module.STAGE_SEED
    assert len(state.plots) == 722


def test_seeds_never_render_as_wilting(game_env):
    module, state = game_env.module, game_env.state
    state.advance_day(90)
    module.render()
    for plot in state.plots:
        if plot.last_reviewed is None:
            assert "plot--wilting" not in cell(game_env, plot.plot_id).className


def test_plots_needing_water_are_marked_as_due(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    assert "plot--due" in cell(game_env, plot.plot_id).className

    state.review(plot.plot_id, True)
    module.render()
    assert "plot--due" not in cell(game_env, plot.plot_id).className


# --- the practice panel ----------------------------------------------------


def test_the_practice_panel_is_closed_until_a_plot_is_clicked(game_env):
    assert game_env.elements["practice-panel"].hidden is True
    open_plot(game_env, game_env.state.plots[0].plot_id)
    assert game_env.elements["practice-panel"].hidden is False


def test_clicking_a_plot_asks_a_question_about_that_plot(game_env):
    plot = game_env.state.plots[3]
    open_plot(game_env, plot.plot_id)
    question = game_env.module.current_question
    assert question["plot_id"] == plot.plot_id
    assert game_env.elements["practice-prompt"].innerText == question["prompt"]
    assert game_env.elements["practice-instruction"].innerText == question["instruction"]
    assert game_env.elements["practice-context"].innerText == question["context"]


def test_multiple_choice_questions_render_one_button_per_choice(game_env):
    module = game_env.module
    plot = next(
        p for p in game_env.state.plots
        if module.variants_for(p) and module.V_FR_EN_CHOICE in module.variants_for(p)
    )
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_CHOICE)
    question = module.current_question

    assert question["mode"] == "choice"
    assert len(game_env.elements["practice-choices"].children) == 4
    for index, choice in enumerate(question["choices"]):
        assert game_env.elements[f"practice-choice-{index}"].innerText == choice
    assert game_env.elements["practice-answer-input"].hidden is True
    assert game_env.elements["practice-submit-button"].hidden is True


def test_typed_questions_render_an_input_instead_of_choices(game_env):
    module = game_env.module
    plot = next(p for p in game_env.state.plots if module.V_FR_EN_TYPED in module.variants_for(p))
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)

    assert module.current_question["mode"] == "typed"
    assert game_env.elements["practice-choices"].children == []
    assert game_env.elements["practice-answer-input"].hidden is False
    assert game_env.elements["practice-submit-button"].hidden is False


def test_a_correct_answer_waters_the_plot_and_grows_it(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    open_plot(game_env, plot.plot_id)
    answer_current_correctly(game_env)

    assert plot.correct_streak == 1
    assert plot.stage == module.STAGE_SPROUT
    assert "plot--sprout" in cell(game_env, plot.plot_id).className
    assert game_env.elements["practice-feedback"].innerText


def test_a_wrong_answer_reschedules_without_any_failure_framing(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    for _ in range(3):
        state.review(plot.plot_id, True)
    stage_before = plot.stage

    open_plot(game_env, plot.plot_id)
    answer_current_incorrectly(game_env)

    assert plot.stage == stage_before  # no demotion
    assert plot.interval_days == 1  # just due again sooner
    feedback = game_env.elements["practice-feedback"].innerText
    assert feedback
    assert module.current_question["answer"] in feedback  # it tells you the answer


def test_answering_reveals_the_answer_and_locks_the_choices(game_env):
    game_env_plot = game_env.state.plots[0]
    open_plot(game_env, game_env_plot.plot_id)
    question = game_env.module.current_question
    answer_current_correctly(game_env)

    if question["mode"] == "choice":
        for index in range(len(question["choices"])):
            assert game_env.elements[f"practice-choice-{index}"].disabled is True
    else:
        assert game_env.elements["practice-submit-button"].disabled is True


def test_closing_the_panel_clears_the_question(game_env):
    open_plot(game_env, game_env.state.plots[0].plot_id)
    game_env.close_practice()
    assert game_env.elements["practice-panel"].hidden is True
    assert game_env.module.current_question is None


def test_watering_the_same_plot_again_rerolls_the_question(game_env):
    module = game_env.module
    plot = game_env.state.plots[0]
    asked = set()
    for _ in range(12):
        open_plot(game_env, plot.plot_id)
        asked.add(module.current_question["variant"])
        answer_current_correctly(game_env)
        game_env.close_practice()
    assert len(asked) >= 2


def test_a_reroll_never_repeats_the_previous_variant_back_to_back(game_env):
    module = game_env.module
    plot = game_env.state.plots[0]
    previous = None
    for _ in range(12):
        open_plot(game_env, plot.plot_id)
        variant = module.current_question["variant"]
        assert variant != previous
        previous = variant
        game_env.close_practice()


# --- counters and controls -------------------------------------------------


def test_the_day_display_tracks_the_in_game_day(game_env):
    assert "1" in game_env.elements["day-display"].innerText
    game_env.next_day()
    assert "2" in game_env.elements["day-display"].innerText


def test_the_due_counter_is_a_calm_plots_needing_water_count(game_env):
    module, state = game_env.module, game_env.state
    text = game_env.elements["due-display"].innerText
    assert str(len(state.due_plots())) in text
    assert "water" in text.lower()

    state.review(state.plots[0].plot_id, True)
    module.render()
    assert str(len(state.due_plots())) in game_env.elements["due-display"].innerText


def test_water_next_button_opens_the_next_due_plot(game_env):
    module = game_env.module
    expected = game_env.state.next_due_plot()
    game_env.water_next()
    assert module.current_question["plot_id"] == expected.plot_id


def test_next_day_button_moves_the_calendar_and_rerenders(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    state.review(plot.plot_id, True)
    module.render()
    assert "plot--due" not in cell(game_env, plot.plot_id).className

    game_env.next_day()
    assert state.current_day == 1
    assert "plot--due" in cell(game_env, plot.plot_id).className


def test_progress_display_counts_growing_and_automated_plots(game_env):
    module, state = game_env.module, game_env.state
    for _ in range(4):
        state.review(state.plots[0].plot_id, True)
    module.render()
    text = game_env.elements["progress-display"].innerText
    assert "722" in text
    assert "1" in text


def test_row_progress_shows_how_far_each_row_has_come(game_env):
    module, state = game_env.module, game_env.state
    row = state.rows[0]
    assert f"0/{len(row.plot_ids)}" in game_env.elements["row-progress-1"].innerText

    state.review(row.plot_ids[0], True)
    module.render()
    assert f"1/{len(row.plot_ids)}" in game_env.elements["row-progress-1"].innerText


def test_the_legend_explains_every_stage(game_env):
    module = game_env.module
    text = game_env.elements["legend"].innerText
    for stage in module.STAGE_ORDER:
        assert module.STAGE_ICON[stage] in text
        assert module.STAGE_LABEL[stage] in text


# --- the wellbeing constraint ---------------------------------------------


BANNED = [
    "fail",
    "wrong",
    "lost",
    "died",
    "dead",
    "streak",
    "penalty",
    "punish",
    "🔥",
    "start over",
    "you missed",
]


def test_no_interface_string_uses_failure_or_streak_framing(game_env):
    """§3 and §8: no 'you failed / start over' framing, no streak guilt, no
    fire emoji. This walks every fixed string the UI can show."""
    module = game_env.module
    strings = (
        list(module.INSTRUCTIONS.values())
        + list(module.STAGE_LABEL.values())
        + list(module.FEEDBACK.values())
        + [module.AUTOMATED_TOOLTIP_NOTE, module.DUE_NOTE, module.NOTHING_DUE_MESSAGE]
    )
    for text in strings:
        lowered = text.lower()
        for banned in BANNED:
            assert banned not in lowered, f"{banned!r} appears in {text!r}"


def test_wrong_answer_feedback_is_gentle_and_reopenable(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    open_plot(game_env, plot.plot_id)
    answer_current_incorrectly(game_env)
    feedback = game_env.elements["practice-feedback"].innerText.lower()
    for banned in BANNED:
        assert banned not in feedback
    assert "water" in feedback
