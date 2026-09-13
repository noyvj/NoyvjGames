"""Milestone 24: a mispronunciation-risk report button. Most of the TTS
watchlist's entries (fren_supplementary_notes.json) describe a rule with no
single catalog item to attach to -- those are already covered abstractly by
the liaison drill (Milestone 22). A handful name one exact catalog item by
its own fr text; those get a small risk note, and every question (flagged
or not) gets a report button so a player can flag something the watchlist
didn't anticipate too.
"""


def _plot_for_fr(state, fr_text):
    return next(p for p in state.plots if p.items[0].get("fr") == fr_text)


def test_pronunciation_risk_notes_resolves_known_exact_matches(game_env):
    module = game_env.module
    assert "travailler" in module.PRONUNCIATION_RISK_NOTES
    assert "du shampooing" in module.PRONUNCIATION_RISK_NOTES


def test_pronunciation_risk_notes_excludes_rule_level_watchlist_entries(game_env):
    """Entries like "liaison consonant sounds" describe a rule, not one
    catalog item -- they must not show up as if they were a flagged item."""
    module = game_env.module
    assert "liaison consonant sounds" not in module.PRONUNCIATION_RISK_NOTES
    assert "septante / huitante / nonante" not in module.PRONUNCIATION_RISK_NOTES


def test_the_report_button_is_hidden_with_no_question_open(game_env):
    module = game_env.module
    assert module.current_question is None
    assert game_env.elements["practice-pronunciation-report-button"].hidden is True
    assert game_env.elements["practice-pronunciation-note"].hidden is True


def test_the_report_button_appears_for_any_open_question_unanswered(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    module.open_practice(plot.plot_id)
    assert game_env.elements["practice-pronunciation-report-button"].hidden is False


def test_the_report_button_stays_visible_after_a_correct_answer(game_env):
    """Unlike the "should count" report button, this one isn't gated by the
    result at all -- a pronunciation concern doesn't depend on whether the
    attempt was right or wrong."""
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_CHOICE)
    question = module.current_question
    module.submit_answer(question["answer"])
    assert module.current_result is True
    assert game_env.elements["practice-pronunciation-report-button"].hidden is False


def test_the_risk_note_shows_for_a_flagged_item(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "travailler")
    module.open_practice(plot.plot_id)
    note = game_env.elements["practice-pronunciation-note"]
    assert note.hidden is False
    assert "travailler" not in note.innerText  # the note is the watchlist's own text, not a restatement
    assert module.PRONUNCIATION_RISK_NOTES["travailler"] in note.innerText


def test_the_risk_note_is_hidden_for_an_unflagged_item(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    assert plot.items[0]["fr"] not in module.PRONUNCIATION_RISK_NOTES
    module.open_practice(plot.plot_id)
    assert game_env.elements["practice-pronunciation-note"].hidden is True


def test_submitting_a_report_sends_the_items_own_fr_text(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "travailler")
    module.open_practice(plot.plot_id)
    payload = module.submit_pronunciation_report()
    assert payload["item_id"] == plot.plot_id
    assert payload["marked_correct_answer"] == ["travailler"]
    assert payload["topic_type"] == "pronunciation"
    assert payload["submitted_answer"] == module.PRONUNCIATION_REPORT_MARKER


def test_a_second_report_click_is_a_no_op(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    module.open_practice(plot.plot_id)
    first = module.submit_pronunciation_report()
    second = module.submit_pronunciation_report()
    assert first is not None
    assert second is None


def test_the_button_disables_and_relabels_once_sent(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    module.open_practice(plot.plot_id)
    module.submit_pronunciation_report()
    button = game_env.elements["practice-pronunciation-report-button"]
    assert button.disabled is True
    assert button.innerText == module.PRONUNCIATION_REPORT_SENT_LABEL


def test_the_report_state_resets_on_a_fresh_question(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    module.open_practice(plot.plot_id)
    module.submit_pronunciation_report()
    module.close_practice()
    module.open_practice(state.plots[1].plot_id)
    assert module.pronunciation_report_sent is False
    assert game_env.elements["practice-pronunciation-report-button"].disabled is False


def test_the_two_report_types_are_independent(game_env):
    """Reporting a pronunciation concern must not also mark the
    correctness-report ("I think this should count") as sent, and vice
    versa -- they track genuinely separate things about the same question."""
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    module.submit_answer("definitely wrong")
    assert module.current_result is False
    module.submit_pronunciation_report()
    assert module.pronunciation_report_sent is True
    assert module.report_sent is False


def test_no_report_payload_with_nothing_open(game_env):
    module = game_env.module
    assert module.submit_pronunciation_report() is None
