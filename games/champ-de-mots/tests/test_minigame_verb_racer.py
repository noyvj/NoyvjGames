"""Milestone 28: "Verb Racer" -- a lane-race minigame over sequence 12-15
(FREN152 Bridge + Ch.5: numbers/time revision, daily routine, reflexives,
comparative/superlative). Pick the correctly conjugated verb form to
advance one discrete step; a fixed-pace rival advances on its own every
few real seconds via racer_tick(), the same JS-driven-counter pattern
Blitz's own blitz_tick() already established -- see minigames.py's module
docstring and CLAUDE.md's Milestone 27/28 build notes.

Sequence 12-15 is not the permanent catch-up zone (unlike Blitz's 1-11), so
whether it's actually unlocked depends on how far this particular farm's
plots have grown -- these tests check state.is_row_unlocked() rather than
assuming either way, the same posture test_liaison_drill.py already takes
for its own non-catch-up-zone content.
"""


def _racer_range_unlocked(state, mg):
    return all(state.is_row_unlocked(seq) for seq in range(mg.RACER_LO, mg.RACER_HI + 1))


def test_racer_toggle_reflects_whether_its_range_is_fully_unlocked(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    assert mg.racer_available() == _racer_range_unlocked(state, mg)
    assert game_env.elements["racer-toggle-button"].disabled == (
        not mg.racer_available()
    )


def test_racer_panel_is_hidden_until_toggled_open(game_env):
    module = game_env.module
    assert game_env.elements["racer-panel"].hidden is True
    module.minigames.on_toggle_racer()
    assert game_env.elements["racer-panel"].hidden is False


def _unlock_racer_range(state, mg):
    """Force sequence 12-15 open by sprouting every plot in every row up to
    (and including) row 14, mirroring how test_row_unlock.py's own tests
    drive the farm's real unlock gate rather than reaching around it."""
    for sequence in range(1, mg.RACER_HI):
        for plot in state.row_plots(sequence):
            state.review(plot.plot_id, True)


def test_starting_a_race_resets_positions_and_rolls_a_question(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    question = mg.start_racer()
    assert question is not None
    assert mg.racer_active is True
    assert mg.racer_player_position == 0
    assert mg.racer_rival_position == 0
    assert mg.racer_question is not None


def test_every_rolled_question_is_a_grammar_plot_choice_question_in_range(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    for _ in range(20):
        mg.start_racer()
        question = mg.racer_question
        assert question["mode"] == "choice"
        assert question["variant"] not in mg.RACER_TYPED_VARIANTS
        plot = state.plots_by_id[question["plot_id"]]
        assert plot.topic_type == "grammar"
        assert mg.RACER_LO <= plot.sequence <= mg.RACER_HI


def test_a_correct_answer_advances_the_player_one_step(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    mg.start_racer()
    question = mg.racer_question
    result = mg.submit_racer_choice(question["answer"])
    assert result is True
    assert mg.racer_player_position == 1
    assert mg.racer_question is not None  # a fresh question rolled


def test_a_wrong_answer_does_not_advance_the_player(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    mg.start_racer()
    question = mg.racer_question
    wrong = next(c for c in question["choices"] if c != question["answer"])
    result = mg.submit_racer_choice(wrong)
    assert result is False
    assert mg.racer_player_position == 0
    assert mg.racer_question is not None  # still rerolled, per the build note


def test_reaching_the_finish_line_first_ends_the_race_for_the_player(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    mg.start_racer()
    for _ in range(mg.RACER_TOTAL_STEPS):
        mg.submit_racer_choice(mg.racer_question["answer"])
    assert mg.racer_active is False
    assert mg.racer_player_position == mg.RACER_TOTAL_STEPS
    assert mg.racer_end_reason == mg.RACER_END_PLAYER
    assert mg.racer_question is None


def test_the_rival_advances_a_fixed_pace_regardless_of_the_player(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    mg.start_racer()
    for _ in range(mg.RACER_RIVAL_TICKS_PER_STEP):
        mg.racer_tick()
    assert mg.racer_rival_position == 1
    for _ in range(mg.RACER_RIVAL_TICKS_PER_STEP):
        mg.racer_tick()
    assert mg.racer_rival_position == 2


def test_the_rival_reaching_the_finish_line_first_ends_the_race(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    mg.start_racer()
    for _ in range(mg.RACER_TOTAL_STEPS * mg.RACER_RIVAL_TICKS_PER_STEP):
        mg.racer_tick()
    assert mg.racer_active is False
    assert mg.racer_rival_position == mg.RACER_TOTAL_STEPS
    assert mg.racer_end_reason == mg.RACER_END_RIVAL


def test_racer_tick_is_a_no_op_when_no_race_is_active(game_env):
    module = game_env.module
    mg = module.minigames
    assert mg.racer_active is False
    result = mg.racer_tick()
    assert result is None
    assert mg.racer_rival_position == 0


def test_summary_reads_as_neutral_not_shaming_either_way(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    mg.start_racer()
    for _ in range(mg.RACER_TOTAL_STEPS * mg.RACER_RIVAL_TICKS_PER_STEP):
        mg.racer_tick()
    module.render()
    summary = game_env.elements["racer-summary"].innerText.lower()
    assert summary != ""
    for banned in ("fail", "you lose", "game over", "🔥"):
        assert banned not in summary


def test_marker_positions_reflect_discrete_steps_not_a_continuous_value(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    mg.start_racer()
    module.render()
    assert game_env.elements["racer-player-marker"].style.left == "0%"
    mg.submit_racer_choice(mg.racer_question["answer"])
    module.render()
    expected = round((1 / mg.RACER_TOTAL_STEPS) * 100)
    assert game_env.elements["racer-player-marker"].style.left == f"{expected}%"


def test_closing_the_panel_ends_any_active_race_and_hides_it(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    mg.start_racer()
    mg.close_racer()
    assert mg.racer_open is False
    assert mg.racer_active is False
    assert mg.racer_question is None
    assert game_env.elements["racer-panel"].hidden is True


def test_start_button_click_starts_a_race(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    game_env.elements["racer-toggle-button"].dispatch("click", None)
    game_env.elements["racer-start-button"].dispatch("click", None)
    assert mg.racer_active is True


def test_choice_buttons_are_rendered_and_clickable(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    mg.start_racer()
    module.render()
    choices_box = game_env.elements["racer-choices"]
    assert len(choices_box.children) == len(mg.racer_question["choices"])
    game_env.elements["racer-choice-0"].dispatch("click", None)
    assert mg.racer_player_position > 0 or mg.racer_result is False


def test_race_would_be_locked_if_its_range_were_not_fully_unlocked(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    real_is_row_unlocked = state.is_row_unlocked
    state.is_row_unlocked = lambda sequence: sequence != 13 and real_is_row_unlocked(sequence)
    try:
        assert mg.racer_available() is False
        assert mg.racer_lock_reason() == mg._lock_reason(mg.RACER_HI)
        assert mg.start_racer() is None
    finally:
        state.is_row_unlocked = real_is_row_unlocked


def test_racer_never_draws_from_a_locked_row(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    _unlock_racer_range(state, mg)
    for _ in range(20):
        mg.start_racer()
        plot = state.plots_by_id[mg.racer_question["plot_id"]]
        assert state.is_row_unlocked(plot.sequence) is True
