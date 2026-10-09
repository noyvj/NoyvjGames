"""Hull Repair -- progress is a function of the best layouts the player has stored; nothing here counts time.

`st` is a dict board id -> best status (1 patched, 2 restored); a board with no entry is open (0)."""

import boards

OPEN_AT = boards.OPEN_AT


def state_of(st, bid):
    return st.get(bid, 0)


def deck_patched(st, chapter):
    return sum(1 for bid in chapter["rooms"] if st.get(bid, 0) >= 1)


def deck_restored(st, chapter):
    return sum(1 for bid in chapter["rooms"] if st.get(bid, 0) >= 2)


def chapter_open(st, index):
    """Deck 1 is always open; the next deck opens once OPEN_AT boards of the one before are patched (or all of them,
    if the deck has fewer). A deck with no boards is never open."""
    chapter = boards.CHAPTER_LIST[index]
    if not chapter["rooms"]:
        return False
    if index == 0:
        return True
    prev = boards.CHAPTER_LIST[index - 1]
    return deck_patched(st, prev) >= min(OPEN_AT, len(prev["rooms"]))


def board_open(st, bid):
    return chapter_open(st, boards.BY_ID[bid].chapter)


def totals(st):
    patched = sum(1 for v in st.values() if v >= 1)
    restored = sum(1 for v in st.values() if v >= 2)
    decks_patched = sum(1 for c in boards.CHAPTER_LIST if c["rooms"] and deck_patched(st, c) == len(c["rooms"]))
    decks_restored = sum(1 for c in boards.CHAPTER_LIST if c["rooms"] and deck_restored(st, c) == len(c["rooms"]))
    return {"rooms": len(boards.ORDER), "patched": patched, "restored": restored,
            "decks_patched": decks_patched, "decks_restored": decks_restored, "decks": len(boards.CHAPTER_LIST)}


def next_board(st, bid):
    """The next open board to play after `bid`: the first not yet patched, going round; else the next open one in order."""
    order = boards.ORDER
    if bid not in order:
        return None
    start = order.index(bid)
    rotated = order[start + 1:] + order[:start]
    for other in rotated:
        if board_open(st, other) and st.get(other, 0) == 0:
            return other
    for other in rotated:
        if board_open(st, other) and st.get(other, 0) < 2:
            return other
    return None
