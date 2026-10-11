"""Zero-G Shift -- finds and freezes the 48 bays.

For each deck it searches seeded candidates (tools/gen.py), keeps the fair ones (solvable, par at least 4, at most 3
shortest solutions, the deck's new part really needed), picks one for each par target and writes `bays_<deck>.py` with
the rows, the par and one stored shortest line. Names and notes live in tools/texts.py. Run from the game folder:

    python3 tools/build_bays.py [deck-number ...]

Everything is deterministic (fixed seeds), so running it again gives the same files.
"""

import os
import sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import gen        # noqa: E402
import rules      # noqa: E402
import solver     # noqa: E402
from texts import DECKS   # noqa: E402


def par_of(spec):
    try:
        bay = rules.Bay(spec)
    except rules.BayError:
        return None
    a = solver.Analysis(bay, cap=30000)
    return a.par if a.complete else None


def without(spec, chars, door=False):
    out = dict(spec)
    out["rows"] = [r.translate(str.maketrans(chars, "." * len(chars))) for r in spec["rows"]]
    if door:
        out.pop("door", None)
    return out


def swapped_pads(spec):
    out = dict(spec)
    out["rows"] = [r.translate(str.maketrans("AB", "BA")) for r in spec["rows"]]
    if spec.get("door") in ("A", "B"):
        out["door"] = "B" if spec["door"] == "A" else "A"
    return out


def needs(feature):
    """A test that the deck's new part really matters: take it away and the par changes (or the bay cannot be solved)."""
    def check(bay, a):
        spec = {"id": bay.id, "rows": list(bay.rows)}
        if bay.door:
            spec["door"] = bay.door
        if feature == "hatch":
            return "h" in "".join(bay.rows) and par_of(without(spec, "h")) != a.par
        if feature == "bumper":
            return "b" in "".join(bay.rows) and par_of(without(spec, "b")) != a.par
        if feature == "door":
            return bool(bay.door) and par_of(without(spec, "=", door=True)) != a.par
        if feature == "pads":
            return len(bay.kinds_in_play) >= 2 and par_of(swapped_pads(spec)) != a.par
        return True
    return check


def search_profile(job):
    deck_no, index, params, feature, seeds, cap = job
    out = []
    check = needs(feature)
    for seed, bay, a in gen.search(params, range(*seeds), cap=cap, need=check):
        out.append((a.par, a.size, seed, index, bay.rows, bay.door, a.line_from(bay.start)))
    return out


def build(deck_no):
    deck = DECKS[deck_no - 1]
    jobs = []
    for index, prof in enumerate(deck["profiles"]):
        for lo in range(0, prof["seeds"], 2000):
            jobs.append((deck_no, index, prof["params"], prof.get("feature"), (lo, min(prof["seeds"], lo + 2000)), prof.get("cap", 30000)))
    with Pool(3) as pool:
        found = [c for part in pool.map(search_profile, jobs) for c in part]
    print("deck %d: %d candidates" % (deck_no, len(found)))
    chosen, used = [], set()
    for target in deck["pars"]:
        best = None
        for cand in found:
            par, size, seed, index, rows, door, line = cand
            if cand[4:6] in used or (rows, door) in used:
                continue
            key = (abs(par - target), -min(size, 2000), seed)
            if best is None or key < best[0]:
                best = (key, cand)
        if best is None:
            raise SystemExit("deck %d: nothing for par %d" % (deck_no, target))
        chosen.append(best[1])
        used.add((best[1][4], best[1][5]))
    return chosen


def write(deck_no, chosen):
    deck = DECKS[deck_no - 1]
    lines = ['"""Zero-G Shift -- deck %d, %s: %d bays found and frozen by tools/build_bays.py (do not edit by hand)."""' % (deck_no, deck["name"], len(chosen)), "", "BAYS = ["]
    for i, (par, size, seed, index, rows, door, line) in enumerate(chosen):
        ident = deck["bays"][i][0]
        name = deck["bays"][i][1]
        lines.append("    {")
        lines.append('        "id": %r, "name": %r,' % (ident, name))
        lines.append('        "rows": [')
        for r in rows:
            lines.append("            %r," % r)
        lines.append("        ],")
        if door:
            lines.append('        "door": %r,' % door)
        lines.append('        "par": %d, "line": %r,' % (par, line))
        lines.append("    },")
    lines.append("]")
    path = os.path.join(ROOT, "bays_%s.py" % deck["module"])
    with open(path, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    print("wrote", path, [c[0] for c in chosen], [c[1] for c in chosen])


if __name__ == "__main__":
    wanted = [int(a) for a in sys.argv[1:]] or list(range(1, len(DECKS) + 1))
    for n in wanted:
        write(n, build(n))
