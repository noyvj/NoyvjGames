"""L28: a small, session-only badge for perfectly answering a full row's
worth of plots in one sitting -- every plot in the row answered correctly
this session, with zero wrong answers anywhere in that row this session.

"One sitting" is read literally as *this session*: the tracking dicts and
the badge itself are pure session state, never saved (same posture as
combo_count/ACCENT_SENSITIVE), so a fresh page load always starts every
row unspoiled and un-badged.

Sequence 22 is the catalog's smallest week (2 plots), used throughout so a
full row can be answered in just two submissions.
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


SEQ22_PLOT_IDS = ["fren152-w12-grammar001", "fren152-w12-grammar002"]


def _badge(game_env, sequence):
    return game_env.elements[f"row-perfect-badge-{sequence}"]


def test_badge_starts_hidden(game_env):
    game_env.module.render()
    assert _badge(game_env, 22).hidden is True


def test_badge_appears_once_every_plot_in_the_row_is_answered_correctly(game_env):
    module = game_env.module
    open_plot(game_env, SEQ22_PLOT_IDS[0])
    answer_current_correctly(game_env)
    assert 22 not in module.row_session_perfect_badge
    assert _badge(game_env, 22).hidden is True

    open_plot(game_env, SEQ22_PLOT_IDS[1])
    answer_current_correctly(game_env)
    assert 22 in module.row_session_perfect_badge
    assert _badge(game_env, 22).hidden is False


def test_a_wrong_answer_spoils_the_row_even_if_everything_else_is_correct(game_env):
    module = game_env.module
    open_plot(game_env, SEQ22_PLOT_IDS[0])
    answer_current_incorrectly(game_env)
    open_plot(game_env, SEQ22_PLOT_IDS[1])
    answer_current_correctly(game_env)

    assert 22 in module.row_session_spoiled
    assert 22 not in module.row_session_perfect_badge
    module.render()
    assert _badge(game_env, 22).hidden is True


def test_correcting_a_spoiled_plot_never_earns_the_badge_this_session(game_env):
    module = game_env.module
    open_plot(game_env, SEQ22_PLOT_IDS[0])
    answer_current_incorrectly(game_env)
    # Re-open and answer correctly on a later attempt -- the row was
    # already spoiled the moment the wrong answer landed.
    open_plot(game_env, SEQ22_PLOT_IDS[0])
    answer_current_correctly(game_env)
    open_plot(game_env, SEQ22_PLOT_IDS[1])
    answer_current_correctly(game_env)

    assert 22 not in module.row_session_perfect_badge


def test_other_rows_are_unaffected_by_one_rows_spoiling(game_env):
    module = game_env.module
    open_plot(game_env, SEQ22_PLOT_IDS[0])
    answer_current_incorrectly(game_env)
    assert 22 in module.row_session_spoiled
    assert 1 not in module.row_session_spoiled
    assert 1 not in module.row_session_correct


def test_session_state_is_not_part_of_the_save_payload(game_env):
    module = game_env.module
    open_plot(game_env, SEQ22_PLOT_IDS[0])
    answer_current_correctly(game_env)
    open_plot(game_env, SEQ22_PLOT_IDS[1])
    answer_current_correctly(game_env)
    assert 22 in module.row_session_perfect_badge

    data = module.get_state()
    assert "row_session_perfect_badge" not in data
    assert "row_session_correct" not in data
    assert "row_session_spoiled" not in data
