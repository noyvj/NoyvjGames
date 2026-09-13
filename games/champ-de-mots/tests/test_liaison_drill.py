"""Improvement Ideas addendum: liaison/elision as a real practice type.
Hand-authored quiz content (fren_supplementary_notes.json's "liaison_drill"
list), one question per testable pronunciation rule from the TTS watchlist.
Entirely stateless with respect to SRS and row-unlock caching, same posture
as the proficiency test and bonus sections: no state.review(), no nudge.
"""


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def test_the_drill_has_real_hand_authored_content(game_env):
    module = game_env.module
    assert len(module.LIAISON_DRILL_QUESTIONS) >= 5
    for entry in module.LIAISON_DRILL_QUESTIONS:
        assert entry["prompt"]
        assert entry["answer"] in entry["choices"]
        assert len(entry["choices"]) >= 2
        assert len(set(entry["choices"])) == len(entry["choices"])


def test_the_drill_is_available_on_a_fresh_farm(game_env):
    """FREN151's catch-up zone (sequence <= 11) is unconditionally unlocked,
    and several drill questions target sequences in it -- so the drill has
    something to offer from the very first day, no watering required."""
    module = game_env.module
    assert module.liaison_drill_available() is True


def test_build_liaison_drill_only_includes_unlocked_sequences(game_env):
    module, state = game_env.module, game_env.state
    drill = module.build_liaison_drill()
    for entry in drill:
        assert state.is_row_unlocked(entry["sequence"])


def test_build_liaison_drill_excludes_a_locked_sequence(game_env):
    module, state = game_env.module, game_env.state
    locked_sequences = {
        entry["sequence"]
        for entry in module.LIAISON_DRILL_QUESTIONS
        if not state.is_row_unlocked(entry["sequence"])
    }
    assert locked_sequences, "fixture assumption: at least one drill question targets a locked week"
    drill = module.build_liaison_drill()
    drill_sequences = {entry["sequence"] for entry in drill}
    assert not (locked_sequences & drill_sequences)


def test_starting_the_drill_populates_a_session(game_env):
    module = game_env.module
    questions = module.start_liaison_drill()
    assert module.liaison_mode is True
    assert questions == module.liaison_questions
    assert module.liaison_index == 0
    assert module.liaison_result is None
    assert module.liaison_score == {"correct": 0, "total": 0}


def test_answering_correctly_scores_a_point(game_env):
    module = game_env.module
    module.start_liaison_drill()
    entry = module.liaison_questions[0]
    result = module.submit_liaison_answer(entry["answer"])
    assert result is True
    assert module.liaison_result is True
    assert module.liaison_score == {"correct": 1, "total": 1}


def test_answering_incorrectly_does_not_score_a_point(game_env):
    module = game_env.module
    module.start_liaison_drill()
    entry = module.liaison_questions[0]
    wrong = next(c for c in entry["choices"] if c != entry["answer"])
    result = module.submit_liaison_answer(wrong)
    assert result is False
    assert module.liaison_score == {"correct": 0, "total": 1}


def test_a_second_submit_before_advancing_is_a_no_op(game_env):
    module = game_env.module
    module.start_liaison_drill()
    entry = module.liaison_questions[0]
    module.submit_liaison_answer(entry["answer"])
    again = module.submit_liaison_answer(entry["answer"])
    assert again is None
    assert module.liaison_score == {"correct": 1, "total": 1}


def test_advancing_moves_to_the_next_question_and_clears_the_result(game_env):
    module = game_env.module
    module.start_liaison_drill()
    entry = module.liaison_questions[0]
    module.submit_liaison_answer(entry["answer"])
    module.next_liaison_question()
    assert module.liaison_index == 1
    assert module.liaison_result is None


def test_finishing_every_question_marks_the_session_complete(game_env):
    module = game_env.module
    module.start_liaison_drill()
    total = len(module.liaison_questions)
    for _ in range(total):
        entry = module.liaison_questions[module.liaison_index]
        module.submit_liaison_answer(entry["answer"])
        module.next_liaison_question()
    assert module.liaison_index == total
    assert module.liaison_score == {"correct": total, "total": total}


def test_closing_the_drill_resets_the_session(game_env):
    module = game_env.module
    module.start_liaison_drill()
    entry = module.liaison_questions[0]
    module.submit_liaison_answer(entry["answer"])
    module.close_liaison_drill()
    assert module.liaison_mode is False
    assert module.liaison_questions == []
    assert module.liaison_index == 0
    assert module.liaison_result is None


def test_the_drill_never_mutates_srs_state(game_env):
    module, state = game_env.module, game_env.state
    stages_before = [p.stage for p in state.plots]
    module.start_liaison_drill()
    entry = module.liaison_questions[0]
    module.submit_liaison_answer(entry["answer"])
    module.next_liaison_question()
    assert [p.stage for p in state.plots] == stages_before


def test_the_panel_is_hidden_until_toggled_open(game_env):
    module = game_env.module
    assert module.liaison_mode is False
    assert game_env.elements["liaison-panel"].hidden is True


def test_toggling_opens_and_then_closes_the_panel(game_env):
    module = game_env.module
    module.on_toggle_liaison_drill()
    assert module.liaison_mode is True
    assert game_env.elements["liaison-panel"].hidden is False

    module.on_toggle_liaison_drill()
    assert module.liaison_mode is False
    assert game_env.elements["liaison-panel"].hidden is True


def test_correct_feedback_does_not_mention_a_plot(game_env):
    """This is a standalone quiz, not tied to any plot -- the farm's usual
    "this plot is growing" phrasing would be nonsense here."""
    module = game_env.module
    module.start_liaison_drill()
    entry = module.liaison_questions[0]
    module.submit_liaison_answer(entry["answer"])
    feedback = game_env.elements["liaison-feedback"].innerText
    assert entry["answer"] in feedback
    assert "plot" not in feedback.lower()


def test_the_explanation_only_appears_after_answering(game_env):
    module = game_env.module
    module.start_liaison_drill()
    explanation = game_env.elements["liaison-explanation"]
    assert explanation.hidden is True

    entry = module.liaison_questions[0]
    module.submit_liaison_answer(entry["answer"])
    assert explanation.hidden is False
    assert explanation.innerText == entry.get("explanation", "")


def test_the_summary_shows_the_final_score(game_env):
    module = game_env.module
    module.start_liaison_drill()
    total = len(module.liaison_questions)
    for _ in range(total):
        entry = module.liaison_questions[module.liaison_index]
        module.submit_liaison_answer(entry["answer"])
        module.next_liaison_question()

    summary = game_env.elements["liaison-summary"]
    assert summary.hidden is False
    assert f"{total} of {total}" in summary.innerText


def test_clicking_a_choice_button_submits_that_answer(game_env):
    module = game_env.module
    module.start_liaison_drill()
    entry = module.liaison_questions[0]
    choices_box = game_env.elements["liaison-choices"]
    button = next(c for c in choices_box.children if c.innerText == entry["answer"])
    button.dispatch("click", None)
    assert module.liaison_result is True


def test_a_correct_choice_button_is_highlighted_after_answering(game_env):
    module = game_env.module
    module.start_liaison_drill()
    entry = module.liaison_questions[0]
    module.submit_liaison_answer(entry["answer"])
    choices_box = game_env.elements["liaison-choices"]
    answer_button = next(c for c in choices_box.children if c.innerText == entry["answer"])
    assert "choice--answer" in answer_button.className
    assert all(c.disabled for c in choices_box.children)
