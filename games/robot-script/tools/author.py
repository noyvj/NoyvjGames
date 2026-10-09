"""Dev-only room authoring aid: draw a room around a reference solution.

`draw(ref_text, exit_end=True, doors=(), pad=0)` expands a reference list (repeats and routine calls, no `if` or
`until`), walks it on an empty grid, and returns the rows of a room where exactly that walk works: floor where the robot
walks, parts where it grabs, sockets where it places, switches where it switches (numbered in order), a door on each
requested path tile, the exit on the last tile, and walls everywhere else. `verify(rows, ref_text)` then runs the real
interpreter on it. Used to author the routine chapter and the capstone; not loaded by the page.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dsl  # noqa: E402
import room  # noqa: E402
import run  # noqa: E402

DX = room.DX
DY = room.DY


def flatten(prog, items=None, routine="main"):
    out = []
    for stmt in (prog[routine] if items is None else items):
        if isinstance(stmt, str):
            out.append(stmt)
        elif stmt[0] == "rep":
            for _ in range(stmt[1]):
                out += flatten(prog, stmt[2], routine)
        elif stmt[0] == "call":
            out += flatten(prog, prog[stmt[1]], stmt[1])
        else:
            raise ValueError("no conditionals here")
    return out


def draw(ref_text, heading=">", exit_end=True, doors=(), extra_floor=()):
    prog = dsl.from_text(ref_text)
    acts = flatten(prog)
    x = y = 0
    d = {">": 1, "<": 3, "^": 0, "v": 2}[heading]
    floor = {(0, 0)}
    parts, sockets, switches = [], [], []
    moves = []
    carry = False
    for a in acts:
        if a == "L":
            d = (d + 3) % 4
        elif a == "R":
            d = (d + 1) % 4
        elif a == "F":
            x, y = x + DX[d], y + DY[d]
            floor.add((x, y))
            moves.append((x, y))
        elif a == "G":
            assert not carry and (x, y) not in parts, "bad grab at %s" % ((x, y),)
            parts.append((x, y))
            carry = True
        elif a == "P":
            assert carry and (x, y) not in sockets
            sockets.append((x, y))
            carry = False
        elif a == "S":
            assert (x, y) not in switches
            switches.append((x, y))
    end = (x, y)
    door_tiles = {}
    for sid, move_no in doors:
        tile = moves[move_no - 1]
        assert moves.count(tile) == 1, "door tile visited twice"
        door_tiles[tile] = sid
    xs = [p[0] for p in floor]
    ys = [p[1] for p in floor]
    for p in extra_floor:
        floor.add(p)
        xs.append(p[0])
        ys.append(p[1])
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0 + 1, max(ys) - y0 + 1
    rows = []
    for yy in range(h):
        row = ""
        for xx in range(w):
            p = (xx + x0, yy + y0)
            ch = "#"
            if p in floor:
                ch = "."
            if p in door_tiles:
                ch = "ABC"[door_tiles[p]]
            if p in parts:
                ch = "p"
            if p in sockets:
                ch = "o"
            if p in switches:
                ch = str(switches.index(p) + 1)
            if exit_end and p == end and p != (0, 0):
                ch = "E"
            if p == (0, 0):
                ch = heading
            row += ch
        rows.append(row)
    return rows


def verify(rows, ref_text):
    layout = room.Layout(rows)
    result = run.run(layout, dsl.from_text(ref_text))
    return result.status, result.message


if __name__ == "__main__":
    text = sys.argv[1].replace("\\n", "\n")
    rows = draw(text)
    print("\n".join(rows))
    print(verify(rows, text))
