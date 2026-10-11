"""Dev tool: prove every authored picture. Run by hand after adding or changing a picture:

    python3 tools/check_pictures.py            # every picture
    python3 tools/check_pictures.py robots     # one gallery (by id)
    python3 tools/check_pictures.py --draw     # also draw each picture

For each picture it prints the clue counts, how many pictures fit the clues (the exhaustive counter, must be 1), whether line
logic alone finishes it (must be yes), how many sweeps of line logic that takes, and whether the second, independent counter
agrees. A picture that fails any of those must be redrawn: a person should never have to guess.
`suggest_fixes(rows)` lists the one- and two-cell edits of a failing draft that DO pass, to help a redraw.
"""

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import nonogram  # noqa: E402
import pictures  # noqa: E402


def passes(rows):
    proof = nonogram.prove(rows)
    return proof["line_solved"] and proof["count"] == 1


def suggest_fixes(rows, max_cells=2):
    """Yield (cells flipped, new rows) for the smallest edits of `rows` that make it uniquely line-solvable."""
    height, width = len(rows), len(rows[0])
    cells = [(r, c) for r in range(height) for c in range(width)]
    for k in range(1, max_cells + 1):
        found = False
        for combo in itertools.combinations(cells, k):
            grid = [list(row) for row in rows]
            for r, c in combo:
                grid[r][c] = "." if grid[r][c] == "#" else "#"
            candidate = ["".join(row) for row in grid]
            if passes(candidate):
                found = True
                yield combo, candidate
        if found:
            return


def main(argv):
    draw = "--draw" in argv
    wanted = [a for a in argv if not a.startswith("--")]
    bad = 0
    for gallery in pictures.GALLERIES:
        if wanted and gallery["id"] not in wanted:
            continue
        print("== %s ==" % gallery["name"])
        for p in gallery["pictures"]:
            proof = nonogram.prove(p.rows, cross_check=True)
            ok = proof["line_solved"] and proof["count"] == 1 and proof["count_by_rows"] == 1
            bad += 0 if ok else 1
            print("%-10s %-5s count=%d by-rows=%d line-logic=%s sweeps=%d  %s" % (
                p.id, p.size, proof["count"], proof["count_by_rows"], "yes" if proof["line_solved"] else "NO", proof["sweeps"], "ok" if ok else "FAIL"))
            if draw:
                for row in p.rows:
                    print("    " + row.replace("#", "##").replace(".", "  "))
    print("all pictures proved" if not bad else "%d picture(s) FAILED" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
