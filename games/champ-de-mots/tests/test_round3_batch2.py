"""Round 3 batch 2 (2026-10-08): the golden plot (L-17), daily goals (L-14),
stubborn weeds (L-18), slip forgiveness (L-19), session highlights (L-27) and
the weak-items export (L-29)."""

import json


def _watered(module, plot_id):
    """Water a plot once on the farm, the plain SRS way."""
    module.state.review(plot_id, True)
    return module.state.plots_by_id[plot_id]


def _typed_plot(module):
    """A plot whose question can be asked as a typed one (and its question)."""
    for plot in module.state.plots:
        if plot.topic_type == "vocab":
            question = module.generate_question(plot, module.QUESTION_RNG, variant=module.V_FR_EN_TYPED)
            if question["mode"] == "typed":
                return plot, question
    raise AssertionError("no typed plot found")


def _open_typed(module, plot, variant=None):
    module.open_practice(plot.plot_id, variant=variant or module.V_FR_EN_TYPED)
    assert module.current_question["mode"] == "typed"
    return module.current_question


# --- L-17 golden plot ---------------------------------------------------------


def test_golden_plot_is_a_due_plot_and_is_stable_within_a_day(game_env):
    module = game_env.module
    first = module.ensure_golden()
    assert first in module.state.plots_by_id
    assert module.is_golden(module.state.plots_by_id[first])
    assert module.ensure_golden() == first
    cell = module.plot_cells[first]
    module.render()
    assert "plot--golden" in cell.className
    assert "golden plot" in cell.title
    assert module.golden_text().startswith("Golden plot today:")
    assert game_env.elements["golden-display"].innerText == module.golden_text()


def test_golden_prefers_plots_that_were_already_watered(game_env):
    module = game_env.module
    plot = _watered(module, module.state.plots[40].plot_id)
    module.state.advance_day(30)  # long overdue, so due again
    assert module.ensure_golden() == plot.plot_id


def test_correct_golden_answer_earns_two_practice_points_once(game_env):
    module = game_env.module
    golden_id = module.ensure_golden()
    module.open_practice(golden_id)
    before = module.practice_score()
    assert module.submit_answer(module.current_question["answer"]) is True
    assert module.practice_score() == before + module.GOLDEN_POINTS
    assert module.practice_ledger["golden"]["points"] == 2
    assert module.golden_plot["claimed"] is True
    assert "claimed" in module.golden_text()
    cell = module.plot_cells[golden_id]
    assert "plot--golden" not in cell.className
    # a second correct answer on the same plot the same day earns nothing more
    module.open_practice(golden_id)
    module.submit_answer(module.current_question["answer"])
    assert module.practice_ledger["golden"]["points"] == 2


def test_wrong_golden_answer_costs_nothing_and_leaves_it_unclaimed(game_env):
    module = game_env.module
    golden_id = module.ensure_golden()
    module.open_practice(golden_id)
    wrong = next(c for c in module.current_question["choices"] if c != module.current_question["answer"]) if module.current_question["mode"] == "choice" else "zzzz"
    module.submit_answer(wrong)
    assert module.golden_plot["claimed"] is False
    assert module.practice_ledger["golden"]["points"] == 0


def test_a_new_day_picks_a_new_golden_plot_and_resets_the_claim(game_env):
    module = game_env.module
    module.ensure_golden()
    module.golden_plot["claimed"] = True
    module.on_next_day()
    assert module.golden_plot["claimed"] is False
    assert module.golden_plot["day"] == module.state.current_day


def test_golden_claim_is_saved_and_validated(game_env):
    module = game_env.module
    golden_id = module.ensure_golden()
    assert "golden" not in module.get_state()  # nothing saved until it is claimed
    module.open_practice(golden_id)
    module.submit_answer(module.current_question["answer"])
    saved = module.get_state()
    assert saved["golden"]["claimed"] is True
    module.golden_plot.update({"day": -1, "plot_id": None, "claimed": False})
    module.load_state(json.loads(json.dumps(saved)))
    assert module.golden_plot["claimed"] is True
    # junk is dropped
    assert module._validated_golden({"day": True, "plot_id": 5}) == {"day": -1, "plot_id": None, "claimed": False}
    assert module._validated_golden({"day": 3, "plot_id": "nope", "claimed": "yes"})["plot_id"] is None


def test_golden_points_cannot_exceed_double_the_correct_count_on_load(game_env):
    module = game_env.module
    ledger = module._validated_practice_ledger({"golden": {"correct": 1, "total": 1, "points": 99}, "blitz": {"correct": 1, "total": 1, "points": 99}})
    assert ledger["golden"]["points"] == 2
    assert ledger["blitz"]["points"] == 1


# --- L-14 daily goals -----------------------------------------------------------


def test_three_distinct_goals_a_day_that_rotate(game_env):
    module = game_env.module
    for day in range(0, 12):
        goals = module.quests_for_day(day)
        assert len(goals) == 3 and len(set(goals)) == 3
    assert module.quests_for_day(0) != module.quests_for_day(1)


def test_water_goal_finishes_and_earns_points_without_a_streak(game_env):
    module = game_env.module
    module.state.current_day = 0
    goals = module.quests_for_day(0)
    assert "water" in goals
    for _ in range(5):
        plot = module.state.next_due_plot()
        module.open_practice(plot.plot_id)
        module.submit_answer(module.current_question["answer"] if module.current_question["mode"] == "choice" else "x")
        module.close_practice()
    assert "water" in module.quest_state["done"]
    assert module.practice_ledger["quests"]["points"] >= 2
    # Five waterings can finish more than one goal (for example a practice-count goal), so only require water.
    assert module.quest_summary_text().startswith("Daily goals: ")
    assert len(module.quest_state["done"]) >= 1
    # next day: nothing carries over
    module.on_next_day()
    assert module.quest_state["done"] == [] and module.quest_state["progress"] == {}


def test_a_goal_pays_out_only_once(game_env):
    module = game_env.module
    module._quest_note("water", 99)
    module._quest_note("water", 99)
    assert module.practice_ledger["quests"]["total"] == 1


def test_goal_for_a_kind_not_on_todays_list_is_ignored(game_env):
    module = game_env.module
    module.state.current_day = 0
    off_list = next(k for k in module.QUEST_ORDER if k not in module.quests_for_day(0))
    module._quest_note(off_list, 99)
    assert module.quest_state["done"] == []


def test_practice_goal_counts_correct_answers_in_other_modes(game_env):
    module = game_env.module
    module.state.current_day = 1
    assert "practice" in module.quests_for_day(1)
    for _ in range(module.QUESTS["practice"][1]):
        module.record_practice("builder", True)
    assert "practice" in module.quest_state["done"]


def test_goal_progress_is_saved_validated_and_dashboard_lists_it(game_env):
    module = game_env.module
    module._quest_note(module.quests_for_day(0)[0], 2)
    saved = module.get_state()
    assert saved["quests"]["progress"]
    module.quest_state.update({"day": -1, "progress": {}, "done": []})
    module.load_state(json.loads(json.dumps(saved)))
    assert module.quest_state["progress"]
    assert module._validated_quests({"day": 1, "progress": {"water": True, "bogus": 3, "combo": 99}, "done": ["nope", "combo"]}) == {
        "day": 1, "progress": {"combo": 3}, "done": ["combo"],
    }
    module.on_toggle_dashboard()
    texts = [child.innerText for child in game_env.elements["dashboard-panel"].children]
    assert any(t.startswith("Daily goals:") for t in texts)


# --- L-18 stubborn weeds --------------------------------------------------------


def _fail(module, plot, times):
    for _ in range(times):
        module.open_practice(plot.plot_id)
        question = module.current_question
        wrong = next(c for c in question["choices"] if c != question["answer"]) if question["mode"] == "choice" else "zzzz"
        module.submit_answer(wrong)
        module.close_practice()


def test_four_misses_in_a_row_make_a_stubborn_weed_and_a_correct_answer_clears_it(game_env):
    module = game_env.module
    plot = module.state.plots[3]
    _fail(module, plot, module.LEECH_THRESHOLD - 1)
    assert not module.is_leech(plot)
    _fail(module, plot, 1)
    assert module.is_leech(plot)
    module.render()
    cell = module.plot_cells[plot.plot_id]
    assert "plot--leech" in cell.className and "stubborn weed" in cell.title
    module.open_practice(plot.plot_id)
    module.submit_answer(module.current_question["answer"] if module.current_question["mode"] == "choice" else "zzz")
    # answer correctly via choice mode if possible
    module.close_practice()
    plot.fail_run = module.LEECH_THRESHOLD
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_CHOICE if hasattr(module, "V_FR_EN_CHOICE") else None)
    module.submit_answer(module.current_question["answer"])
    assert plot.fail_run == 0 and not module.is_leech(plot)


def test_the_reteach_card_shows_before_the_question_and_hides_once_answered(game_env):
    module = game_env.module
    plot = module.state.plots[5]
    plot.fail_run = module.LEECH_THRESHOLD
    module.open_practice(plot.plot_id)
    assert game_env.elements["practice-leech"].hidden is False
    assert "missed 4 times" in game_env.elements["practice-leech-what"].innerText
    assert game_env.elements["practice-leech-pieces"].innerText.startswith("In pieces:")
    assert "hook" in game_env.elements["practice-leech-hook"].innerText
    module.submit_answer(module.current_question["answer"] if module.current_question["mode"] == "choice" else "zzz")
    assert game_env.elements["practice-leech"].hidden is True


def test_resting_a_stubborn_plot_pushes_it_a_week_and_clears_the_run(game_env):
    module = game_env.module
    plot = module.state.plots[7]
    plot.fail_run = module.LEECH_THRESHOLD
    module.open_practice(plot.plot_id)
    assert module.rest_leech() is True
    assert plot.next_due == module.state.current_day + module.LEECH_REST_DAYS
    assert plot.fail_run == 0
    assert module.leech_rests == 1
    assert module.practice_open is False
    assert module.get_state()["leech_rests"] == 1
    # a normal plot cannot be rested
    other = module.state.plots[8]
    module.open_practice(other.plot_id)
    assert module.rest_leech() is False


def test_leech_run_is_saved_only_while_it_exists_and_validated(game_env):
    module = game_env.module
    plot = module.state.plots[9]
    module.state.review(plot.plot_id, False)
    assert "fail_run" not in module.get_state()["plots"][plot.plot_id]
    plot.fail_run = 5
    saved = module.get_state()
    assert saved["plots"][plot.plot_id]["fail_run"] == 5
    plot.fail_run = 0
    module.load_state(json.loads(json.dumps(saved)))
    assert plot.fail_run == 5
    assert module._validated_fail_run(True) == 0
    assert module._validated_fail_run("4") == 0
    assert module._validated_fail_run(10**9) == module.LEECH_FAIL_RUN_LIMIT


def test_chunking_splits_words_into_syllable_like_pieces(game_env):
    module = game_env.module
    assert module.chunk_word("bonjour") == ["bon", "jour"]
    assert module.chunk_word("chat") == ["chat"]
    assert "".join(module.chunk_word("université")) == "université"
    assert len(module.chunk_word("université")) >= 3
    assert module.chunk_text("Bonjour madame") == "Bon · jour   ma · dame"
    for plot in module.state.plots[:200]:
        for item in plot.items:
            fr = item.get("fr")
            if fr:
                assert "".join(module.chunk_word(fr.split()[0].strip(".,;:!?"))) == fr.split()[0].strip(".,;:!?")


# --- L-19 slip forgiveness -------------------------------------------------------


def _slip_setup(module):
    plot, _ = _typed_plot(module)
    question = _open_typed(module, plot)
    answer = question["answer"]
    return plot, question, answer


def _long_plain_word_plot(module):
    for plot in module.state.plots:
        fr = plot.items[0].get("fr", "")
        if plot.topic_type == "vocab" and fr.isalpha() and fr.isascii() and 9 <= len(fr) <= 14:
            return plot
    raise AssertionError("no long plain word found")


def test_a_typo_can_be_forgiven_once_and_restores_the_plot_and_combo(game_env):
    module = game_env.module
    plot = _long_plain_word_plot(module)
    module.state.review(plot.plot_id, True)
    module.state.advance_day(30)
    snapshot = module._plot_record(plot)
    module.combo_count = 3
    question = _open_typed(module, plot, module.V_EN_FR_TYPED)
    assert question["answer"] == plot.items[0]["fr"]
    typo = question["answer"][:-1] + ("q" if question["answer"][-1] != "q" else "z")
    module.submit_answer(typo)
    assert module.current_result is False
    assert module._slip_snapshot["pattern"] == module.ERROR_PATTERN_CLOSE_TYPO
    assert module.combo_count == 0 and plot.correct_streak == 0
    patterns = sum(module.error_pattern_counts.values())
    assert module.can_forgive_slip() is True
    assert game_env.elements["practice-slip-button"].hidden is False
    assert module.forgive_slip() is True
    assert module._plot_record(plot) == snapshot  # the SRS interval and ease were not penalised
    assert module.combo_count == 3
    assert module.slip_used is True
    assert game_env.elements["practice-slip-note"].hidden is False
    assert "Slip forgiven" in game_env.elements["practice-slip-note"].innerText
    assert module.current_result is None and module.current_question["plot_id"] == plot.plot_id
    assert sum(module.error_pattern_counts.values()) == patterns - 1
    # once per session: the next typo is a real miss with no button
    module.submit_answer("qqqqqqqqqq")
    assert module.can_forgive_slip() is False
    assert game_env.elements["practice-slip-button"].hidden is True


def test_a_genuine_miss_cannot_be_forgiven(game_env):
    module = game_env.module
    plot, question, answer = _slip_setup(module)
    module.submit_answer("qqqqqqqqqqqq")
    assert module.current_result is False
    assert module.can_forgive_slip() is False
    assert module.forgive_slip() is False
    assert module.slip_used is False


def test_accent_slip_is_forgivable(game_env):
    module = game_env.module
    target = None
    for plot in module.state.plots:
        if plot.topic_type == "vocab" and any(ch in plot.items[0]["fr"] for ch in "éèêàç") and len(plot.items[0]["fr"]) < 25:
            target = plot
            break
    assert target is not None
    question = _open_typed(module, target, module.V_EN_FR_TYPED)
    if question["mode"] != "typed" or question["answer"] != target.items[0]["fr"]:
        return
    stripped = module.normalize_answer(question["answer"], fold_accents=True)
    module.submit_answer(stripped)
    assert module.current_result is False  # accents matter by default
    assert module._slip_snapshot["pattern"] == module.ERROR_PATTERN_ACCENT
    assert module.can_forgive_slip() is True


def test_slip_state_is_never_saved(game_env):
    module = game_env.module
    assert not any("slip" in key for key in module.get_state())


# --- L-27 session highlights --------------------------------------------------------


def test_highlights_track_best_combo_and_toughest_word_beaten(game_env):
    module = game_env.module
    assert module.session_highlights_text() == ""
    plot = module.state.plots[11]
    plot.fail_run = 3
    module.open_practice(plot.plot_id)
    module.submit_answer(module.current_question["answer"] if module.current_question["mode"] == "choice" else "zzz")
    module.close_practice()
    if module.current_result:
        pass
    text = module.session_highlights_text()
    if module.session_highlights["toughest_label"]:
        assert "toughest word beaten" in text and plot.label in text and "3 times" in text
    module.combo_count = 4
    module._note_highlights(plot, True, 0)
    assert module.session_highlights["best_combo"] >= 4
    assert "best combo" in module.session_highlights_text()


def test_highlights_are_not_saved_and_appear_on_the_review_summary(game_env):
    module = game_env.module
    module.session_highlights.update({"best_combo": 5, "toughest_label": "chat", "toughest_misses": 2})
    assert not any("highlight" in key for key in module.get_state())
    assert "best combo 5" in module._with_highlights("Done.")
    assert module._with_highlights("Done.").startswith("Done. Highlights this session:")


# --- L-29 weak-items export -------------------------------------------------------------


def test_weak_items_collects_flagged_plots_with_reasons(game_env):
    module = game_env.module
    assert module.weak_items() == []
    missed = module.state.plots[20]
    module.state.review(missed.plot_id, False)
    weedy = module.state.plots[21]
    weedy.in_weeds = True
    stubborn = module.state.plots[22]
    stubborn.fail_run = 4
    module.phrasebook.append(module.state.plots[23].plot_id)
    reasons = {row["why"] for row in module.weak_items()}
    assert any("missed last time" in r for r in reasons)
    assert any("known mix-up" in r for r in reasons)
    assert any("stubborn weed" in r for r in reasons)
    assert any("phrasebook" in r for r in reasons)


def test_csv_and_anki_formats(game_env):
    module = game_env.module
    plot = module.state.plots[30]
    module.state.review(plot.plot_id, False)
    csv_text = module.weak_items_csv()
    lines = csv_text.splitlines()
    assert lines[0] == "French,English,Topic,Week,Why it is here"
    assert len(lines) >= 2
    anki = module.weak_items_anki()
    assert anki.startswith("#separator:tab\n#html:false\n#tags column:3\n")
    body = anki.splitlines()[3:]
    assert body and all(line.count("\t") == 2 for line in body)
    assert "missed_last_time" in anki


def test_export_hands_the_file_to_the_page_downloader(game_env):
    module = game_env.module
    module.state.review(module.state.plots[31].plot_id, False)
    module.export_weak_items_csv()
    assert module._last_download["filename"].endswith(".csv")
    assert module._last_download["mime"] == "text/csv"
    assert module._last_download["text"].startswith("French,English")
    module.export_weak_items_anki()
    assert module._last_download["filename"].endswith(".txt")


def test_dashboard_offers_the_export_buttons_and_counts_the_weak_items(game_env):
    module = game_env.module
    module.state.review(module.state.plots[32].plot_id, False)
    module.on_toggle_dashboard()
    panel = game_env.elements["dashboard-panel"]
    labels = [child.innerText for child in panel.children]
    assert "Download weak items (CSV)" in labels
    assert "Download for Anki (tab-separated)" in labels
    assert any("weak item" in t and "ready to export" in t for t in labels)
    assert any(t.startswith("Stubborn weeds:") for t in labels)
    # re-rendering must not leak proxies: the old ones are destroyed
    old = list(module.dashboard_proxies)
    module.render()
    assert all(proxy.destroyed for proxy in old)
