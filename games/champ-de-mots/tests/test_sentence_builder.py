"""L11 -- the freeform sentence builder: bonus sentences from every unlocked
week, tapped into order at any time, counting toward the practice score."""


def _solve(m):
    """Taps the current sentence's tiles in the right order."""
    sentence = m.builder_queue[m.builder_index]
    for tile in sentence["tiles"]:
        index = next(i for i, t in enumerate(m.builder_pool) if t["fr"] == tile["fr"])
        m.place_builder_tile(index)


def test_it_is_a_practice_mode(game_env):
    m = game_env.module
    assert "builder" in m.PRACTICE_MODES
    assert set(m.practice_ledger) == set(m.PRACTICE_MODES)


def test_only_unlocked_weeks_feed_the_builder(game_env):
    m = game_env.module
    game_env.state.is_row_unlocked = lambda sequence: sequence <= 2
    ids = {s["id"] for s in m.builder_sentences()}
    expected = {
        s["id"] for w in m.CATALOG["weeks"] if w["sequence"] <= 2 for s in w.get("bonus_sentences", [])
    }
    assert ids == expected and ids
    all_ids = {s["id"] for w in m.CATALOG["weeks"] for s in w.get("bonus_sentences", [])}
    assert ids < all_ids


def test_nothing_unlocked_shows_the_empty_message(game_env):
    m = game_env.module
    game_env.state.is_row_unlocked = lambda sequence: False
    m.start_sentence_builder()
    assert m.builder_queue == []
    empty = game_env.elements["builder-empty-message"]
    assert empty.hidden is False and empty.innerText == m.BUILDER_EMPTY_MESSAGE
    assert game_env.elements["builder-card"].hidden is True


def test_button_opens_a_shuffled_session(game_env):
    m = game_env.module
    game_env.elements["sentence-builder-button"].dispatch("click", None)
    assert m.builder_active and 1 <= len(m.builder_queue) <= m.BUILDER_SESSION_LENGTH
    assert game_env.elements["builder-panel"].hidden is False
    sentence = m.builder_queue[0]
    assert game_env.elements["builder-prompt"].innerText == sentence["en"]
    assert len(m.builder_pool) == len(sentence["tiles"])
    assert [t["fr"] for t in m.builder_pool] != [t["fr"] for t in sentence["tiles"]] or len(m.builder_pool) == 1


def test_right_order_scores_a_practice_point(game_env):
    m = game_env.module
    m.start_sentence_builder()
    before = m.practice_score()
    _solve(m)
    assert m.builder_result is True
    assert m.builder_score == {"correct": 1, "total": 1}
    assert m.practice_ledger["builder"]["correct"] == 1
    assert m.practice_score() == before + 1
    assert game_env.elements["builder-feedback"].innerText == m.BUILDER_CORRECT
    assert game_env.elements["builder-next-button"].hidden is False


def test_wrong_order_shows_the_real_sentence_and_scores_nothing(game_env):
    m = game_env.module
    m.start_sentence_builder()
    sentence = m.builder_queue[0]
    wrong = list(reversed(sentence["tiles"]))
    if [t["fr"] for t in wrong] == [t["fr"] for t in sentence["tiles"]]:
        return  # a palindrome sentence: nothing to get wrong
    for tile in wrong:
        index = next(i for i, t in enumerate(m.builder_pool) if t["fr"] == tile["fr"])
        m.place_builder_tile(index)
    assert m.builder_result is False
    assert sentence["fr"] in game_env.elements["builder-feedback"].innerText
    assert m.practice_ledger["builder"]["total"] == 1 and m.practice_ledger["builder"]["points"] == 0


def test_undo_takes_the_last_tile_back_only_before_checking(game_env):
    m = game_env.module
    m.start_sentence_builder()
    size = len(m.builder_pool)
    m.place_builder_tile(0)
    assert m.undo_builder_tile() is True
    assert len(m.builder_pool) == size and m.builder_placed == []
    assert m.undo_builder_tile() is False
    _solve(m)
    assert m.undo_builder_tile() is False


def test_next_walks_the_queue_then_shows_the_summary(game_env):
    m = game_env.module
    m.start_sentence_builder()
    total = len(m.builder_queue)
    for _ in range(total):
        _solve(m)
        m.next_builder_sentence()
    assert m.builder_index == total
    assert game_env.elements["builder-summary"].hidden is False
    assert f"{total}/{total}" in game_env.elements["builder-summary"].innerText


def test_next_and_placing_are_ignored_at_the_wrong_time(game_env):
    m = game_env.module
    assert m.place_builder_tile(0) is None and m.next_builder_sentence() is None
    m.start_sentence_builder()
    assert m.next_builder_sentence() is None  # not answered yet
    assert m.place_builder_tile(999) is None


def test_close_resets_and_hides(game_env):
    m = game_env.module
    m.start_sentence_builder()
    m.place_builder_tile(0)
    game_env.elements["builder-close-button"].dispatch("click", None)
    assert m.builder_active is False and m.builder_queue == [] and m.builder_placed == []
    assert game_env.elements["builder-panel"].hidden is True


def test_it_never_touches_any_plot(game_env):
    m = game_env.module
    snapshot = [(p.stage, p.last_reviewed, p.correct_streak) for p in game_env.state.plots]
    m.start_sentence_builder()
    _solve(m)
    assert [(p.stage, p.last_reviewed, p.correct_streak) for p in game_env.state.plots] == snapshot
