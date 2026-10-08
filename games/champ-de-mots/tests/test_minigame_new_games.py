"""The four new arcade games (2026-10-08): Word Match, Grammar Gaps, Listening
Pick and Word Order Race. Each waters real plots, names them under every
question, feeds the practice ledger, has a difficulty setting and is gated by
row unlocking like the first five."""

import pytest

NEW = ("pairs", "gaps", "listenpick", "wordorder")


def _game(module, key):
    return {g.key: g for g in module.minigames.NEW_GAMES}[key]


def _flush(module):
    """Reset the per-game credit tallies the way a fresh run does."""
    for key in NEW:
        module.reset_growth_credit(key)


# --- shared frame ------------------------------------------------------------------------------


@pytest.mark.parametrize("key", NEW)
def test_the_toggle_opens_and_closes_the_panel_and_start_runs_a_round(game_env, key):
    module = game_env.module
    game = _game(module, key)
    panel = game_env.elements[f"{key}-panel"]
    assert panel.hidden is True
    game_env.elements[f"{key}-toggle-button"].dispatch("click", None)
    assert panel.hidden is False and game.open
    assert game_env.elements[f"{key}-toggle-button"].innerText == game.close_label
    game_env.elements[f"{key}-start-button"].dispatch("click", None)
    assert game.active and game.round is not None
    assert game_env.elements[f"{key}-start-button"].hidden is True
    game_env.elements[f"{key}-close-button"].dispatch("click", None)
    assert panel.hidden is True and not game.active


@pytest.mark.parametrize("key", NEW)
def test_every_round_names_the_plots_it_waters(game_env, key):
    module = game_env.module
    game = _game(module, key)
    game.start()
    text = game_env.elements[f"{key}-waters"].innerText
    assert text.startswith("Waters: ") and len(text) > len("Waters: ")
    for label in game.waters_labels():
        assert label in text
    assert game_env.elements[f"growth-marker-{key}"].innerText == "Grows plots: waters, then nudges"


@pytest.mark.parametrize("key", NEW)
def test_each_game_is_in_the_ledger_and_registered(game_env, key):
    module = game_env.module
    assert key in module.PRACTICE_MODES and key in module.practice_ledger
    assert key in module.GROWTH_SURFACES
    assert any(entry[0] == key for entry in module.minigames.WATER_GAMES)
    assert callable(getattr(module, f"{key}_tick"))


@pytest.mark.parametrize("key", NEW)
def test_the_tick_is_a_no_op_while_idle(game_env, key):
    module = game_env.module
    assert getattr(module, f"{key}_tick")() is None


@pytest.mark.parametrize("key", NEW)
def test_the_game_is_gated_by_row_unlocking_like_the_others(game_env, key):
    module = game_env.module
    game = _game(module, key)
    assert game.available()
    module.state.is_row_unlocked = lambda sequence: sequence < game.lo
    game._pool = None
    module.render()
    if game.lo > 1:
        assert not game.available()
        assert game_env.elements[f"{key}-toggle-button"].disabled is True
        assert game.start() is None
    else:  # the whole farm is its range: with everything locked there is nothing to play
        module.state.is_row_unlocked = lambda sequence: False
        game._pool = None
        assert game.start() is None


# --- Word Match ---------------------------------------------------------------------------------


def test_word_match_pool_is_vocab_and_phrase_plots_from_weeks_12_to_23(game_env):
    module = game_env.module
    pool = _game(module, "pairs").pool()
    assert pool and all(p.topic_type in ("vocab", "phrase") for p in pool)
    assert all(12 <= p.sequence <= 23 for p in pool)
    strip = module.minigames._strip_parens
    assert all(len(strip(p.items[0]["fr"])) <= 22 and "/" not in p.items[0]["fr"] for p in pool)


def test_word_match_board_has_four_distinct_pairs(game_env):
    module = game_env.module
    game = _game(module, "pairs")
    for _ in range(8):
        game.start()
        cards = game.round["cards"]
        assert len(cards) == 8
        assert len({c["plot_id"] for c in cards}) == 4
        assert sorted(c["side"] for c in cards) == ["en"] * 4 + ["fr"] * 4
        assert len({c["text"].lower() for c in cards if c["side"] == "fr"}) == 4
        game.close()


def _match_all(game):
    by_plot = {}
    for card in game.round["cards"]:
        by_plot.setdefault(card["plot_id"], []).append(card)
    results = []
    for plot_id, (first, second) in by_plot.items():
        results.append(game.select(first["id"]))
        results.append(game.select(second["id"]))
    return results


def test_word_match_each_right_pair_waters_its_plot_and_three_boards_clear_the_game(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "pairs")
    game.start()
    watered = set()
    for board in range(3):
        plot_ids = set(game.round["plots"])
        assert len(plot_ids) == 4
        _match_all(game)
        watered |= plot_ids
    assert game.end_reason == "cleared" and not game.active
    assert all(state.plots_by_id[p].stage == module.STAGE_SPROUT for p in watered)
    assert len(watered) >= 8  # distinct plots across a play
    assert module.growth_credit["pairs"]["full"] == len(watered)
    assert module.practice_ledger["pairs"]["correct"] == 12 and module.practice_ledger["pairs"]["points"] == 10  # daily cap
    summary = game_env.elements["pairs-summary"].innerText
    assert "Board cleared" in summary and "Plot growth credited: watered" in summary


def test_word_match_wrong_pair_costs_a_life_and_changes_no_plot(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "pairs")
    game.start()
    lives = game.lives
    cards = game.round["cards"]
    fr = next(c for c in cards if c["side"] == "fr")
    wrong_en = next(c for c in cards if c["side"] == "en" and c["plot_id"] != fr["plot_id"])
    snapshots = {p: (state.plots_by_id[p].stage, state.plots_by_id[p].last_reviewed) for p in game.round["plots"]}
    game.select(fr["id"])
    assert game.select(wrong_en["id"]) is False
    assert game.lives == lives - 1 and game.combo == 0
    assert {p: (state.plots_by_id[p].stage, state.plots_by_id[p].last_reviewed) for p in game.round["plots"]} == snapshots
    assert game_env.elements["pairs-feedback"].innerText.startswith("Not a pair")


def test_word_match_selection_toggles_and_same_side_switches(game_env):
    module = game_env.module
    game = _game(module, "pairs")
    game.start()
    cards = game.round["cards"]
    frs = [c for c in cards if c["side"] == "fr"]
    game.select(frs[0]["id"])
    assert game.selected == frs[0]["id"]
    game.select(frs[1]["id"])
    assert game.selected == frs[1]["id"]
    game.select(frs[1]["id"])
    assert game.selected is None
    assert game.select(999) is None


def test_word_match_runs_out_of_lives_and_out_of_time(game_env):
    module = game_env.module
    game = _game(module, "pairs")
    game.start()
    for _ in range(game.params()["lives"]):
        cards = game.round["cards"]
        fr = next(c for c in cards if c["side"] == "fr")
        wrong_en = next(c for c in cards if c["side"] == "en" and c["plot_id"] != fr["plot_id"])
        game.select(fr["id"])
        game.select(wrong_en["id"])
    assert game.end_reason == "lives" and "Out of lives" in game_env.elements["pairs-summary"].innerText
    game.start()
    for _ in range(game.params()["seconds"]):
        module.pairs_tick()
    assert game.end_reason == "time" and not game.active


def test_word_match_prefers_plots_that_can_still_be_watered_today(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "pairs")
    pool = game.pool()
    for plot in pool[:-20]:
        module.water_plot(plot)
    for _ in range(10):
        game.start()
        assert all(state.plots_by_id[p].last_watered != state.current_day for p in game.round["plots"])
        game.close()


# --- Grammar Gaps ----------------------------------------------------------------------------------


def test_gaps_pool_is_grammar_outside_racer_and_the_passe_compose(game_env):
    module = game_env.module
    mg = module.minigames
    pool = _game(module, "gaps").pool()
    assert pool and all(p.topic_type == "grammar" for p in pool)
    assert not any(mg.RACER_LO <= p.sequence <= mg.RACER_HI for p in pool)
    # the passe compose rules the Sprint can ask are left to it
    sprint = {p.plot_id for p in mg._sprint_candidate_plots()}
    assert not any(p.plot_id in sprint for p in pool)
    assert {p.sequence for p in pool} >= {1, 3, 5, 7, 8, 9, 10, 16, 20, 22}


def test_gaps_asks_a_list_only_rule_as_an_example_translation(game_env):
    module = game_env.module
    game = _game(module, "gaps")
    plot = module.state.plots_by_id["fren152-w12-grammar002"]  # Savoir vs Connaitre: a list of forms
    assert plot in game.pool()
    assert set(game.variants_of(plot)) == {module.V_EXAMPLE_FR_EN, module.V_EXAMPLE_EN_FR}


def test_gaps_correct_answer_waters_and_scores_with_a_combo(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "gaps")
    game.start()
    question = game.round
    assert question["variant"] in module.minigames.GAPS_VARIANTS | module.minigames.GAPS_FALLBACK_VARIANTS
    plot = state.plots_by_id[question["plot_id"]]
    assert game.submit(question["answer"]) is True
    assert plot.stage == module.STAGE_SPROUT and game.score == 10 and game.combo == 1
    assert game_env.elements["gaps-feedback"].innerText.startswith(plot.label)
    assert module.practice_ledger["gaps"]["correct"] == 1


def test_gaps_wrong_answer_costs_a_life_and_changes_nothing(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "gaps")
    game.start()
    question = game.round
    plot = state.plots_by_id[question["plot_id"]]
    wrong = next(c for c in question["choices"] if c != question["answer"])
    assert game.submit(wrong) is False
    assert plot.stage == module.STAGE_SEED and plot.last_reviewed is None
    assert game.lives == game.params()["lives"] - 1 and game.combo == 0


def test_gaps_ends_on_lives_and_on_time_with_the_credit_line(game_env):
    module = game_env.module
    game = _game(module, "gaps")
    game.start()
    while game.active:
        question = game.round
        wrong = next(c for c in question["choices"] if c != question["answer"]) if question["mode"] == "choice" else "zzz"
        game.submit(wrong)
    assert game.end_reason == "lives"
    assert "Out of lives" in game_env.elements["gaps-summary"].innerText
    game.start()
    for _ in range(game.params()["seconds"]):
        module.gaps_tick()
    assert game.end_reason == "time"
    assert "Time's up" in game_env.elements["gaps-summary"].innerText
    assert "Plot growth credited" in game_env.elements["gaps-summary"].innerText


def test_gaps_can_ask_for_a_typed_answer_for_a_grown_plot(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "gaps")
    module.wants_typed = lambda plot: True
    for _ in range(60):
        game.start()
        if game.round["mode"] == "typed":
            break
    question = game.round
    assert question["mode"] == "typed"
    assert game_env.elements["gaps-typed-input"] is not None and game_env.elements["gaps-typed-submit"] is not None
    assert game.submit(question["answer"]) is True


# --- Listening Pick ---------------------------------------------------------------------------------


def test_listening_pick_pool_is_vocab_phrase_and_pronunciation_plots_from_every_week(game_env):
    module = game_env.module
    pool = _game(module, "listenpick").pool()
    assert all(p.topic_type != "grammar" for p in pool)
    assert {p.topic_type for p in pool} == {"vocab", "phrase", "phonetic"}
    assert {p.sequence for p in pool} >= set(range(1, 24)) - {22}  # week 22 is grammar only


def test_listening_pick_speaks_each_question_and_hides_the_text_when_it_can(game_env, monkeypatch):
    module = game_env.module
    spoken = []
    monkeypatch.setattr(module.minigames, "_speech_ok", lambda: True)
    monkeypatch.setattr(module.minigames, "_speak", lambda text, slow=False: spoken.append((text, slow)))
    game = _game(module, "listenpick")
    game.start()
    question = game.round
    assert spoken == [(question["prompt"], False)]
    assert game_env.elements["listenpick-prompt"].innerText == module.minigames.LISTEN_HIDDEN_PROMPT
    assert game_env.elements["listenpick-play-button"].hidden is False
    assert game_env.elements["listenpick-slow-button"].hidden is False
    assert game_env.elements["listenpick-show-button"].hidden is False
    game_env.elements["listenpick-slow-button"].dispatch("click", None)
    assert spoken[-1] == (question["prompt"], True)
    assert question["prompt"] not in game_env.elements["listenpick-waters"].innerText  # no giveaway
    game_env.elements["listenpick-show-button"].dispatch("click", None)
    assert game_env.elements["listenpick-prompt"].innerText == question["prompt"]
    game.submit(question["answer"])
    assert game_env.elements["listenpick-prompt"].innerText == module.minigames.LISTEN_HIDDEN_PROMPT  # hidden again for the next one


def test_listening_pick_shows_the_french_when_the_browser_cannot_speak(game_env):
    module = game_env.module
    game = _game(module, "listenpick")
    game.start()
    assert game_env.elements["listenpick-prompt"].innerText == game.round["prompt"]
    assert game_env.elements["listenpick-play-button"].hidden is True


def test_listening_pick_ten_questions_water_ten_plots_and_end_the_game(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "listenpick")
    game.start()
    plots = []
    while game.active:
        plots.append(game.round["plot_id"])
        game.submit(game.round["answer"])
    assert game.end_reason == "cleared" and len(plots) == 10
    assert all(state.plots_by_id[p].stage == module.STAGE_SPROUT for p in set(plots))
    assert "All 10 heard" in game_env.elements["listenpick-summary"].innerText


def test_listening_pick_a_slow_question_times_out_as_a_miss_and_moves_on(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "listenpick")
    game.start()
    first = game.round
    plot = state.plots_by_id[first["plot_id"]]
    lives = game.lives
    for _ in range(game.params()["seconds"]):
        module.listenpick_tick()
    assert game.round is not first and game.lives == lives - 1
    assert plot.stage == module.STAGE_SEED
    assert "Time ran out" in game.note
    assert game.time_remaining == game.params()["seconds"]  # a fresh clock for the new question


def test_listening_pick_wrong_answer_tells_you_what_it_was(game_env):
    module = game_env.module
    game = _game(module, "listenpick")
    game.start()
    question = game.round
    wrong = next(c for c in question["choices"] if c != question["answer"])
    game.submit(wrong)
    assert question["answer"] in game.note and game.combo == 0


# --- Word Order Race --------------------------------------------------------------------------------


def test_word_order_pool_is_grammar_plots_with_a_short_example_sentence(game_env):
    module = game_env.module
    game = _game(module, "wordorder")
    pool = game.pool()
    assert len(pool) >= 20 and all(p.topic_type == "grammar" for p in pool)
    for plot in pool:
        for item in game.eligible_items(plot):
            words = item["fr"].split()
            assert 3 <= len(words) <= 8 and not set("[]+/…(){}<>→") & set(item["fr"])


def _build(game, order=None):
    words = game.round["words"]
    pool_order = game.round["order"]
    wanted = list(range(len(words))) if order is None else order
    for target in wanted:
        index = next(i for i, w in enumerate(pool_order) if w == target and i not in game.placed)
        result = game.place(index)
    return result


def test_word_order_tiles_are_shuffled_and_the_right_order_waters_the_plot(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "wordorder")
    game.start()
    assert game.round["order"] != list(range(len(game.round["words"])))
    plot = state.plots_by_id[game.round["plot_id"]]
    assert game_env.elements["wordorder-prompt"].innerText == game.round["en"]
    assert len(game_env.elements["wordorder-pool"].children) == len(game.round["words"])
    assert _build(game) is True
    assert plot.stage == module.STAGE_SPROUT and game.score >= 10 and game.done == 1
    assert game.note.startswith(plot.label)
    assert module.practice_ledger["wordorder"]["correct"] == 1


def test_word_order_tapping_moves_a_tile_to_the_sentence_and_undo_takes_it_back(game_env):
    module = game_env.module
    game = _game(module, "wordorder")
    game.start()
    game.place(0)
    assert len(game_env.elements["wordorder-placed"].children) == 1
    assert len(game_env.elements["wordorder-pool"].children) == len(game.round["words"]) - 1
    assert game_env.elements["wordorder-undo-button"].hidden is False
    game_env.elements["wordorder-undo-button"].dispatch("click", None)
    assert game.placed == [] and game_env.elements["wordorder-undo-button"].hidden is True
    assert game.place(99) is None


def test_word_order_wrong_order_shows_the_sentence_and_changes_nothing(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "wordorder")
    game.start()
    plot = state.plots_by_id[game.round["plot_id"]]
    answer = game.round["answer"]
    tiles = len(game.round["order"])
    result = None
    for index in range(tiles):  # tap in pool order: wrong because the pool is shuffled
        result = game.place(index)
    assert result is False
    assert plot.stage == module.STAGE_SEED and plot.last_reviewed is None
    assert answer in game.note and game.combo == 0 and game.done == 1


def test_word_order_six_sentences_then_done_and_each_is_a_different_plot(game_env):
    module, state = game_env.module, game_env.state
    game = _game(module, "wordorder")
    game.start()
    seen = []
    while game.active:
        seen.append(game.round["plot_id"])
        _build(game)
    assert len(seen) == 6 and len(set(seen)) == 6
    assert game.end_reason == "cleared"
    assert "All 6 sentences done" in game_env.elements["wordorder-summary"].innerText
    assert all(state.plots_by_id[p].stage == module.STAGE_SPROUT for p in seen)


def test_word_order_a_sentence_times_out_as_a_miss(game_env):
    module = game_env.module
    game = _game(module, "wordorder")
    game.start()
    first = game.round
    for _ in range(game.params()["seconds"]):
        module.wordorder_tick()
    assert game.round is not first and game.done == 1 and "Time ran out" in game.note
    assert game.time_remaining == game.params()["seconds"]


def test_word_order_a_clock_tick_does_not_rebuild_the_buttons(game_env):
    module = game_env.module
    game = _game(module, "wordorder")
    game.start()
    buttons = list(game_env.elements["wordorder-pool"].children)
    module.wordorder_tick()
    assert list(game_env.elements["wordorder-pool"].children) == buttons


def test_a_clock_tick_does_not_rebuild_the_other_new_games_controls(game_env):
    module = game_env.module
    for key in ("gaps", "listenpick"):
        game = _game(module, key)
        game.start()
        box = game_env.elements[f"{key}-choices"]
        before = list(box.children)
        getattr(module, f"{key}_tick")()
        assert list(box.children) == before


# --- the whole farm is reachable ----------------------------------------------------------------------


def test_every_plot_on_the_farm_has_at_least_one_arcade_game(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    reach = {}
    for key, *_ in mg.WATER_GAMES:
        for plot in mg.game_pool(key):
            reach.setdefault(plot.plot_id, set()).add(key)
    for row in state.rows:
        plots = state.row_plots(row.sequence)
        covered = [p for p in plots if p.plot_id in reach]
        assert len(covered) == len(plots), (row.sequence, len(covered), len(plots))
    assert len(reach) == len(state.plots)


def test_weeks_12_to_23_vocab_and_phrases_were_the_gap_and_are_now_covered(game_env):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    old = set()
    for key in ("blitz", "racer", "boutique", "cafe", "sprint"):
        old |= {p.plot_id for p in mg.game_pool(key)}
    new = set()
    for key in NEW:
        new |= {p.plot_id for p in mg.game_pool(key)}
    late = [p for p in state.plots if p.sequence >= 12 and p.topic_type in ("vocab", "phrase")]
    uncovered_before = [p for p in late if p.plot_id not in old]
    assert len(uncovered_before) > 100  # the gap the new games were built for
    assert all(p.plot_id in new or p.plot_id in old for p in late)
    assert sum(1 for p in uncovered_before if p.plot_id in new) >= 0.95 * len(uncovered_before)
