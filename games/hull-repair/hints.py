"""Hull Repair -- the hint ladder. Three rungs per board, all free, none touching a board's status:
1 a nudge (one plain sentence about where to start), 2 a hint (the opening cells of one line shown as a ghost), 3 the
answer (the whole stored layout shown as a ghost, with a button to lay it). Everything is derived from the board and its
stored layout, so it is the same every time."""

import rules

WORDS = ("up", "right", "down", "left")
OPENING = 4
EASY_OPENING = 8       # AN-17: on Easy the hint rung shows twice as much of the starting line


def exits(board, cell):
    n = 0
    for nb in board.neighbours(cell):
        if nb in board.port_at or nb in board.mixers:
            continue
        n += 1
    return n


def starter(board):
    """The line to start with: a line long enough to show an opening, whose ports have the fewest ways out, then the shortest."""
    def key(c):
        ends = (board.src[c], board.dst[c])
        return (len(board.solution[c]) < OPENING, min(exits(board, e) for e in ends), len(board.solution[c]), c)
    return min(board.lines, key=key)


def nudge_text(board):
    c = starter(board)
    name = rules.LINE_NAMES[c]
    low = min(exits(board, e) for e in (board.src[c], board.dst[c]))
    if low <= 1:
        return "Start with the %s line (%s): one of its ports has only one way out, so its first step is already decided." % (name, c)
    if low == 2:
        return "Start with the %s line (%s): one of its ports sits in a tight spot with only two ways out." % (name, c)
    return "Start with the %s line (%s): it is the one with the least room to wander." % (name, c)


def opening(board, easy=False):
    c = starter(board)
    cells = board.solution[c][:(EASY_OPENING if easy else OPENING) + 1]
    return c, cells


def hint_text(board, easy=False):
    c, cells = opening(board, easy)
    steps = [WORDS[rules.dir_index(rules.sub(b, a))] for a, b in zip(cells, cells[1:])]
    here = "column %d, row %d" % (cells[0][0] + 1, cells[0][1] + 1)
    return "The %s line (%s) leaves its source at %s and goes %s. The dotted ghost on the board shows it." % (
        rules.LINE_NAMES[c], c, here, ", then ".join(steps))


def view(board, rung, limit=3, easy=False):
    """What the ladder shows at `rung`. `limit` is the last rung on offer (2 on Hard: no answer step); `easy` lengthens the hint."""
    rung = min(rung, limit)
    out = {"rung": rung, "nudge": "", "hint": "", "answer": False, "max": limit}
    if rung >= 1:
        out["nudge"] = nudge_text(board)
    if rung >= 2:
        out["hint"] = hint_text(board, easy)
    if rung >= 3:
        out["answer"] = True
    return out


def ghosts(board, rung, limit=3, easy=False):
    """The ghost lines to draw under the player's lines for a rung."""
    rung = min(rung, limit)
    if rung >= 3:
        return {c: list(p) for c, p in board.solution.items()}
    if rung == 2:
        c, cells = opening(board, easy)
        return {c: list(cells)}
    return {}
