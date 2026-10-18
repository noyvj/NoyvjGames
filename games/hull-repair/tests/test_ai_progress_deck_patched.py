import boards
import progress


def test_deck_patched_counts_some_patched():
    """Normal case: counts rooms with status >= 1 in a chapter."""
    st = {boards.CHAPTER_LIST[0]["rooms"][0]: 1}
    assert progress.deck_patched(st, boards.CHAPTER_LIST[0]) == 1


def test_deck_patched_counts_all_patched():
    """Normal case: all rooms in the chapter are patched (status >= 1)."""
    st = {bid: 1 for bid in boards.CHAPTER_LIST[1]["rooms"]}
    assert progress.deck_patched(st, boards.CHAPTER_LIST[1]) == len(boards.CHAPTER_LIST[1]["rooms"])


def test_deck_patched_handles_empty_state():
    """Edge case: state has no entries for the chapter."""
    st = {}
    assert progress.deck_patched(st, boards.CHAPTER_LIST[2]) == 0
