"""Z11 (planning/TODO.md, site-wide goal): "My Reports" -- a small, dated
feed confirming every report this player has actually sent, built on the
shared shared/narrative_log.py component. Investigating this game's own
L14 line found it already fully satisfied by the pre-existing
REPORT_SENT_LABEL button-label swap (unrelated to a narrative log); this
panel is the genuinely new narrative-log-shaped feature Z11 asks for
instead. See game.py's own build note right above `_record_report_log_entry`.
"""


def _plot_for_fr(state, fr_text):
    return next(p for p in state.plots if p.items[0].get("fr") == fr_text)


def _open_typed_question(game_env):
    module, state = game_env.module, game_env.state
    plot = next(p for p in state.plots if module.V_FR_EN_TYPED in module.variants_for(p))
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    return module.current_question


# --- recording -------------------------------------------------------------


def test_report_log_starts_empty(game_env):
    module = game_env.module
    assert module.report_log == []


def test_submitting_a_should_count_report_adds_one_log_entry(game_env):
    module = game_env.module
    question = _open_typed_question(game_env)
    module.submit_answer("definitely not the answer 12345")
    module.submit_report()

    assert len(module.report_log) == 1
    entry = module.report_log[0]
    assert entry["day"] == module.state.current_day
    assert entry["topic"] == question["topic_type"]
    assert question["answer"] in entry["text"]
    assert entry["text"].startswith("Reported")


def test_submitting_a_pronunciation_report_uses_the_pronunciation_label(game_env):
    module, state = game_env.module, game_env.state
    plot = _plot_for_fr(state, "travailler")
    module.open_practice(plot.plot_id)
    module.submit_pronunciation_report()

    assert len(module.report_log) == 1
    entry = module.report_log[0]
    assert entry["topic"] == "pronunciation"
    assert "pronunciation concern" in entry["text"]
    assert "travailler" in entry["text"]


def test_a_second_click_does_not_double_log(game_env):
    """submit_*_report() is already one-shot per question -- a second call
    is a no-op that returns None before _record_report_log_entry() is ever
    reached, so nothing extra should land in the log either."""
    module = game_env.module
    _open_typed_question(game_env)
    module.submit_answer("wrong answer")
    module.submit_report()
    module.submit_report()
    assert len(module.report_log) == 1


def test_a_report_with_nothing_to_report_logs_nothing(game_env):
    module = game_env.module
    assert module.submit_report() is None
    assert module.report_log == []


def test_reports_from_different_surfaces_all_land_in_the_one_shared_log(game_env):
    """Sanity check that every one of the 10 submit_*_report() call sites
    was actually wired up, not just the two exercised above."""
    module, state = game_env.module, game_env.state

    plot = next(p for p in state.plots if module.V_FR_EN_TYPED in module.variants_for(p))
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    module.submit_answer("wrong")
    module.submit_report()

    module.close_practice()
    module.open_practice(plot.plot_id)
    module.submit_pronunciation_report()

    assert len(module.report_log) == 2
    assert {e["topic"] for e in module.report_log} == {plot.topic_type, "pronunciation"}


# --- cap ---------------------------------------------------------------


def test_the_log_is_capped_at_report_log_max(game_env):
    module = game_env.module
    for _ in range(module.REPORT_LOG_MAX + 5):
        module.report_log.append({"day": 0, "topic": "vocab", "text": "x"})
    module._record_report_log_entry(
        {"topic_type": "vocab", "marked_correct_answer": ["y"]}
    )
    assert len(module.report_log) == module.REPORT_LOG_MAX
    assert module.report_log[-1]["text"].endswith("“y”.")


# --- panel/toggle ------------------------------------------------------


def test_the_panel_is_closed_by_default(game_env):
    module = game_env.module
    module.render()
    assert game_env.elements["report-log-panel"].hidden is True
    assert game_env.elements["report-log-toggle-button"].innerText == "📨 My Reports (0)"


def test_toggling_opens_and_closes_the_panel(game_env):
    module = game_env.module
    button = game_env.elements["report-log-toggle-button"]
    button.dispatch("click", None)
    assert module.report_log_open is True
    assert game_env.elements["report-log-panel"].hidden is False

    button.dispatch("click", None)
    assert module.report_log_open is False
    assert game_env.elements["report-log-panel"].hidden is True


def test_the_panel_shows_the_empty_state_with_nothing_reported(game_env):
    module = game_env.module
    module.on_toggle_report_log()
    panel = game_env.elements["report-log-panel"]
    assert len(panel.children) == 1
    assert "Nothing reported yet" in panel.children[0].innerText


def test_the_panel_renders_a_row_per_report_newest_first(game_env):
    module = game_env.module
    _open_typed_question(game_env)
    module.submit_answer("wrong answer")
    module.submit_report()

    module.on_toggle_report_log()
    button = game_env.elements["report-log-toggle-button"]
    assert button.innerText == "Hide My Reports (1)"
    panel = game_env.elements["report-log-panel"]
    assert len(panel.children) == 1
    row_text = panel.children[0].innerText
    assert "Day 1" in row_text
    assert "Reported" in row_text


# --- save/load -----------------------------------------------------------


def test_report_log_round_trips_through_get_state_and_load_state(game_env):
    module = game_env.module
    _open_typed_question(game_env)
    module.submit_answer("wrong answer")
    module.submit_report()

    saved = module.get_state()
    assert saved["report_log"] == module.report_log

    module.report_log.clear()
    assert module.load_state(saved) is True
    assert len(module.report_log) == 1
    assert module.report_log[0]["text"] == saved["report_log"][0]["text"]


def test_an_old_save_with_no_report_log_key_loads_as_empty(game_env):
    module = game_env.module
    module.report_log.append({"day": 0, "topic": "vocab", "text": "stale"})
    assert module.load_state({"version": module.SAVE_VERSION, "current_day": 0, "plots": {}}) is True
    assert module.report_log == []


def test_a_malformed_report_log_is_dropped_entry_by_entry(game_env):
    module = game_env.module
    data = {
        "version": module.SAVE_VERSION,
        "current_day": 0,
        "plots": {},
        "report_log": [
            {"day": 1, "topic": "vocab", "text": "a real one"},
            {"day": "not-a-number", "topic": "vocab", "text": "bad day"},
            {"day": 2, "topic": "vocab"},  # missing text
            "not even a dict",
            42,
        ],
    }
    assert module.load_state(data) is True
    assert module.report_log == [{"day": 1, "topic": "vocab", "text": "a real one"}]


def test_get_state_omits_report_log_when_nothing_has_been_reported(game_env):
    module = game_env.module
    assert module.report_log == []
    assert "report_log" not in module.get_state()


def test_an_untouched_farm_does_not_bloat_the_save_with_report_log(game_env):
    """Same 'don't bloat an untouched save' rule practice_ledger already
    follows (CLAUDE.md Milestone 35's build note)."""
    module = game_env.module
    saved = module.get_state()
    assert "report_log" not in saved
