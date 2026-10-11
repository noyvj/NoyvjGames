"""Mirror Lab -- turns the pictures in tools/specs.py into the frozen bench files and PROVES each bench on the way.

    python3 tools/build_benches.py [chapter]      (default: every chapter)

For each bench it strips the pieces out of the picture, solves the bench with tools/solve.py and checks:
  - the drawn solution is one of the solutions found;
  - the tray is not padded: the fewest pieces any solution uses equals the tray, and the drawn solution uses exactly that;
  - the empty bench is not already a solution;
and records how many distinct solutions there are (1 means a single answer). Then it writes `benches_ch<N>.py`.
Do not edit those files by hand; change the picture and run this again, then run the tests.
"""

import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
for path in (GAME_DIR, GAME_DIR / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import optics  # noqa: E402
import solve  # noqa: E402
import specs  # noqa: E402

PICTURE_PIECES = {"m": ("mirror", 0), "n": ("mirror", 1), "y": ("splitter", 0), "p": ("prism", 0), "q": ("prism", 1),
                  "f": ("filter_s", 0), "g": ("filter_l", 0), "b": ("absorber", 0)}


def parse_picture(pic):
    width = max(len(row) for row in pic)
    pic = [row.ljust(width, ".") for row in pic]
    rows, solution, tray = [], [], {}
    for r, row in enumerate(pic):
        out = ""
        for c, ch in enumerate(row):
            if ch in PICTURE_PIECES:
                piece, state = PICTURE_PIECES[ch]
                solution.append((r, c, piece, state))
                tray[piece] = tray.get(piece, 0) + 1
                out += "o"
            else:
                out += ch
        rows.append(out)
    return rows, tray, tuple(sorted(solution))


def prove(spec):
    rows, tray, drawn = parse_picture(spec["pic"])
    board = optics.Board(rows)
    found = solve.solve(board, tray)
    name = spec["id"]
    assert drawn in found, "%s: the drawn solution is not a solution" % name
    fewest = min(len(s) for s in found)
    assert fewest == len(drawn) == sum(tray.values()), "%s: the tray is padded (fewest %d, drawn %d, tray %d)" % (name, fewest, len(drawn), sum(tray.values()))
    assert not optics.trace(board, {}).ok, "%s: the empty bench is already solved" % name
    return {"id": name, "name": spec["name"], "rows": rows, "tray": dict(sorted(tray.items())), "solution": list(drawn), "par": fewest,
            "count": len(found), "line": spec["line"]}


def write(chapter, benches):
    path = GAME_DIR / ("benches_ch%d.py" % chapter)
    lines = ['"""Mirror Lab -- chapter %d benches. FROZEN DATA written by tools/build_benches.py from tools/specs.py: do not edit by hand."""' % chapter, "",
             "BENCHES = ["]
    for b in benches:
        lines.append("    {")
        lines.append('        "id": %r, "name": %r,' % (b["id"], b["name"]))
        lines.append('        "rows": [')
        for row in b["rows"]:
            lines.append("            %r," % row)
        lines.append("        ],")
        lines.append('        "tray": %r,' % (b["tray"],))
        lines.append('        "solution": %r,' % (b["solution"],))
        lines.append('        "par": %d, "count": %d,' % (b["par"], b["count"]))
        lines.append('        "line": %r,' % b["line"])
        lines.append("    },")
    lines.append("]")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    wanted = int(sys.argv[1]) if len(sys.argv) > 1 else None
    for chapter, items in specs.CHAPTERS.items():
        if wanted is not None and chapter != wanted:
            continue
        built = []
        for spec in items:
            b = prove(spec)
            print("%-6s %-18s %dx%d  tray %-40s par %d  solutions %d" % (b["id"], b["name"], len(b["rows"][0]), len(b["rows"]), b["tray"], b["par"], b["count"]))
            built.append(b)
        print("wrote", write(chapter, built))
