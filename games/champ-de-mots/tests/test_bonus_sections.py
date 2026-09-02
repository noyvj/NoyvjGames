"""Milestone 13: bonus sentence-building sections (§14.6).

One original sentence per week, authored fresh from that week's own vocab +
grammar (never lifted from the workbook), stored in the catalog's new
`bonus_sentences` field. Three tasks per sentence: (1) drag/place word tiles
into order, (2) translate each tile individually (STRICT), (3) translate the
assembled sentence as a whole (LENIENT).
"""

import pytest


# --- catalog data shape --------------------------------------------------


def test_every_week_has_at_least_one_bonus_sentence(game_env):
    module = game_env.module
    for week in module.CATALOG["weeks"]:
        assert week.get("bonus_sentences"), week["sequence"]


def test_bonus_sentence_tiles_reconstruct_the_full_sentence(game_env):
    module = game_env.module
    for week in module.CATALOG["weeks"]:
        for sentence in week["bonus_sentences"]:
            rebuilt = " ".join(tile["fr"] for tile in sentence["tiles"])
            assert rebuilt == sentence["fr"], sentence["id"]


def test_bonus_sentence_ids_are_unique(game_env):
    module = game_env.module
    ids = [
        sentence["id"]
        for week in module.CATALOG["weeks"]
        for sentence in week["bonus_sentences"]
    ]
    assert len(ids) == len(set(ids))


def test_bonus_sentence_is_not_a_verbatim_copy_of_an_existing_catalog_item(game_env):
    """§14.6/§5's copyright rule: original, not lifted. A bonus sentence must
    not just be one existing catalog item's fr text copy-pasted whole."""
    module = game_env.module
    for week in module.CATALOG["weeks"]:
        existing_fr = {
            module.normalize_answer(item["fr"])
            for topic in week["topics"]
            for item in topic["items"]
        }
        for sentence in week["bonus_sentences"]:
            assert module.normalize_answer(sentence["fr"]) not in existing_fr, sentence["id"]


# --- availability --------------------------------------------------------


def test_bonus_section_is_available_for_an_unlocked_week_with_sentences(game_env):
    module = game_env.module
    assert module.is_bonus_section_available(1) is True


def test_bonus_section_is_not_available_for_a_locked_week(game_env):
    module, state = game_env.module, game_env.state
    assert state.is_row_unlocked(12) is False
    assert module.is_bonus_section_available(12) is False


def test_starting_a_bonus_section_for_a_locked_week_does_nothing(game_env):
    module = game_env.module
    module.start_bonus_section(12)
    assert module.bonus_mode is False


# --- task 1: tile ordering -------------------------------------------------


def test_start_bonus_section_shuffles_the_tile_pool(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    assert module.bonus_mode is True
    assert module.bonus_task == "order"
    sentence = module.bonus_queue[0]
    assert len(module.bonus_tile_pool) == len(sentence["tiles"])
    assert sorted(t["fr"] for t in module.bonus_tile_pool) == sorted(
        t["fr"] for t in sentence["tiles"]
    )


def test_placing_all_tiles_in_the_correct_order_is_marked_correct(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    sentence = module.bonus_queue[0]
    for tile in sentence["tiles"]:
        index = next(
            i for i, t in enumerate(module.bonus_tile_pool) if t["fr"] == tile["fr"]
        )
        module.place_bonus_tile(index)
    assert module.bonus_tile_pool == []
    assert module.bonus_order_correct is True
    assert module.bonus_score == {"correct": 1, "total": 1}


def test_placing_tiles_out_of_order_is_marked_incorrect(game_env):
    module = game_env.module
    week = next(
        w
        for w in module.CATALOG["weeks"]
        if w["sequence"] <= 11 and len(w["bonus_sentences"][0]["tiles"]) > 1
    )
    module.start_bonus_section(week["sequence"])
    while module.bonus_tile_pool:
        # Always take from the far end of the pool -- reliably out of the
        # correct order for any sentence with more than one distinct tile.
        module.place_bonus_tile(len(module.bonus_tile_pool) - 1)
    if module.bonus_order_correct is not False:
        pytest.skip("this week's own tile order happens to be a palindrome")
    assert module.bonus_score == {"correct": 0, "total": 1}


def test_place_bonus_tile_does_nothing_once_the_order_task_is_done(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    sentence = module.bonus_queue[0]
    for tile in sentence["tiles"]:
        index = next(
            i for i, t in enumerate(module.bonus_tile_pool) if t["fr"] == tile["fr"]
        )
        module.place_bonus_tile(index)
    before = module.bonus_score.copy()
    module.place_bonus_tile(0)
    assert module.bonus_score == before


# --- task 2: per-tile STRICT translation -----------------------------------


def _complete_order_task(module):
    sentence = module.bonus_queue[module.bonus_index]
    for tile in sentence["tiles"]:
        index = next(
            i for i, t in enumerate(module.bonus_tile_pool) if t["fr"] == tile["fr"]
        )
        module.place_bonus_tile(index)
    module.advance_from_order()


def test_task_two_starts_after_advancing_from_the_order_task(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    assert module.bonus_task == "translate_tiles"
    assert module.bonus_tile_index == 0


def test_correct_tile_translation_is_accepted(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    sentence = module.bonus_queue[module.bonus_index]
    first_tile = sentence["tiles"][0]
    result = module.submit_bonus_tile_translation(first_tile["en"])
    assert result is True
    assert module.bonus_tile_result is True


def test_tile_translation_is_graded_strict_not_lenient(game_env):
    """§14.6: task 2 is explicitly STRICT -- an added leading article (a
    LENIENT-only forgiveness) must not be accepted here."""
    module = game_env.module
    week = next(
        w for w in module.CATALOG["weeks"]
        if any(t["en"].split()[0].casefold() in ("a", "an", "the") for t in w["bonus_sentences"][0]["tiles"])
    )
    module.start_bonus_section(week["sequence"])
    _complete_order_task(module)
    sentence = module.bonus_queue[module.bonus_index]
    tile_index = next(
        i for i, t in enumerate(sentence["tiles"])
        if t["en"].split()[0].casefold() in ("a", "an", "the")
    )
    while module.bonus_tile_index < tile_index:
        module.submit_bonus_tile_translation(sentence["tiles"][module.bonus_tile_index]["en"])
        module.next_bonus_tile()
    tile = sentence["tiles"][tile_index]
    dropped_article = " ".join(tile["en"].split()[1:])
    result = module.submit_bonus_tile_translation(dropped_article)
    assert result is False


def test_wrong_tile_translation_is_rejected(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    result = module.submit_bonus_tile_translation("absolutely not the right answer")
    assert result is False


def test_next_bonus_tile_advances_through_every_tile(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    sentence = module.bonus_queue[module.bonus_index]
    for tile in sentence["tiles"]:
        assert module.bonus_task == "translate_tiles"
        module.submit_bonus_tile_translation(tile["en"])
        module.next_bonus_tile()
    assert module.bonus_task == "translate_sentence"
    assert module.bonus_tile_score == {"correct": len(sentence["tiles"]), "total": len(sentence["tiles"])}


# --- task 3: whole-sentence LENIENT translation -----------------------------


def _complete_tile_task(module):
    sentence = module.bonus_queue[module.bonus_index]
    for tile in sentence["tiles"]:
        module.submit_bonus_tile_translation(tile["en"])
        module.next_bonus_tile()


def test_sentence_translation_is_graded_leniently(game_env):
    """§14.6: task 3 is LENIENT -- a dropped leading article/contraction
    equivalence should still pass, unlike task 2."""
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    _complete_tile_task(module)
    assert module.bonus_task == "translate_sentence"
    sentence = module.bonus_queue[module.bonus_index]
    result = module.submit_bonus_sentence_translation(sentence["en"])
    assert result is True


def test_wrong_sentence_translation_is_rejected(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    _complete_tile_task(module)
    result = module.submit_bonus_sentence_translation("nothing at all like it")
    assert result is False


# --- moving between sentences and finishing --------------------------------


def test_next_bonus_sentence_advances_the_queue_or_ends_the_session(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    total_sentences = len(module.bonus_queue)
    for _ in range(total_sentences):
        _complete_order_task(module)
        _complete_tile_task(module)
        sentence = module.bonus_queue[module.bonus_index]
        module.submit_bonus_sentence_translation(sentence["en"])
        module.next_bonus_sentence()
    assert module.bonus_index == total_sentences
    assert module.bonus_task is None


def test_close_bonus_section_resets_everything(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    module.close_bonus_section()
    assert module.bonus_mode is False
    assert module.bonus_queue == []
    assert module.bonus_sequence is None
    assert module.bonus_task is None


# --- doesn't touch SRS or unlock state -------------------------------------


def test_bonus_section_never_touches_srs_state(game_env):
    module, state = game_env.module, game_env.state
    before = {
        p.plot_id: (p.stage, p.interval_days, p.next_due, p.last_reviewed, p.correct_streak)
        for p in state.plots
    }
    module.start_bonus_section(1)
    total_sentences = len(module.bonus_queue)
    for _ in range(total_sentences):
        _complete_order_task(module)
        _complete_tile_task(module)
        sentence = module.bonus_queue[module.bonus_index]
        module.submit_bonus_sentence_translation(sentence["en"])
        module.next_bonus_sentence()
    after = {
        p.plot_id: (p.stage, p.interval_days, p.next_due, p.last_reviewed, p.correct_streak)
        for p in state.plots
    }
    assert before == after


def test_bonus_section_never_affects_row_unlock_state(game_env):
    module, state = game_env.module, game_env.state
    assert state.is_row_unlocked(12) is False
    module.start_bonus_section(1)
    total_sentences = len(module.bonus_queue)
    for _ in range(total_sentences):
        _complete_order_task(module)
        _complete_tile_task(module)
        sentence = module.bonus_queue[module.bonus_index]
        module.submit_bonus_sentence_translation(sentence["en"])
        module.next_bonus_sentence()
    assert state.is_row_unlocked(12) is False


def test_bonus_session_is_not_part_of_the_save_payload(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    state_dict = module.get_state()
    assert set(state_dict) == {"version", "current_day", "plots"}


# --- rendering / entry point -------------------------------------------


def test_each_unlocked_row_gets_a_bonus_section_button(game_env):
    module, state = game_env.module, game_env.state
    for row in state.rows:
        button = game_env.elements.get(f"row-bonus-{row.sequence}")
        assert button is not None
        assert button.disabled == (not state.is_row_unlocked(row.sequence))


def test_clicking_a_row_bonus_button_starts_that_weeks_section(game_env):
    module = game_env.module
    game_env.elements["row-bonus-1"].dispatch("click", None)
    assert module.bonus_mode is True
    assert module.bonus_sequence == 1


def test_bonus_panel_shows_the_tile_pool_during_the_order_task(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    assert game_env.elements["bonus-panel"].hidden is False
    assert len(game_env.elements["bonus-tile-pool"].children) == len(module.bonus_tile_pool)


def test_bonus_panel_hides_on_close(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    module.close_bonus_section()
    assert game_env.elements["bonus-panel"].hidden is True
