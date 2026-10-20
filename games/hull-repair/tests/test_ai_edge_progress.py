import boards
import progress


def test_state_of_returns_defaults_and_present_values():
    """state_of should return 0 for missing keys and the stored value when present."""
    assert progress.state_of({}, "any-board") == 0
    assert progress.state_of({"some": 1}, "other") == 0
    assert progress.state_of({"target": 2}, "target") == 2


def test_deck_patched_counts_correctly():
    """deck_patched should count boards with status >= 1 in a chapter."""
    empty_chapter = {"rooms": []}
    assert progress.deck_patched({}, empty_chapter) == 0

    full_chapter = {"rooms": ["a", "b", "c"]}
    st = {"a": 1, "b": 2, "c": 0}
    assert progress.deck_patched(st, full_chapter) == 2


def test_deck_restored_counts_correctly():
    """deck_restored should count boards with status >= 2 in a chapter."""
    empty_chapter = {"rooms": []}
    assert progress.deck_restored({}, empty_chapter) == 0

    full_chapter = {"rooms": ["a", "b"]}
    st = {"a": 1, "b": 2}
    assert progress.deck_restored(st, full_chapter) == 1


def test_chapter_open_handles_bounds():
    """chapter_open should return True for valid indices with rooms, False otherwise."""
    assert progress.chapter_open({}, 0) is True
    assert progress.chapter_open({}, -1) is False
    assert progress.chapter_open({}, len(boards.CHAPTER_LIST)) is False
    assert progress.chapter_open({}, 999) is False


def test_board_open_checks_known_boards():
    """board_open should return True for known board ids, False otherwise."""
    first_board = boards.ORDER[0]
    assert progress.board_open({}, first_board) is True
    assert progress.board_open({}, "nonexistent-board") is False


def test_totals_handles_empty_and_full_states():
    """totals should compute correct counts for empty and fully restored states."""
    t_empty = progress.totals({})
    assert t_empty["rooms"] == len(boards.ORDER)
    assert t_empty["patched"] == 0
    assert t_empty["restored"] == 0

    full_st = {bid: 2 for bid in boards.ORDER}
    t_full = progress.totals(full_st)
    assert t_full["rooms"] == len(boards.ORDER)
    assert t_full["patched"] == len(boards.ORDER)
    assert t_full["restored"] == len(boards.ORDER)
    assert t_full["decks_patched"] == len(boards.CHAPTER_LIST)
    assert t_full["decks_restored"] == len(boards.CHAPTER_LIST)


def test_next_board_returns_correct_sequence():
    """next_board should find the first open board after `bid`, wrapping around."""
    assert progress.next_board({}, "unknown") is None

    full_st = {bid: 2 for bid in boards.ORDER}
    assert progress.next_board(full_st, boards.ORDER[0]) is None

    st = {boards.ORDER[0]: 1}
    next_b = progress.next_board(st, boards.ORDER[0])
    assert next_b == boards.ORDER[1]

    st = {bid: 1 for bid in boards.ORDER[:-1]}
    next_b = progress.next_board(st, boards.ORDER[-2])
    assert next_b == boards.ORDER[-1]
