"""Milestone 11: the Review tab (§14.4) -- Random Word Review and Grammar
Review. Both are opt-in cross-section modes: they pull from any *unlocked*
week regardless of what's currently planted, don't affect row-unlock pacing
(only growth stage does that, and a Review nudge never changes stage), and a
correct answer nudges the source plot's SRS interval slightly forward rather
than being untracked.
"""

import pytest


def _unlock_row_12(game_env):
    """Row 12 stays locked until every plot in row 11 reaches Sprout+."""
    state = game_env.state
    for plot in state.row_plots(11):
        state.review(plot.plot_id, True)


# --- candidate selection -----------------------------------------------


def test_review_candidates_only_pulls_from_unlocked_rows(game_env):
    module, state = game_env.module, game_env.state
    candidates = module.review_candidates({"vocab", "phrase"})
    assert all(state.is_row_unlocked(p.sequence) for p in candidates)
    assert not any(p.sequence == 12 for p in candidates)  # row 12 starts locked


def test_review_candidates_filters_by_topic_type(game_env):
    module = game_env.module
    word_candidates = module.review_candidates({"vocab", "phrase"})
    assert all(p.topic_type in ("vocab", "phrase") for p in word_candidates)

    grammar_candidates = module.review_candidates({"grammar"})
    assert all(p.topic_type == "grammar" for p in grammar_candidates)


def test_review_candidates_respects_the_minimum_stage_filter(game_env):
    module, state = game_env.module, game_env.state
    plot = next(p for p in state.plots if p.topic_type == "vocab")
    state.review(plot.plot_id, True)  # -> Sprout

    at_seed = module.review_candidates({"vocab"}, min_stage=module.STAGE_SEED)
    at_sprout = module.review_candidates({"vocab"}, min_stage=module.STAGE_SPROUT)
    assert plot in at_seed
    assert plot in at_sprout
    assert any(p.stage == module.STAGE_SEED for p in at_seed)
    assert all(p.stage != module.STAGE_SEED for p in at_sprout)


def test_review_never_pulls_plots_from_a_locked_row_even_after_unlock_changes(game_env):
    module, state = game_env.module, game_env.state
    _unlock_row_12(game_env)
    assert state.is_row_unlocked(12)
    candidates = module.review_candidates({"vocab", "phrase"})
    assert any(p.sequence == 12 for p in candidates)
    assert not any(p.sequence == 13 for p in candidates)  # still locked


# --- starting a session --------------------------------------------------


def test_start_word_review_builds_a_queue_of_vocab_and_phrase_plots(game_env):
    module = game_env.module
    module.start_review("word")
    assert module.review_mode == "word"
    assert 1 <= len(module.review_queue) <= module.MAX_REVIEW_COUNT
    for plot_id in module.review_queue:
        plot = module.state.plots_by_id[plot_id]
        assert plot.topic_type in ("vocab", "phrase")
    assert module.review_question is not None


def test_start_grammar_review_builds_a_queue_of_only_grammar_plots(game_env):
    module = game_env.module
    module.start_review("grammar")
    assert module.review_mode == "grammar"
    for plot_id in module.review_queue:
        assert module.state.plots_by_id[plot_id].topic_type == "grammar"


def test_grammar_review_is_biased_toward_blank_and_conjugation_variants(game_env):
    module = game_env.module
    seen_preferred = 0
    total = 0
    for seed in range(20):
        module.QUESTION_RNG = module.random.Random(seed)
        module.start_review("grammar")
        total += 1
        if module.review_question["variant"] in module.GRAMMAR_REVIEW_PREFERRED_VARIANTS:
            seen_preferred += 1
    assert seen_preferred >= total * 0.5


def test_review_count_setting_caps_the_queue_size(game_env):
    module = game_env.module
    game_env.elements["review-count-input"].value = "3"
    module.start_review("word")
    assert len(module.review_queue) <= 3


def test_review_count_setting_is_clamped_to_a_sane_range(game_env):
    module = game_env.module
    game_env.elements["review-count-input"].value = "9999"
    module.start_review("word")
    assert len(module.review_queue) <= module.MAX_REVIEW_COUNT

    game_env.elements["review-count-input"].value = "not a number"
    module.start_review("word")
    assert len(module.review_queue) >= 1


def test_review_min_stage_setting_is_read_from_the_select(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots:
        if plot.topic_type == "vocab":
            state.review(plot.plot_id, True)
            break  # exactly one vocab plot reaches Sprout

    game_env.elements["review-min-stage-select"].value = "automated"
    module.start_review("word")
    assert module.review_queue == []  # nothing has reached Automated yet
    assert module.review_question is None


def test_starting_a_review_with_no_candidates_leaves_the_panel_closed(game_env):
    module = game_env.module
    game_env.elements["review-min-stage-select"].value = "automated"
    module.start_review("word")
    assert module.review_question is None
    assert game_env.elements["review-panel"].hidden is True
    assert game_env.elements["review-empty-message"].hidden is False


# --- answering -------------------------------------------------------------


def test_correct_review_answer_nudges_the_interval_without_touching_stage(game_env):
    module, state = game_env.module, game_env.state
    module.start_review("word")
    plot = state.plots_by_id[module.review_question["plot_id"]]
    stage_before = plot.stage
    interval_before = plot.interval_days

    module.submit_review_answer(module.review_question["answer"])

    assert module.review_result is True
    assert plot.stage == stage_before  # unaffected -- only the daily loop grows plants
    assert plot.interval_days > interval_before
    assert plot.last_reviewed == state.current_day


def test_wrong_review_answer_does_not_touch_srs_state_at_all(game_env):
    module, state = game_env.module, game_env.state
    module.start_review("word")
    plot = state.plots_by_id[module.review_question["plot_id"]]
    before = (plot.stage, plot.interval_days, plot.next_due, plot.last_reviewed, plot.correct_streak)

    question = module.review_question
    if question["mode"] == "choice":
        wrong = next(c for c in question["choices"] if c != question["answer"])
        module.submit_review_answer(wrong)
    else:
        module.submit_review_answer("definitely not correct")

    assert module.review_result is False
    after = (plot.stage, plot.interval_days, plot.next_due, plot.last_reviewed, plot.correct_streak)
    assert before == after


def test_review_never_promotes_a_plot_past_its_daily_loop_stage(game_env):
    """§14.4: Review nudges the interval but is explicitly not a substitute
    for the daily watering loop that actually grows the farm."""
    module, state = game_env.module, game_env.state
    module.start_review("word")
    for _ in range(10):
        if module.review_question is None:
            module.start_review("word")
            if module.review_question is None:
                break
        module.submit_review_answer(module.review_question["answer"])
        module.next_review_question()
    for plot in state.plots:
        if plot.last_reviewed is not None:
            assert plot.stage == module.STAGE_SEED  # never watered via the main loop


def test_review_does_not_change_row_unlock_state(game_env):
    """§14.4: Review is opt-in and doesn't affect plot unlock pacing."""
    module, state = game_env.module, game_env.state
    assert state.is_row_unlocked(12) is False
    module.start_review("word")
    for _ in range(20):
        if module.review_question is None:
            break
        module.submit_review_answer(module.review_question["answer"])
        module.next_review_question()
    assert state.is_row_unlocked(12) is False


# --- session progression ---------------------------------------------------


def test_next_review_question_advances_through_the_queue(game_env):
    module = game_env.module
    game_env.elements["review-count-input"].value = "3"
    module.start_review("word")
    seen = []
    for _ in range(len(module.review_queue)):
        seen.append(module.review_question["plot_id"])
        module.submit_review_answer(module.review_question["answer"])
        module.next_review_question()
    assert seen == module.review_queue
    assert module.review_question is None  # session complete


def test_review_score_tallies_correct_and_total(game_env):
    module = game_env.module
    game_env.elements["review-count-input"].value = "2"
    module.start_review("word")
    module.submit_review_answer(module.review_question["answer"])  # correct
    module.next_review_question()
    if module.review_question is not None:
        question = module.review_question
        if question["mode"] == "choice":
            wrong = next(c for c in question["choices"] if c != question["answer"])
            module.submit_review_answer(wrong)
        else:
            module.submit_review_answer("nope")
        module.next_review_question()
    assert module.review_score["total"] >= 1
    assert module.review_score["correct"] >= 1


def test_close_review_resets_everything(game_env):
    module = game_env.module
    module.start_review("word")
    module.close_review()
    assert module.review_mode is None
    assert module.review_queue == []
    assert module.review_question is None
    assert module.review_result is None
    assert game_env.elements["review-panel"].hidden is True


# --- rendering ---------------------------------------------------------


def test_review_panel_shows_the_current_question(game_env):
    module = game_env.module
    module.start_review("word")
    assert game_env.elements["review-panel"].hidden is False
    assert game_env.elements["review-prompt"].innerText == module.review_question["prompt"]
    assert game_env.elements["review-instruction"].innerText == module.review_question["instruction"]


def test_review_progress_reads_current_position_and_total(game_env):
    module = game_env.module
    game_env.elements["review-count-input"].value = "5"
    module.start_review("word")
    total = len(module.review_queue)
    assert f"1 of {total}" in game_env.elements["review-progress"].innerText


def test_review_summary_shown_once_the_queue_is_exhausted(game_env):
    module = game_env.module
    game_env.elements["review-count-input"].value = "1"
    module.start_review("word")
    module.submit_review_answer(module.review_question["answer"])
    module.next_review_question()
    assert module.review_question is None
    assert "1" in game_env.elements["review-summary"].innerText
    assert game_env.elements["review-summary"].hidden is False


# --- doesn't leak into the save payload -------------------------------------


def test_review_session_state_is_not_part_of_the_save_payload(game_env):
    module = game_env.module
    module.start_review("word")
    state_dict = module.get_state()
    assert set(state_dict) == {"version", "current_day", "plots"}
