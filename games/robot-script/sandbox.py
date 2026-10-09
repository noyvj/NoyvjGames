"""Robot Script -- the free sandbox: paint a room, write any list, run it as often as you like. No goal, no medal.

The room is an 8 by 8 grid of the same tile characters the authored rooms use. Every paint is checked here, so the saved
layout is always something room.Layout can draw and run. The sandbox opens once The Long Shift is cleared.
"""

import dsl
import room

SIZE = 8
ALLOW = "F L R G P S rep until if A B"
TILES = (
    (".", "Floor (erase)"), ("#", "Wall"), ("E", "Exit pad"), ("p", "Part"), ("o", "Socket"),
    ("1", "Switch 1"), ("2", "Switch 2"), ("3", "Switch 3"), ("A", "Door A (switch 1)"), ("B", "Door B (switch 2)"),
    ("C", "Door C (switch 3)"), (">", "Robot, facing east"), ("<", "Robot, facing west"), ("^", "Robot, facing north"),
    ("v", "Robot, facing south"),
)
PAINTABLE = "".join(t for t, _ in TILES)
STARTS = "><^v"

PRESETS = {
    "open": ("An open floor", [">.......", "........", "........", "........", "........", "........", "........", "........"]),
    "maze": ("A small maze", [">.#.....", ".##.###.", "....#...", "#####.#.", "......#.", ".######.", "........", "E#######"]),
    "workshop": ("A workshop", [">.......", "..#..#o.", ".1#..#..", "..#..A..", "..#p.#..", "..#..#..", "..#2.#..", "E.#..#.."]),
}
DEFAULT = "open"


def default_rows():
    return list(PRESETS[DEFAULT][1])


def valid_rows(rows):
    """True when `rows` is an 8 by 8 drawing of known tiles with exactly one robot."""
    if not isinstance(rows, list) or len(rows) != SIZE or not all(isinstance(r, str) and len(r) == SIZE for r in rows):
        return False
    text = "".join(rows)
    if any(c not in PAINTABLE for c in text) or sum(text.count(c) for c in STARTS) != 1:
        return False
    return True


def paint(rows, x, y, tile):
    """Return (new rows, changed) or (rows, reason string) when the paint is refused."""
    if not (isinstance(x, int) and isinstance(y, int) and not isinstance(x, bool) and not isinstance(y, bool)) or not (0 <= x < SIZE and 0 <= y < SIZE):
        return rows, "That is outside the room."
    if not isinstance(tile, str) or len(tile) != 1 or tile not in PAINTABLE:
        return rows, "That is not a tile."
    here = rows[y][x]
    if here == tile:
        return rows, False
    grid = [list(r) for r in rows]
    if here in STARTS and tile not in STARTS:
        return rows, "The robot has to be somewhere: place it on another tile first."
    if tile in STARTS:
        for yy in range(SIZE):
            for xx in range(SIZE):
                if grid[yy][xx] in STARTS:
                    grid[yy][xx] = "."
    grid[y][x] = tile
    return ["".join(r) for r in grid], True


class SandboxRoom:
    """Looks enough like rooms.Room for the engine's view code: no par, no medals, every instruction allowed."""
    id = "sandbox"
    name = "Sandbox"
    chapter = -1
    number = 1
    allow = ALLOW
    par = None
    silver = None
    nudge = ""
    ref = None
    intro = "Nothing here is scored. Paint a room, write a list, and see what it does."

    def __init__(self, rows):
        self.rows = tuple(rows)
        self.layout = room.Layout(rows, strict=False)

    def toolbox(self):
        return dsl.allowed_ops(self.allow)
