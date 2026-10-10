"""Water options (2026-10-08): the chooser beside "Water the next plot", each
option's live count, and the review-panel sessions it starts. Every option
uses the one watering rule."""


def _open(game_env):
    game_env.elements["water-options-toggle-button"].dispatch("click", None)


def _answer_all(module):
    """Answer the open Review session correctly to the end."""
    while module.review_question is not None:
        module.submit_review_answer(module.review_question["answer"])
        module.next_review_question()


# --- the panel -----------------------------------------------------------------------------------


def test_the_chooser_opens_and_closes_from_its_button(game_env):
    panel = game_env.elements["water-options-panel"]
    assert panel.hidden is True
    _open(game_env)
    assert panel.hidden is False
    assert game_env.elements["water-options-toggle-button"].innerText == "Close water options"
    game_env.elements["water-options-close-button"].dispatch("click", None)
    assert panel.hidden is True
    assert game_env.elements["water-options-toggle-button"].innerText == "🚿 Water options"


def test_every_option_shows_how_many_plots_it_can_water_right_now(game_env):
    module = game_env.module
    _open(game_env)
    counts = module.water_option_counts()
    assert set(counts) == {"next", "row", "topic", "wilting", "mc", "typed", "listen"}
    for key in ("next", "row", "topic", "wilting", "mc", "typed"):
        text = game_env.elements[f"water-opt-{key}-count"].innerText
        assert text.endswith("can be watered now"), (key, text)
        assert str(counts[key]) in text
    assert game_env.elements["water-opt-wilting-button"].disabled is True  # nothing wilting on a new farm
    assert counts["wilting"] == 0
    assert game_env.elements["water-opt-mc-button"].disabled is False
    assert counts["mc"] == len(module.state.plots)
    assert counts["next"] == len(module.state.due_plots())


def test_counts_drop_as_plots_are_watered_today(game_env):
    module, state = game_env.module, game_env.state
    before = module.water_option_counts()
    for plot in state.row_plots(1)[:5]:
        module.water_plot(plot)
    after = module.water_option_counts()
    assert after["row"] == before["row"] - 5  # row 1 is the default choice
    assert after["mc"] == before["mc"] - 5
    state.advance_day(1)
    assert module.water_option_counts()["mc"] >= after["mc"]  # a new day: plots can be watered again


def test_the_listening_option_needs_speech_and_says_so(game_env):
    module = game_env.module
    _open(game_env)
    assert module.water_option_counts()["listen"] == 0
    assert "speech synthesis" in game_env.elements["water-opt-listen-count"].innerText
    assert game_env.elements["water-opt-listen-button"].disabled is True


def test_the_row_and_topic_selects_are_filled_and_change_the_counts(game_env):
    module = game_env.module
    row_select = game_env.elements["water-row-select"]
    assert len(row_select.children) == len(module.state.rows)
    topic_select = game_env.elements["water-topic-select"]
    assert [c.value for c in topic_select.children] == ["vocab", "phrase", "grammar", "pronunciation"]
    row_select.value = "7"
    row_select.dispatch("change", None)
    assert module.water_row_choice == 7
    assert module.water_option_counts()["row"] == len(module.state.row_plots(7))
    topic_select.value = "pronunciation"
    topic_select.dispatch("change", None)
    assert module.water_topic_choice == "pronunciation"
    phonetic = [p for p in module.state.plots if p.topic_type == "phonetic"]
    assert module.water_option_counts()["topic"] == len(phonetic)


def test_the_minigame_list_names_every_game_and_which_plots_it_waters(game_env):
    module = game_env.module
    _open(game_env)
    rows = module.minigames.water_game_rows()
    assert [r["key"] for r in rows] == [
        "blitz", "racer", "boutique", "cafe", "sprint", "pairs", "gaps", "listenpick", "wordorder",
    ]
    for row in rows:
        assert row["available"] and row["count"] > 0 and row["note"], row
    box = game_env.elements["water-games-list"]
    assert len(box.children) == 9
    labels = [line.children[0].innerText for line in box.children]
    assert all(" — waters " in label for label in labels)
    assert "Word Match" in labels[5] and "weeks 12-23" in labels[5]


def test_playing_a_game_from_the_chooser_opens_it_and_closes_the_chooser(game_env):
    module = game_env.module
    _open(game_env)
    box = game_env.elements["water-games-list"]
    pairs_line = box.children[5]
    pairs_line.children[2].dispatch("click", None)
    assert module.minigames.PAIRS.open is True
    assert game_env.elements["pairs-panel"].hidden is False
    assert game_env.elements["water-options-panel"].hidden is True


def test_water_next_plot_starts_the_farms_own_question(game_env):
    module = game_env.module
    _open(game_env)
    game_env.elements["water-opt-next-button"].dispatch("click", None)
    assert module.practice_open is True and module.current_question is not None
    assert game_env.elements["water-options-panel"].hidden is True


# --- the sessions ----------------------------------------------------------------------------------


def test_a_week_session_asks_only_about_that_week_up_to_ten_plots(game_env):
    module, state = game_env.module, game_env.state
    game_env.elements["water-row-select"].value = "9"
    game_env.elements["water-row-select"].dispatch("change", None)
    game_env.elements["water-opt-row-button"].dispatch("click", None)
    assert module.review_mode == module.WATER_ROW_MODE
    assert len(module.review_queue) == module.WATER_SESSION_MAX
    queue = list(module.review_queue)
    assert {state.plots_by_id[p].sequence for p in queue} == {9}
    assert game_env.elements["water-options-panel"].hidden is True
    _answer_all(module)
    assert "watered 10 plots" in game_env.elements["review-summary"].innerText
    # the le/la questions in this week are counted by the gender drill's own ledger line
    assert module.practice_ledger["wateropts"]["total"] + module.practice_ledger["gender"]["total"] == 10
    assert all(state.plots_by_id[p].stage == module.STAGE_SPROUT for p in queue)


def test_a_topic_session_only_asks_that_type(game_env):
    module, state = game_env.module, game_env.state
    for key, expect in (("grammar", {"grammar"}), ("phrase", {"phrase"}), ("pronunciation", {"phonetic"}), ("vocab", {"vocab"})):
        game_env.elements["water-topic-select"].value = key
        game_env.elements["water-topic-select"].dispatch("change", None)
        module.start_water_session(module.WATER_TOPIC_MODE, key)
        assert module.review_queue
        assert {state.plots_by_id[p].topic_type for p in module.review_queue} == expect
        module.close_review()


def test_a_session_skips_plots_already_watered_today(game_env):
    module, state = game_env.module, game_env.state
    row = state.row_plots(3)
    for plot in row[:-2]:
        module.water_plot(plot)
    module.start_water_session(module.WATER_ROW_MODE, 3)
    assert set(module.review_queue) == {p.plot_id for p in row[-2:]}


def test_a_session_with_nothing_left_says_so_kindly(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.row_plots(3):
        module.water_plot(plot)
    assert module.start_water_session(module.WATER_ROW_MODE, 3) == 0
    message = game_env.elements["review-empty-message"]
    assert not message.hidden and "already been watered today" in message.innerText


def test_wilting_first_orders_the_most_overdue_plot_first(game_env):
    module, state = game_env.module, game_env.state
    a, b, c = state.plots[0], state.plots[1], state.plots[2]
    for plot in (a, b, c):
        state.review(plot.plot_id, True)
    state.advance_day(60)
    a.next_due, b.next_due, c.next_due = 30, 10, 20  # all overdue, b the longest
    assert module.is_wilting(a, state.current_day)
    queue = module.water_session_plots(module.WATER_WILTING_MODE)
    assert [p.plot_id for p in queue] == [b.plot_id, c.plot_id, a.plot_id]
    assert module.water_option_counts()["wilting"] == 3
    module.start_water_session(module.WATER_WILTING_MODE)
    assert module.review_queue[0] == b.plot_id


def test_quick_multiple_choice_is_five_plots_all_multiple_choice(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.plots[:30]:  # grown plots would normally be asked as typed
        plot.stage, plot.last_reviewed, plot.correct_streak = module.STAGE_AUTOMATED, 0, 5
        plot.next_due = 1
    state.advance_day(5)
    module.wants_typed = lambda p: True
    assert module.start_water_session(module.WATER_MC_MODE) == module.WATER_QUICK_COUNT
    seen = 0
    while module.review_question is not None:
        assert module.review_question["mode"] == "choice"
        module.submit_review_answer(module.review_question["answer"])
        module.next_review_question()
        seen += 1
    assert seen == 5


def test_typing_water_is_five_plots_all_typed(game_env):
    module = game_env.module
    assert module.start_water_session(module.WATER_TYPED_MODE) == module.WATER_QUICK_COUNT
    seen = 0
    while module.review_question is not None:
        assert module.review_question["mode"] == "typed"
        assert module.submit_review_answer(module.review_question["answer"]) is True
        module.next_review_question()
        seen += 1
    assert seen == 5
    assert game_env.elements["accent-bar-review"] is not None
    assert "watered 5 plots" in game_env.elements["review-summary"].innerText


def test_listening_water_speaks_and_hides_the_text_until_asked(game_env, monkeypatch):
    module = game_env.module
    spoken = []
    monkeypatch.setattr(module, "speech_available", lambda: True)
    monkeypatch.setattr(module, "speak_french", lambda text, slow=False: spoken.append((text, slow)) or True)
    assert module.water_option_counts()["listen"] > 0
    assert module.start_water_session(module.WATER_LISTEN_MODE) == module.WATER_QUICK_COUNT
    question = module.review_question
    assert question["mode"] == "choice" and question["variant"] in module.WATER_LISTEN_VARIANTS
    assert spoken == [(question["prompt"], False)]
    assert game_env.elements["review-prompt"].innerText == module.LISTEN_HIDDEN_PROMPT
    assert game_env.elements["review-listen-button"].hidden is False
    assert game_env.elements["review-listen-show-button"].hidden is False
    game_env.elements["review-listen-button"].dispatch("click", None)
    assert len(spoken) == 2
    game_env.elements["review-listen-show-button"].dispatch("click", None)
    assert game_env.elements["review-prompt"].innerText == question["prompt"]
    assert game_env.elements["review-listen-show-button"].hidden is True
    module.submit_review_answer(question["answer"])
    assert game_env.elements["review-prompt"].innerText == question["prompt"]
    module.next_review_question()
    assert game_env.elements["review-prompt"].innerText == module.LISTEN_HIDDEN_PROMPT  # hidden again


def test_a_wrong_answer_in_a_chooser_session_changes_nothing(game_env):
    module, state = game_env.module, game_env.state
    module.start_water_session(module.WATER_MC_MODE)
    question = module.review_question
    plot = state.plots_by_id[question["plot_id"]]
    before = (plot.stage, plot.interval_days, plot.last_reviewed, plot.correct_streak, plot.last_watered)
    wrong = next(c for c in question["choices"] if c != question["answer"])
    module.submit_review_answer(wrong)
    assert (plot.stage, plot.interval_days, plot.last_reviewed, plot.correct_streak, plot.last_watered) == before
    assert module.practice_ledger["wateropts"]["total"] == 1 and module.practice_ledger["wateropts"]["points"] == 0


def test_chooser_answers_feed_the_practice_ledger_and_the_score(game_env):
    module = game_env.module
    module.start_water_session(module.WATER_MC_MODE)
    _answer_all(module)
    entry = module.practice_ledger["wateropts"]
    assert entry["correct"] == 5 and entry["points"] == 5
    assert module.practice_score() == 5
    assert "Water options" in module.PRACTICE_MODES["wateropts"]


def test_both_pages_carry_every_chooser_id():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    ids = [
        "water-options-toggle-button", "water-options-panel", "water-today-line", "water-row-select", "water-topic-select",
        "water-games-list", "water-options-close-button", "review-listen-button", "review-listen-show-button",
        "review-water-note", "practice-water-note",
    ] + [f"water-opt-{k}-{p}" for k in ("next", "row", "topic", "wilting", "mc", "typed", "listen") for p in ("button", "count")]
    for name in ("index.html", "pc.html"):
        html = (root / name).read_text(encoding="utf-8")
        for element_id in ids:
            assert f'id="{element_id}"' in html, (name, element_id)
    pc = (root / "pc-config.json").read_text(encoding="utf-8")
    assert "water-options-panel" in pc
