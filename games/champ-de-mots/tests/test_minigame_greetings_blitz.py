"""Milestone 27: "Greetings & Basics Blitz" -- a 60-second beat-the-clock
rapid-fire vocab match over sequence 1-11 (FREN151 Ch.1-4). See
minigames.py's own module docstring for the file-boundary rationale (why
this whole arcade family lives outside game.py/style.css, the two files
the farm's own no-timer/no-animation tests scan by name) and CLAUDE.md's
Milestone 27 build note for the 3-lives-not-a-time-penalty design call.

The "60 seconds" is never a real clock in these tests -- blitz_tick() is a
plain counter decrement, driven here exactly like index.html's own
setInterval would drive it in the browser.
"""


def test_blitz_toggle_button_is_enabled_since_rows_1_11_are_always_open(game_env):
    module = game_env.module
    assert module.minigames.blitz_available() is True
    assert game_env.elements["blitz-toggle-button"].disabled is False


def test_blitz_panel_is_hidden_until_toggled_open(game_env):
    module = game_env.module
    assert game_env.elements["blitz-panel"].hidden is True
    module.minigames.on_toggle_blitz()
    assert game_env.elements["blitz-panel"].hidden is False


def test_starting_a_run_resets_score_lives_and_timer(game_env):
    module = game_env.module
    mg = module.minigames
    question = mg.start_blitz()
    assert question is not None
    assert mg.blitz_active is True
    assert mg.blitz_score == 0
    assert mg.blitz_lives == mg.BLITZ_STARTING_LIVES
    assert mg.blitz_combo == 0
    assert mg.blitz_time_remaining == mg.BLITZ_DURATION_SECONDS
    assert mg.blitz_question is not None


def test_every_rolled_question_is_a_translate_choice_variant_in_range(game_env):
    module = game_env.module
    mg = module.minigames
    for _ in range(30):
        mg.start_blitz()
        question = mg.blitz_question
        assert question["mode"] == "choice"
        assert question["variant"] in mg.BLITZ_TRANSLATE_VARIANTS
        plot = module.state.plots_by_id[question["plot_id"]]
        assert mg.BLITZ_LO <= plot.sequence <= mg.BLITZ_HI


def test_a_correct_answer_scores_points_and_builds_combo(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    question = mg.blitz_question
    result = mg.submit_blitz_choice(question["answer"])
    assert result is True
    assert mg.blitz_score == mg.BLITZ_BASE_POINTS  # combo=1, multiplier still 1.0x
    assert mg.blitz_combo == 1
    assert mg.blitz_lives == mg.BLITZ_STARTING_LIVES  # unaffected by a correct answer
    assert mg.blitz_question is not None  # a fresh question rolled immediately


def test_a_wrong_answer_costs_a_life_and_resets_combo_not_time(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    question = mg.blitz_question
    wrong = next(c for c in question["choices"] if c != question["answer"])
    time_before = mg.blitz_time_remaining
    result = mg.submit_blitz_choice(wrong)
    assert result is False
    assert mg.blitz_lives == mg.BLITZ_STARTING_LIVES - 1
    assert mg.blitz_combo == 0
    assert mg.blitz_score == 0
    assert mg.blitz_time_remaining == time_before  # no time penalty, see build note


def test_combo_multiplier_grows_every_three_correct_in_a_row(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    for _ in range(6):
        mg.submit_blitz_choice(mg.blitz_question["answer"])
    assert mg.blitz_combo == 6
    expected_multiplier_at_6 = (
        1.0 + min(6 // mg.BLITZ_COMBO_STEP, mg.BLITZ_MAX_COMBO_STEPS) * mg.BLITZ_COMBO_BONUS_PER_STEP
    )
    assert expected_multiplier_at_6 == 2.0
    assert mg._blitz_multiplier(6) == 2.0


def test_three_wrong_answers_end_the_run_on_lives(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    for _ in range(mg.BLITZ_STARTING_LIVES):
        question = mg.blitz_question
        wrong = next(c for c in question["choices"] if c != question["answer"])
        mg.submit_blitz_choice(wrong)
    assert mg.blitz_active is False
    assert mg.blitz_lives == 0
    assert mg.blitz_end_reason == mg.BLITZ_END_LIVES
    assert mg.blitz_question is None


def test_the_timer_running_out_ends_the_run_on_time(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    for _ in range(mg.BLITZ_DURATION_SECONDS):
        mg.blitz_tick()
    assert mg.blitz_active is False
    assert mg.blitz_time_remaining == 0
    assert mg.blitz_end_reason == mg.BLITZ_END_TIME


def test_blitz_tick_is_a_no_op_when_no_run_is_active(game_env):
    module = game_env.module
    mg = module.minigames
    assert mg.blitz_active is False
    result = mg.blitz_tick()
    assert result is None
    assert mg.blitz_time_remaining == mg.BLITZ_DURATION_SECONDS


def test_best_score_this_session_persists_across_runs(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    mg.submit_blitz_choice(mg.blitz_question["answer"])
    scored = mg.blitz_score
    for _ in range(mg.BLITZ_DURATION_SECONDS):
        mg.blitz_tick()
    assert mg.blitz_best_score == scored

    # A fresh run that scores nothing shouldn't erase the earlier best.
    mg.start_blitz()
    for _ in range(mg.BLITZ_STARTING_LIVES):
        question = mg.blitz_question
        wrong = next(c for c in question["choices"] if c != question["answer"])
        mg.submit_blitz_choice(wrong)
    assert mg.blitz_best_score == scored


def test_summary_reads_as_a_light_celebratory_readout_not_a_shaming_one(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    for _ in range(mg.BLITZ_DURATION_SECONDS):
        mg.blitz_tick()
    module.render()
    summary = game_env.elements["blitz-summary"].innerText.lower()
    assert summary != ""
    for banned in ("fail", "lost", "you lose", "game over", "🔥"):
        assert banned not in summary


def test_closing_the_panel_ends_any_active_run_and_hides_it(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    mg.close_blitz()
    assert mg.blitz_open is False
    assert mg.blitz_active is False
    assert mg.blitz_question is None
    assert game_env.elements["blitz-panel"].hidden is True


def test_start_button_click_starts_a_run(game_env):
    module = game_env.module
    game_env.elements["blitz-toggle-button"].dispatch("click", None)
    game_env.elements["blitz-start-button"].dispatch("click", None)
    assert module.minigames.blitz_active is True


def test_choice_buttons_are_rendered_and_clickable(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    module.render()
    choices_box = game_env.elements["blitz-choices"]
    assert len(choices_box.children) == len(mg.blitz_question["choices"])
    game_env.elements["blitz-choice-0"].dispatch("click", None)
    # Either it advanced (fresh question) or ended the run -- either way the
    # click was actually wired to submit_blitz_choice, not inert.
    assert mg.blitz_score > 0 or mg.blitz_lives < mg.BLITZ_STARTING_LIVES


# --- row-unlock gating (spoiler-avoidance, same rule as every other mode) --


def test_blitz_would_be_locked_if_its_range_were_not_fully_unlocked(game_env, monkeypatch):
    """Sequence 1-11 is the permanent catch-up zone so this can't be
    exercised on the real farm -- pins the *mechanism* instead by faking a
    farm whose is_row_unlocked() reports a gap inside the Blitz range."""
    module = game_env.module
    mg = module.minigames
    real_is_row_unlocked = module.state.is_row_unlocked
    module.state.is_row_unlocked = lambda sequence: sequence != 5 and real_is_row_unlocked(sequence)
    try:
        assert mg.blitz_available() is False
        assert mg.blitz_lock_reason() == mg._lock_reason(mg.BLITZ_HI)
        assert mg.start_blitz() is None
    finally:
        module.state.is_row_unlocked = real_is_row_unlocked


def test_blitz_never_draws_from_a_locked_row(game_env):
    module = game_env.module
    mg = module.minigames
    for _ in range(25):
        mg.start_blitz()
        plot = module.state.plots_by_id[mg.blitz_question["plot_id"]]
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
