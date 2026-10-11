"""Picture Grid -- the nonogram maths: clues from a picture, the line-logic solver and two exhaustive solution counters.

Everything here is pure and deterministic (no clock, no randomness) and uses only plain lists and ints, so it runs unchanged
under CPython 3.9 and Pyodide. A picture is a list of equal-length strings of '#' (filled) and '.' (empty).

Cell states in a working grid:  UNKNOWN = 0, FILLED = 1, EMPTY = 2 (the player's dot).

The two proofs the tests lean on:
  * `solve_lines(rows, cols)` is the line-logic solver. It looks at ONE row or column at a time, keeps every cell that is
    filled (or empty) in every arrangement of that line that fits the clue and the cells already known, and repeats until
    nothing changes. It never guesses and never branches. A picture it finishes can be solved by a person with logic alone.
  * `count_solutions(rows, cols, limit)` is an exhaustive counter: line logic, then a branch on an unknown cell, so it
    visits every possible picture that fits. `count_by_rows` is a second counter that shares no code with the solver (it
    tries every row arrangement and prunes only by column prefixes), used by the tests to cross-check the first.
"""

UNKNOWN, FILLED, EMPTY = 0, 1, 2


# ---- clues from a picture --------------------------------------------------------------------------------------------
def line_clue(cells):
    """Block lengths of the filled runs in one line of booleans/ints/chars ('#' counts as filled), left to right."""
    runs, run = [], 0
    for cell in cells:
        if cell == "#" or cell is True or cell == 1:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    if run:
        runs.append(run)
    return runs


def bitmap_ok(bitmap):
    """A picture must be a non-empty rectangle of '#' and '.'."""
    if not isinstance(bitmap, (list, tuple)) or not bitmap:
        return False
    width = len(bitmap[0]) if isinstance(bitmap[0], str) else 0
    if width == 0:
        return False
    for row in bitmap:
        if not isinstance(row, str) or len(row) != width or any(ch not in "#." for ch in row):
            return False
    return True


def clues_of(bitmap):
    """(row clues, column clues) of a picture. The clues are lists of block lengths; an empty line is []."""
    rows = [line_clue(row) for row in bitmap]
    cols = [line_clue([row[c] for row in bitmap]) for c in range(len(bitmap[0]))]
    return rows, cols


def grid_of(bitmap):
    """The picture as a working grid of FILLED / EMPTY cells."""
    return [[FILLED if ch == "#" else EMPTY for ch in row] for row in bitmap]


def bitmap_of(grid):
    """The inverse of grid_of for a finished grid (anything not FILLED counts as empty)."""
    return ["".join("#" if cell == FILLED else "." for cell in row) for row in grid]


def blank_grid(rows, cols):
    return [[UNKNOWN] * cols for _ in range(rows)]


# ---- one line --------------------------------------------------------------------------------------------------------
def line_options(clue, cells):
    """Look at every arrangement of `clue` in a line whose cells are UNKNOWN/FILLED/EMPTY.

    Returns None when no arrangement fits (the cells contradict the clue), else (can_fill, can_empty): two bitmasks (bit i
    for cell i) of the cells that are FILLED in at least one fitting arrangement and EMPTY in at least one.
    """
    n = len(cells)
    k_total = len(clue)
    memo = {}

    def go(pos, k):
        key = (pos, k)
        if key in memo:
            return memo[key]
        result = None
        if k == k_total:
            # every block is placed: the rest of the line must be empty
            if all(cells[i] != FILLED for i in range(pos, n)):
                result = (0, ((1 << n) - 1) ^ ((1 << pos) - 1))
        else:
            fill, empty, found = 0, 0, False
            if pos < n and cells[pos] != FILLED:                      # this cell is empty, block k starts later
                sub = go(pos + 1, k)
                if sub is not None:
                    found = True
                    fill |= sub[0]
                    empty |= sub[1] | (1 << pos)
            length = clue[k]
            end = pos + length
            if end <= n and all(cells[i] != EMPTY for i in range(pos, end)):     # block k starts here
                last = k == k_total - 1
                if last:
                    sub = go(end, k + 1)
                    gap = 0
                elif end < n and cells[end] != FILLED:
                    sub = go(end + 1, k + 1)
                    gap = 1 << end
                else:
                    sub = None
                    gap = 0
                if sub is not None:
                    found = True
                    fill |= sub[0] | (((1 << length) - 1) << pos)
                    empty |= sub[1] | gap
            if found:
                result = (fill, empty)
        memo[key] = result
        return result

    return go(0, 0)


def line_deductions(clue, cells):
    """What one line forces. Returns None for a contradiction, else a list of (index, FILLED or EMPTY) for every UNKNOWN cell
    whose value is the same in all fitting arrangements, in left-to-right order."""
    options = line_options(clue, cells)
    if options is None:
        return None
    can_fill, can_empty = options
    found = []
    for i, cell in enumerate(cells):
        if cell != UNKNOWN:
            continue
        bit = 1 << i
        f, e = bool(can_fill & bit), bool(can_empty & bit)
        if f and not e:
            found.append((i, FILLED))
        elif e and not f:
            found.append((i, EMPTY))
    return found


# ---- the line-logic solver -------------------------------------------------------------------------------------------
def propagate(rows, cols, grid):
    """Repeat line logic on `grid` (changed in place) until nothing more is forced. Returns True when it stayed consistent and
    False when some line has no arrangement left (a contradiction)."""
    height, width = len(rows), len(cols)
    changed = True
    while changed:
        changed = False
        for r in range(height):
            found = line_deductions(rows[r], grid[r])
            if found is None:
                return False
            for c, value in found:
                grid[r][c] = value
                changed = True
        for c in range(width):
            column = [grid[r][c] for r in range(height)]
            found = line_deductions(cols[c], column)
            if found is None:
                return False
            for r, value in found:
                grid[r][c] = value
                changed = True
    return True


def solve_lines(rows, cols, grid=None):
    """Solve by line logic alone. Returns (grid, solved): the working grid after every forced cell is filled in, and whether
    it is complete (no UNKNOWN left and the clues all hold). A contradiction returns solved False."""
    grid = [list(row) for row in grid] if grid else blank_grid(len(rows), len(cols))
    if not propagate(rows, cols, grid):
        return grid, False
    done = all(cell != UNKNOWN for row in grid for cell in row)
    return grid, done and grid_matches(rows, cols, grid)


def count_of_unknown(grid):
    return sum(1 for row in grid for cell in row if cell == UNKNOWN)


def grid_matches(rows, cols, grid):
    """True when every row and column of the (complete) grid has exactly the clue's blocks."""
    for r, clue in enumerate(rows):
        if line_clue(grid[r]) != clue:
            return False
    for c, clue in enumerate(cols):
        if line_clue([grid[r][c] for r in range(len(rows))]) != clue:
            return False
    return True


def line_steps(rows, cols):
    """How many sweeps of line logic the solver needs (a measure of how deep the deduction goes) and whether it finishes."""
    grid = blank_grid(len(rows), len(cols))
    sweeps = 0
    while True:
        before = [row[:] for row in grid]
        if not propagate_once(rows, cols, grid):
            return sweeps, False
        if grid == before:
            break
        sweeps += 1
    return sweeps, count_of_unknown(grid) == 0 and grid_matches(rows, cols, grid)


def propagate_once(rows, cols, grid):
    """One sweep: every row then every column, once. False on contradiction."""
    for r in range(len(rows)):
        found = line_deductions(rows[r], grid[r])
        if found is None:
            return False
        for c, value in found:
            grid[r][c] = value
    for c in range(len(cols)):
        found = line_deductions(cols[c], [grid[r][c] for r in range(len(rows))])
        if found is None:
            return False
        for r, value in found:
            grid[r][c] = value
    return True


# ---- exhaustive counting ---------------------------------------------------------------------------------------------
def count_solutions(rows, cols, limit=2):
    """Count the pictures that fit these clues, stopping once `limit` are found (so a count equal to `limit` means 'at least
    that many'). Line logic prunes; where it stops, the search tries both values of an unknown cell, so no picture is missed."""
    state = {"count": 0}

    def search(grid):
        if state["count"] >= limit:
            return
        if not propagate(rows, cols, grid):
            return
        spot = None
        for r, row in enumerate(grid):
            for c, cell in enumerate(row):
                if cell == UNKNOWN:
                    spot = (r, c)
                    break
            if spot:
                break
        if spot is None:
            if grid_matches(rows, cols, grid):
                state["count"] += 1
            return
        for value in (FILLED, EMPTY):
            nxt = [row[:] for row in grid]
            nxt[spot[0]][spot[1]] = value
            search(nxt)
            if state["count"] >= limit:
                return

    search(blank_grid(len(rows), len(cols)))
    return state["count"]


def row_arrangements(clue, width):
    """Every way to lay the clue's blocks in a row of `width`, as tuples of 0/1 (plain enumeration, no propagation)."""

    def rec(pos, k):
        if k == len(clue):
            return [(0,) * (width - pos)]
        out = []
        last = k == len(clue) - 1
        need = sum(clue[k:]) + len(clue) - k - 1
        for start in range(pos, width - need + 1):
            head = (0,) * (start - pos) + (1,) * clue[k] + (() if last else (0,))
            for tail in rec(start + clue[k] + (0 if last else 1), k + 1):
                out.append(head + tail)
        return out

    return rec(0, 0)


def _prefix_ok(clue, prefix):
    """Could a column that starts with `prefix` (0/1 values) still be completed to `clue`? Sound pruning only."""
    runs, run = [], 0
    for value in prefix:
        if value:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    closed = len(runs)
    if runs != clue[:closed]:
        return False
    if run:
        return closed < len(clue) and run <= clue[closed]
    return True


def count_by_rows(rows, cols, limit=2):
    """A second, independent counter: choose a row arrangement for each row in turn, rejecting a choice as soon as a column
    prefix can no longer fit its clue. No line logic, no shared code with the solver above."""
    width, height = len(cols), len(rows)
    options = [row_arrangements(clue, width) for clue in rows]
    columns = [[] for _ in range(width)]
    state = {"count": 0}

    def descend(r):
        if state["count"] >= limit:
            return
        if r == height:
            if all(line_clue(col) == cols[c] for c, col in enumerate(columns)):
                state["count"] += 1
            return
        for arrangement in options[r]:
            ok = True
            for c in range(width):
                columns[c].append(arrangement[c])
                if not _prefix_ok(cols[c], columns[c]):
                    ok = False
            if ok:
                descend(r + 1)
            for c in range(width):
                columns[c].pop()
            if state["count"] >= limit:
                return

    descend(0)
    return state["count"]


def prove(bitmap, cross_check=False):
    """The full proof for one picture: its clues, how many pictures fit them, whether line logic alone finishes it and
    returns the same picture. `cross_check` also runs the independent counter (slower)."""
    rows, cols = clues_of(bitmap)
    grid, solved = solve_lines(rows, cols)
    out = {"rows": rows, "cols": cols, "line_solved": solved and bitmap_of(grid) == list(bitmap),
           "count": count_solutions(rows, cols, 2), "sweeps": line_steps(rows, cols)[0]}
    if cross_check:
        out["count_by_rows"] = count_by_rows(rows, cols, 2)
    return out
