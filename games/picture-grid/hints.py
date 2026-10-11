"""Picture Grid -- the hint ladder. Every hint is a line-logic deduction, so it is always justified, and nothing is guessed.

Three rungs, each opened only when the player asks (never shown on its own):
  1 the nudge   which row or column has a move that is certain (no cell named)
  2 the hint    that line again and what KIND of reasoning forces the move (still no cell named)
  3 the fill    the certain cells of that line, put on the frame (one undo step; on Normal after a confirm)

The line is chosen from what the player has marked and is RIGHT: a mark that disagrees with the picture is ignored when working
out what is certain (it is not named, and the fill will replace it), so a hint can never be led astray by a mistake and a hint
never says "you made a mistake" on its own. Chosen deterministically: the line with the most certain fills, then the most
certain moves, rows before columns, lowest number first. Pure functions of the picture and the grid: no clock, no randomness.
"""

import nonogram

UNKNOWN, FILLED, EMPTY = nonogram.UNKNOWN, nonogram.FILLED, nonogram.EMPTY

KINDS = ("empty", "complete", "exact", "overlap", "pinned")


def knowledge(picture, grid):
    """The player's marks that agree with the picture (a wrong mark counts as unknown), as FILLED / EMPTY / UNKNOWN."""
    solution = picture.solution_grid()
    out = []
    for r in range(picture.height):
        row = []
        for c in range(picture.width):
            cell = grid[r][c]
            if cell == UNKNOWN:
                row.append(UNKNOWN)
            elif (cell == FILLED) == (solution[r][c] == FILLED):
                row.append(FILLED if cell == FILLED else EMPTY)
            else:
                row.append(UNKNOWN)
        out.append(row)
    return out


def line_of(cells2d, kind, index):
    if kind == "row":
        return list(cells2d[index])
    return [row[index] for row in cells2d]


def point(kind, index, i):
    """Grid position of cell number `i` of a line."""
    return (index, i) if kind == "row" else (i, index)


def clue_of(picture, kind, index):
    return picture.row_clues[index] if kind == "row" else picture.col_clues[index]


def line_name(kind, index):
    return "%s %d" % ("Row" if kind == "row" else "Column", index + 1)


def clue_words(clue):
    return " ".join(str(n) for n in clue) if clue else "0"


def candidates(picture, grid):
    """Every line with something certain to do, as dicts. `moves` are (position, FILLED/EMPTY) the grid does not already show."""
    know = knowledge(picture, grid)
    found = []
    for kind, count in (("row", picture.height), ("col", picture.width)):
        for index in range(count):
            cells = line_of(know, kind, index)
            clue = clue_of(picture, kind, index)
            certain = nonogram.line_deductions(clue, cells)
            if not certain:
                continue
            shown = line_of(grid, kind, index)
            moves = [(i, value) for i, value in certain if shown[i] != value]
            if moves:
                found.append({"kind": kind, "index": index, "moves": moves, "known": cells})
    return found


def pick(picture, grid):
    """The line to offer, or None when nothing is certain (only when the frame is already done)."""
    best, best_key = None, None
    for cand in candidates(picture, grid):
        fills = sum(1 for _i, value in cand["moves"] if value == FILLED)
        key = (-fills, -len(cand["moves"]), 0 if cand["kind"] == "row" else 1, cand["index"])
        if best_key is None or key < best_key:
            best, best_key = cand, key
    return best


def reasoning(clue, cells):
    """Which kind of line logic forces the move: one of KINDS. `cells` is what is known (correct marks) in the line."""
    n = len(cells)
    if not clue:
        return "empty"
    known_fills = [1 if cell == FILLED else 0 for cell in cells]
    if nonogram.line_clue(known_fills) == list(clue):
        return "complete"
    if all(cell == UNKNOWN for cell in cells):
        total = sum(clue) + len(clue) - 1
        return "exact" if total == n else "overlap"
    return "pinned"


def nudge_text(kind, index):
    return "%s has a move that is certain. No guessing is needed there." % line_name(kind, index)


def detail_text(picture, kind, index, known):
    clue = clue_of(picture, kind, index)
    name = line_name(kind, index)
    n = picture.width if kind == "row" else picture.height
    why = reasoning(clue, known)
    head = "%s, clue %s." % (name, clue_words(clue))
    if why == "empty":
        return head + " A clue of 0 means the line has no filled cells at all, so every cell in it can be dotted."
    if why == "complete":
        return head + " The filled cells you have already make every block of the clue, so every other cell in this line is empty."
    if why == "exact":
        total = sum(clue) + len(clue) - 1
        return head + " The blocks and the one-cell gaps between them need %d cells and the line has %d, so there is no spare room and the whole line is certain." % (total, n)
    if why == "overlap":
        total = sum(clue) + len(clue) - 1
        slack = n - total
        return head + " The blocks and the gaps between them leave %d spare cell%s, and a block longer than that must be filled in its middle wherever it sits." % (slack, "" if slack == 1 else "s")
    return head + " Put the clue together with the cells already marked in this line: only some placements of the blocks still fit, and some cells are the same in all of them."


def cells_phrase(kind, moves):
    """'filled columns 3 to 5, dotted column 8' for the moves of a line (positions numbered from 1)."""
    parts = []
    for word, value in (("filled", FILLED), ("dotted", EMPTY)):
        spots = [i + 1 for i, v in moves if v == value]
        if not spots:
            continue
        runs, start, prev = [], spots[0], spots[0]
        for s in spots[1:]:
            if s == prev + 1:
                prev = s
                continue
            runs.append((start, prev))
            start = prev = s
        runs.append((start, prev))
        unit = "column" if kind == "row" else "row"
        pieces = [("%s %d" % (unit, a)) if a == b else ("%ss %d to %d" % (unit, a, b)) for a, b in runs]
        parts.append(word + " " + ", ".join(pieces))
    return ", ".join(parts)


def fill_text(kind, index, moves):
    return "%s: %s." % (line_name(kind, index), cells_phrase(kind, moves))
