"""Milestone 12: weekly proficiency tests (§14.5).

One test per `sequence` entry, covering every topic in that week regardless
of what's currently planted/watered, a single fixed-length session sampling
across the week's topics. Purely informational -- score + per-topic
breakdown, no unlock-gating, no SRS state touched at all.
"""

import pytest


def _unlock_row_12(game_env):
    for plot in game_env.state.row_plots(11):
        game_env.state.review(plot.plot_id, True)


def _unlock_through(game_env, sequence):
    """Sprout every plot in every row up to (and including) `sequence` so
    that row unlocks cascade all the way there."""
    state = game_env.state
    for seq in range(1, sequence + 1):
        for plot in state.row_plots(seq):
            state.review(plot.plot_id, True)


# --- availability ------------------------------------------------------


def test_proficiency_test_is_available_for_an_unlocked_week(game_env):
    module = game_env.module
    assert module.is_proficiency_test_available(1) is True


def test_proficiency_test_is_not_available_for_a_locked_week(game_env):
    module, state = game_env.module, game_env.state
    assert state.is_row_unlocked(12) is False
    assert module.is_proficiency_test_available(12) is False


def test_proficiency_test_becomes_available_once_the_week_unlocks(game_env):
    module, state = game_env.module, game_env.state
    _unlock_row_12(game_env)
    assert state.is_row_unlocked(12) is True
    assert module.is_proficiency_test_available(12) is True


def test_starting_a_test_for_a_locked_week_does_nothing(game_env):
    module = game_env.module
    module.start_proficiency_test(12)
    assert module.proficiency_mode is False
    assert module.proficiency_questions == []


# --- building the test: covers every topic ----------------------------


def test_build_proficiency_test_covers_every_topic_in_the_week(game_env):
    module = game_env.module
    topics = module.proficiency_test_topics(1)
    entries = module.build_proficiency_test(1, module.random.Random(1))
    covered_topic_ids = {e["topic_id"] for e in entries}
    assert covered_topic_ids == {t["id"] for t in topics}


def test_build_proficiency_test_is_a_fixed_length_around_fifteen_to_twenty(game_env):
    module = game_env.module
    # Sequence 8 has 10 topics -- the biggest in the catalog -- and still
    # fits comfortably under the target length.
    entries = module.build_proficiency_test(8, module.random.Random(2))
    assert 15 <= len(entries) <= 20


def test_build_proficiency_test_never_drops_below_topic_coverage_even_if_short(game_env):
    """A tiny week (sequence 22 has only 2 topics) still gets every topic
    covered, even though the session can't reach a full 15 without repeats."""
    module = game_env.module
    topics = module.proficiency_test_topics(22)
    entries = module.build_proficiency_test(22, module.random.Random(3))
    covered = {e["topic_id"] for e in entries}
    assert covered == {t["id"] for t in topics}
    assert len(entries) >= len(topics)


def test_build_proficiency_test_ignores_current_plot_srs_state(game_env):
    """§14.5: "covering every topic in that week regardless of what's
    currently planted/watered" -- an all-Seed week still produces a full
    test (this doesn't depend on Review's growth-stage filtering at all)."""
    module = game_env.module
    for plot in game_env.state.row_plots(1):
        assert plot.stage == module.STAGE_SEED  # nothing watered yet
    entries = module.build_proficiency_test(1, module.random.Random(4))
    assert len(entries) > 0


def test_every_proficiency_question_is_a_valid_checkable_question(game_env):
    module = game_env.module
    for sequence in (1, 8, 11, 22):
        entries = module.build_proficiency_test(sequence, module.random.Random(sequence))
        for entry in entries:
            question = entry["question"]
            assert question["prompt"]
            assert question["answer"]
            assert module.check_answer(question, question["answer"]) is True


# --- starting and answering a session ---------------------------------


def test_start_proficiency_test_sets_up_session_state(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    assert module.proficiency_mode is True
    assert module.proficiency_sequence == 1
    assert len(module.proficiency_questions) > 0
    assert module.proficiency_index == 0
    assert module.proficiency_score == {"correct": 0, "total": 0}


def test_submit_proficiency_answer_updates_score_and_topic_breakdown(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    entry = module.proficiency_questions[0]
    question = entry["question"]
    module.submit_proficiency_answer(question["answer"])
    assert module.proficiency_result is True
    assert module.proficiency_score == {"correct": 1, "total": 1}
    topic_score = module.proficiency_topic_scores[entry["topic_id"]]
    assert topic_score["correct"] == 1
    assert topic_score["total"] == 1


def test_submit_proficiency_wrong_answer_still_counts_the_attempt(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    question = module.proficiency_questions[0]["question"]
    if question["mode"] == "choice":
        wrong = next(c for c in question["choices"] if c != question["answer"])
        module.submit_proficiency_answer(wrong)
    else:
        module.submit_proficiency_answer("definitely wrong")
    assert module.proficiency_result is False
    assert module.proficiency_score == {"correct": 0, "total": 1}


def test_proficiency_test_never_touches_srs_state(game_env):
    """Purely informational (§14.5) -- no plot's stage/interval/streak/
    last_reviewed changes as a result of taking the test."""
    module, state = game_env.module, game_env.state
    before = {
        p.plot_id: (p.stage, p.interval_days, p.next_due, p.last_reviewed, p.correct_streak)
        for p in state.plots
    }
    module.start_proficiency_test(1)
    for _ in range(len(module.proficiency_questions)):
        question = module.proficiency_questions[module.proficiency_index]["question"]
        module.submit_proficiency_answer(question["answer"])
        module.next_proficiency_question()
    after = {
        p.plot_id: (p.stage, p.interval_days, p.next_due, p.last_reviewed, p.correct_streak)
        for p in state.plots
    }
    assert before == after


def test_proficiency_test_never_affects_row_unlock_state(game_env):
    module, state = game_env.module, game_env.state
    assert state.is_row_unlocked(12) is False
    module.start_proficiency_test(1)
    for _ in range(len(module.proficiency_questions)):
        question = module.proficiency_questions[module.proficiency_index]["question"]
        module.submit_proficiency_answer(question["answer"])
        module.next_proficiency_question()
    assert state.is_row_unlocked(12) is False


def test_next_proficiency_question_advances_and_resets_result(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    question = module.proficiency_questions[0]["question"]
    module.submit_proficiency_answer(question["answer"])
    assert module.proficiency_result is not None
    module.next_proficiency_question()
    assert module.proficiency_index == 1
    assert module.proficiency_result is None


def test_proficiency_test_completes_after_the_last_question(game_env):
    module = game_env.module
    _unlock_through(game_env, 22)
    module.start_proficiency_test(22)  # smallest week
    total = len(module.proficiency_questions)
    for _ in range(total):
        question = module.proficiency_questions[module.proficiency_index]["question"]
        module.submit_proficiency_answer(question["answer"])
        module.next_proficiency_question()
    assert module.proficiency_index == total
    assert module.proficiency_score["total"] == total


def test_close_proficiency_test_resets_everything(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    module.close_proficiency_test()
    assert module.proficiency_mode is False
    assert module.proficiency_questions == []
    assert module.proficiency_sequence is None


# --- rendering -----------------------------------------------------------


def test_proficiency_panel_shows_the_current_question(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    entry = module.proficiency_questions[0]
    assert game_env.elements["proficiency-panel"].hidden is False
    assert game_env.elements["proficiency-prompt"].innerText == entry["question"]["prompt"]


def test_proficiency_progress_reads_position_and_total(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    total = len(module.proficiency_questions)
    assert f"1 of {total}" in game_env.elements["proficiency-progress"].innerText


def test_proficiency_summary_and_topic_breakdown_shown_on_completion(game_env):
    module = game_env.module
    _unlock_through(game_env, 22)
    module.start_proficiency_test(22)
    total = len(module.proficiency_questions)
    for _ in range(total):
        question = module.proficiency_questions[module.proficiency_index]["question"]
        module.submit_proficiency_answer(question["answer"])
        module.next_proficiency_question()
    assert str(total) in game_env.elements["proficiency-summary"].innerText
    breakdown = game_env.elements["proficiency-topic-breakdown"]
    assert len(breakdown.children) == len(module.proficiency_topic_scores)


def test_proficiency_panel_hides_on_close(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    module.close_proficiency_test()
    assert game_env.elements["proficiency-panel"].hidden is True


# --- per-row entry point -----------------------------------------------


def test_each_unlocked_row_gets_a_proficiency_test_button(game_env):
    module, state = game_env.module, game_env.state
    for row in state.rows:
        button = game_env.elements.get(f"row-proficiency-{row.sequence}")
        assert button is not None
        assert button.disabled == (not state.is_row_unlocked(row.sequence))


def test_clicking_a_row_proficiency_button_starts_that_weeks_test(game_env):
    module = game_env.module
    game_env.elements["row-proficiency-1"].dispatch("click", None)
    assert module.proficiency_mode is True
    assert module.proficiency_sequence == 1


def test_locked_row_proficiency_button_is_disabled_and_does_nothing(game_env):
    module = game_env.module
    button = game_env.elements["row-proficiency-12"]
    assert button.disabled is True
    button.dispatch("click", None)
    assert module.proficiency_mode is False


# --- no SRS state leaks into the save payload -------------------------------


def test_proficiency_session_is_not_part_of_the_save_payload(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    state_dict = module.get_state()
    assert set(state_dict) == {"version", "current_day", "plots"}
