import boards
import progress


def test_deck_restored_counts_all_when_every_board_is_restored():
    """Normal case: every board in the chapter has status 2."""
    st = {bid: 2 for bid in boards.CHAPTER_LIST[0]["rooms"]}
    assert progress.deck_restored(st, boards.CHAPTER_LIST[0]) == len(boards.CHAPTER_LIST[0]["rooms"])


def test_deck_restored_counts_none_when_no_board_is_restored():
    """Normal case: every board has status 1 (patched) or 0 (open)."""
    st = {bid: 1 for bid in boards.CHAPTER_LIST[1]["rooms"]}
    assert progress.deck_restored(st, boards.CHAPTER_LIST[1]) == 0


def test_deck_restored_counts_only_the_restored_boards_in_a_mixed_state():
    """Normal case: only boards with status >= 2 are counted."""
    rooms = boards.CHAPTER_LIST[2]["rooms"]
    st_mixed = {rooms[0]: 2, rooms[1]: 1}
    assert progress.deck_restored(st_mixed, boards.CHAPTER_LIST[2]) == 1


def test_deck_restored_handles_missing_boards_gracefully():
    """Edge case: st is empty or missing some board ids; defaults to 0."""
    assert progress.deck_restored({}, boards.CHAPTER_LIST[3]) == 0
