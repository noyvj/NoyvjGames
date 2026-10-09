"""Robot Script -- progress rules: which chapters are open, how far along the player is.

Nothing here is stored: it is all computed from `best`, the dict {room id: {"n": steps, "t": program text}} of the best
clears, so a loaded save and a played one cannot disagree and a retuned par re-grades the medals on its own.
"""

import rooms

OPEN_AT = 5          # rooms of a chapter that must be cleared to open the next chapter


def cleared_in(best, chapter):
    return sum(1 for rid in chapter["rooms"] if rid in best)


def chapter_open(best, index):
    if index == 0:
        return True
    prev = rooms.CHAPTER_LIST[index - 1]
    return cleared_in(best, prev) >= min(OPEN_AT, len(prev["rooms"]))


def chapter_done(best, index):
    chapter = rooms.CHAPTER_LIST[index]
    return cleared_in(best, chapter) == len(chapter["rooms"])


def room_open(best, rid):
    return chapter_open(best, rooms.BY_ID[rid].chapter)


def medal_of(best, rid):
    """0 not cleared, else 1 bronze, 2 silver, 3 gold."""
    entry = best.get(rid)
    return rooms.medal(rooms.BY_ID[rid].par, entry["n"]) if entry else 0


def totals(best):
    medals = [medal_of(best, rid) for rid in rooms.ORDER]
    return {"cleared": sum(1 for m in medals if m), "gold": sum(1 for m in medals if m == 3),
            "silver": sum(1 for m in medals if m == 2), "bronze": sum(1 for m in medals if m == 1),
            "rooms": len(rooms.ORDER), "chapters_done": sum(1 for i in range(len(rooms.CHAPTER_LIST)) if chapter_done(best, i)),
            "chapters": len(rooms.CHAPTER_LIST)}


def next_room(best, rid):
    """The room to offer after `rid`: the next uncleared open room in order, else the next open one, else None."""
    order = rooms.ORDER
    i = order.index(rid)
    for other in order[i + 1:] + order[:i]:
        if other not in best and room_open(best, other):
            return other
    for other in order[i + 1:]:
        if room_open(best, other):
            return other
    return None
