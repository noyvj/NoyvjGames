"""L1: "Passé Composé Sprint" -- the fifth arcade minigame. The same
60-second, three-lives, combo-multiplier rapid-fire as Blitz, but over sequence
21-23 and only the passé composé grammar topics' fill-in-the-blank and
conjugation-swap prompts. Cloned from the Blitz tests: every behaviour that is
shared (timer, lives, combo, lock, render guard) is pinned the same way, and
the two range/content-specific checks are adjusted.

The "60 seconds" is never a real clock in these tests -- sprint_tick() is a
plain counter decrement, driven here exactly like index.html's own
setInterval would drive it in the browser."""


def test_sprint_toggle_button_is_enabled_when_the_range_is_unlocked(game_env):
    module = game_env.module
    assert module.minigames.sprint_available() is True
    assert game_env.elements["sprint-toggle-button"].disabled is False


def test_sprint_panel_is_hidden_until_toggled_open(game_env):
    module = game_env.module
    assert game_env.elements["sprint-panel"].hidden is True
    module.minigames.on_toggle_sprint()
    assert game_env.elements["sprint-panel"].hidden is False


def test_starting_a_run_resets_score_lives_and_timer(game_env):
    module = game_env.module
    mg = module.minigames
    question = mg.start_sprint()
    assert question is not None
    assert mg.sprint_active is True
    assert mg.sprint_score == 0
    assert mg.sprint_lives == mg.SPRINT_STARTING_LIVES
    assert mg.sprint_combo == 0
    assert mg.sprint_time_remaining == mg.SPRINT_DURATION_SECONDS
    assert mg.sprint_question is not None


def test_every_rolled_question_is_a_passe_compose_blank_or_conjugation_choice_in_range(game_env):
    module = game_env.module
    mg = module.minigames
    for _ in range(30):
        mg.start_sprint()
        question = mg.sprint_question
        assert question["mode"] == "choice"
        assert question["variant"] in mg.SPRINT_VARIANTS
        assert module.state.plots_by_id[question["plot_id"]].topic_id in mg.CAFE_PASSE_COMPOSE_TOPIC_IDS
        plot = module.state.plots_by_id[question["plot_id"]]
        assert mg.SPRINT_LO <= plot.sequence <= mg.SPRINT_HI


def test_a_correct_answer_scores_points_and_builds_combo(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_sprint()
    question = mg.sprint_question
    result = mg.submit_sprint_choice(question["answer"])
    assert result is True
    assert mg.sprint_score == mg.SPRINT_BASE_POINTS  # combo=1, multiplier still 1.0x
    assert mg.sprint_combo == 1
    assert mg.sprint_lives == mg.SPRINT_STARTING_LIVES  # unaffected by a correct answer
    assert mg.sprint_question is not None  # a fresh question rolled immediately


def test_a_wrong_answer_costs_a_life_and_resets_combo_not_time(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_sprint()
    question = mg.sprint_question
    wrong = next(c for c in question["choices"] if c != question["answer"])
    time_before = mg.sprint_time_remaining
    result = mg.submit_sprint_choice(wrong)
    assert result is False
    assert mg.sprint_lives == mg.SPRINT_STARTING_LIVES - 1
    assert mg.sprint_combo == 0
    assert mg.sprint_score == 0
    assert mg.sprint_time_remaining == time_before  # no time penalty, see build note


def test_combo_multiplier_grows_every_three_correct_in_a_row(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_sprint()
    for _ in range(6):
        mg.submit_sprint_choice(mg.sprint_question["answer"])
    assert mg.sprint_combo == 6
    expected_multiplier_at_6 = (
        1.0 + min(6 // mg.SPRINT_COMBO_STEP, mg.SPRINT_MAX_COMBO_STEPS) * mg.SPRINT_COMBO_BONUS_PER_STEP
    )
    assert expected_multiplier_at_6 == 2.0
    assert mg._sprint_multiplier(6) == 2.0


def test_three_wrong_answers_end_the_run_on_lives(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_sprint()
    for _ in range(mg.SPRINT_STARTING_LIVES):
        question = mg.sprint_question
        wrong = next(c for c in question["choices"] if c != question["answer"])
        mg.submit_sprint_choice(wrong)
    assert mg.sprint_active is False
    assert mg.sprint_lives == 0
    assert mg.sprint_end_reason == mg.SPRINT_END_LIVES
    assert mg.sprint_question is None


def test_the_timer_running_out_ends_the_run_on_time(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_sprint()
    for _ in range(mg.SPRINT_DURATION_SECONDS):
        mg.sprint_tick()
    assert mg.sprint_active is False
    assert mg.sprint_time_remaining == 0
    assert mg.sprint_end_reason == mg.SPRINT_END_TIME


def test_sprint_tick_is_a_no_op_when_no_run_is_active(game_env):
    module = game_env.module
    mg = module.minigames
    assert mg.sprint_active is False
    result = mg.sprint_tick()
    assert result is None
    assert mg.sprint_time_remaining == mg.SPRINT_DURATION_SECONDS


def test_best_score_this_session_persists_across_runs(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_sprint()
    mg.submit_sprint_choice(mg.sprint_question["answer"])
    scored = mg.sprint_score
    for _ in range(mg.SPRINT_DURATION_SECONDS):
        mg.sprint_tick()
    assert mg.sprint_best_score == scored

    # A fresh run that scores nothing shouldn't erase the earlier best.
    mg.start_sprint()
    for _ in range(mg.SPRINT_STARTING_LIVES):
        question = mg.sprint_question
        wrong = next(c for c in question["choices"] if c != question["answer"])
        mg.submit_sprint_choice(wrong)
    assert mg.sprint_best_score == scored


def test_summary_reads_as_a_light_celebratory_readout_not_a_shaming_one(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_sprint()
    for _ in range(mg.SPRINT_DURATION_SECONDS):
        mg.sprint_tick()
    module.render()
    summary = game_env.elements["sprint-summary"].innerText.lower()
    assert summary != ""
    for banned in ("fail", "lost", "you lose", "game over", "🔥"):
        assert banned not in summary


def test_closing_the_panel_ends_any_active_run_and_hides_it(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_sprint()
    mg.close_sprint()
    assert mg.sprint_open is False
    assert mg.sprint_active is False
    assert mg.sprint_question is None
    assert game_env.elements["sprint-panel"].hidden is True


def test_start_button_click_starts_a_run(game_env):
    module = game_env.module
    game_env.elements["sprint-toggle-button"].dispatch("click", None)
    game_env.elements["sprint-start-button"].dispatch("click", None)
    assert module.minigames.sprint_active is True


def test_choice_buttons_are_rendered_and_clickable(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_sprint()
    module.render()
    choices_box = game_env.elements["sprint-choices"]
    assert len(choices_box.children) == len(mg.sprint_question["choices"])
    game_env.elements["sprint-choice-0"].dispatch("click", None)
    # Either it advanced (fresh question) or ended the run -- either way the
    # click was actually wired to submit_sprint_choice, not inert.
    assert mg.sprint_score > 0 or mg.sprint_lives < mg.SPRINT_STARTING_LIVES


# --- row-unlock gating (spoiler-avoidance, same rule as every other mode) --


def test_sprint_would_be_locked_if_its_range_were_not_fully_unlocked(game_env, monkeypatch):
    """The harness farm has every row open, so this pins the *mechanism* by
    faking a farm whose is_row_unlocked() reports a gap inside the range."""
    module = game_env.module
    mg = module.minigames
    real_is_row_unlocked = module.state.is_row_unlocked
    module.state.is_row_unlocked = lambda sequence: sequence != 22 and real_is_row_unlocked(sequence)
    try:
        assert mg.sprint_available() is False
        assert mg.sprint_lock_reason() == mg._lock_reason(mg.SPRINT_HI)
        assert mg.start_sprint() is None
    finally:
        module.state.is_row_unlocked = real_is_row_unlocked


def test_sprint_never_draws_from_a_locked_row(game_env):
    module = game_env.module
    mg = module.minigames
    for _ in range(25):
        mg.start_sprint()
        plot = module.state.plots_by_id[mg.sprint_question["plot_id"]]
        assert module.state.is_row_unlocked(plot.sequence) is True


# --- variant-constant drift guard -------------------------------------------


def test_minigames_variant_constants_match_games_own(game_env):
    """minigames.py duplicates game.py's V_* variant-name strings rather
    than importing them (avoids the circular import -- see minigames.py's
    module docstring). This pins the duplication against silent drift if
    game.py ever renames one of its own variant constants."""
    module = game_env.module
    mg = module.minigames
    pairs = [
        (mg.VARIANT_FR_EN_CHOICE, module.V_FR_EN_CHOICE),
        (mg.VARIANT_EN_FR_CHOICE, module.V_EN_FR_CHOICE),
        (mg.VARIANT_SYMBOL_NAME_CHOICE, module.V_SYMBOL_NAME_CHOICE),
        (mg.VARIANT_NAME_SYMBOL_CHOICE, module.V_NAME_SYMBOL_CHOICE),
        (mg.VARIANT_EXAMPLE_FR_EN, module.V_EXAMPLE_FR_EN),
        (mg.VARIANT_EXAMPLE_EN_FR, module.V_EXAMPLE_EN_FR),
        (mg.VARIANT_BLANK_WORD, module.V_BLANK_WORD),
        (mg.VARIANT_BLANK_ENDING, module.V_BLANK_ENDING),
        (mg.VARIANT_CONJUGATION_SWAP, module.V_CONJUGATION_SWAP),
    ]
    for mirrored, real in pairs:
        assert mirrored == real
