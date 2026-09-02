"""Milestone 9: the "I think this should count" report button (§14.2.4).

Shown only once a written (typed) answer is marked wrong. Tapping it builds
`{item_id, submitted_answer, marked_correct_answer, topic_type, timestamp}`
(the timestamp is the backend's own `created_at`, not something game.py has
to produce -- see CLAUDE.md's Milestone 9 build note) and hands it off to a
JS-side sender; the actual network POST is out of scope for this fake-DOM
harness (same boundary the shared save widget already draws -- Python
computes, JS fetches), so these tests pin the payload's shape and the
button's visibility/one-shot behaviour instead.
"""


def _open_typed_question(game_env, plot_id=None, variant=None):
    module, state = game_env.module, game_env.state
    if plot_id is None:
        plot = next(
            p for p in state.plots if module.V_FR_EN_TYPED in module.variants_for(p)
        )
        plot_id = plot.plot_id
        variant = module.V_FR_EN_TYPED
    module.open_practice(plot_id, variant=variant)
    return module.current_question


# --- visibility --------------------------------------------------------


def test_report_button_is_hidden_before_any_answer(game_env):
    module = game_env.module
    _open_typed_question(game_env)
    module.render()
    assert game_env.elements["practice-report-button"].hidden is True


def test_report_button_is_hidden_when_the_answer_is_correct(game_env):
    module = game_env.module
    question = _open_typed_question(game_env)
    module.submit_answer(question["answer"])
    assert module.current_result is True
    assert game_env.elements["practice-report-button"].hidden is True


def test_report_button_appears_once_a_typed_answer_is_marked_wrong(game_env):
    module = game_env.module
    _open_typed_question(game_env)
    module.submit_answer("definitely not the answer 12345")
    assert module.current_result is False
    assert game_env.elements["practice-report-button"].hidden is False


def test_report_button_never_appears_for_a_wrong_multiple_choice_answer(game_env):
    """§14.2.4 says "every written-answer prompt" -- a multiple-choice miss
    isn't ambiguous the way a typed miss can be, so no report button there."""
    module = game_env.module
    plot = next(
        p for p in game_env.state.plots if module.V_FR_EN_CHOICE in module.variants_for(p)
    )
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_CHOICE)
    question = module.current_question
    wrong_choice = next(c for c in question["choices"] if c != question["answer"])
    module.submit_answer(wrong_choice)
    assert module.current_result is False
    assert game_env.elements["practice-report-button"].hidden is True


def test_report_button_is_hidden_again_once_the_panel_closes(game_env):
    module = game_env.module
    _open_typed_question(game_env)
    module.submit_answer("wrong answer")
    assert game_env.elements["practice-report-button"].hidden is False
    game_env.close_practice()
    assert game_env.elements["practice-report-button"].hidden is True


# --- payload shape -------------------------------------------------------


def test_report_payload_has_the_documented_shape(game_env):
    module = game_env.module
    question = _open_typed_question(game_env)
    module.submit_answer("wrong answer")

    payload = module._report_payload()
    assert set(payload) == {
        "game_id", "item_id", "submitted_answer", "marked_correct_answer", "topic_type",
    }
    assert payload["item_id"] == question["plot_id"]
    assert payload["submitted_answer"] == "wrong answer"
    assert payload["marked_correct_answer"] == [question["answer"]]
    assert payload["topic_type"] == question["topic_type"]
    assert payload["game_id"] == "champ-de-mots"


def test_report_payload_is_none_when_there_is_nothing_to_report(game_env):
    module = game_env.module
    assert module._report_payload() is None  # no question open at all

    question = _open_typed_question(game_env)
    assert module._report_payload() is None  # not yet answered

    module.submit_answer(question["answer"])
    assert module._report_payload() is None  # answered correctly


def test_report_payload_includes_accepted_variants_when_present(game_env):
    module, state = game_env.module, game_env.state
    plot = next(
        p
        for p in state.plots
        if module.V_FR_EN_TYPED in module.variants_for(p)
        and module.grading_tier(p.items[0]["en"]) == module.TIER_LENIENT
    )
    item = plot.items[0]
    item["accepted_en"] = ["a hand-curated alternate phrasing"]
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    module.submit_answer("nothing like the answer at all")

    payload = module._report_payload()
    assert payload["marked_correct_answer"][0] == item["en"]
    assert "a hand-curated alternate phrasing" in payload["marked_correct_answer"]
    del item["accepted_en"]


# --- submit_report(): one-shot, updates the button ------------------------


def test_submit_report_disables_further_reports_for_the_same_question(game_env):
    module = game_env.module
    _open_typed_question(game_env)
    module.submit_answer("wrong answer")

    button = game_env.elements["practice-report-button"]
    assert button.disabled is False

    button.dispatch("click", None)
    assert module.report_sent is True
    assert button.disabled is True
    assert button.hidden is False  # stays visible, just disabled/relabelled

    # A second click is a no-op -- nothing to send twice.
    result = module.submit_report()
    assert result is None


def test_report_sent_resets_on_the_next_question(game_env):
    module = game_env.module
    plot = next(p for p in game_env.state.plots if module.V_FR_EN_TYPED in module.variants_for(p))
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    module.submit_answer("wrong answer")
    module.submit_report()
    assert module.report_sent is True

    game_env.close_practice()
    assert module.report_sent is False

    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    assert module.report_sent is False


def test_submit_report_is_a_no_op_with_nothing_to_report(game_env):
    module = game_env.module
    assert module.submit_report() is None
    assert module.report_sent is False


# --- no in-game admin/review UI (§14.4's decision) -------------------------


def test_no_report_review_or_admin_page_elements_exist(game_env):
    """§14.4: reports get triaged by querying the backend directly, not
    through a page in the game itself."""
    for forbidden_id in ("report-review-panel", "report-admin-panel", "reports-list"):
        assert forbidden_id not in game_env.elements
