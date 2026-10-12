"""Teach the Machine -- writes lessons_s1.py ... lessons_s3.py from tools/lesson_specs.py (dev tool; GENERATED files, do not edit them).

For each spec the builder draws the training table and the unseen table with a seeded generator (a small linear congruential one of its
own: the game itself has no random source) and keeps the FIRST seed whose tables pass the proof for the lesson's kind (see lesson_specs.py):
the class balance is sensible, the needed features reach the target, the stored best set is exactly the needed features, and the
kind-specific "choosing matters" check holds. A lesson that cannot be proved with any seed is an error, never shipped.

    python3 tools/build_lessons.py            # write the files
    python3 tools/build_lessons.py --check    # rebuild in memory and compare with the files on disk
"""

import pprint
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
for p in (GAME_DIR, GAME_DIR / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import learner  # noqa: E402
import lessonkit  # noqa: E402
import lesson_specs  # noqa: E402
import subsets  # noqa: E402

MAX_SEEDS = 6000


class Lcg:
    def __init__(self, seed):
        self.x = (seed * 2654435761 + 12345) % 2147483648

    def below(self, n):
        self.x = (self.x * 1103515245 + 12345) % 2147483648
        return (self.x >> 8) % n


def draw_value(rng, f):
    if f["kind"] == "yes_no":
        return 1 if rng.below(100) < f.get("p", 50) else 0
    if f["kind"] == "number":
        return f["lo"] + rng.below(f["hi"] - f["lo"] + 1)
    return f["values"][rng.below(len(f["values"]))]


def draw_tables(spec, seed):
    rng = Lcg(seed)
    feats = spec["features"]
    rows = []
    for i in range(spec["n_train"] + spec["n_test"]):
        v = {f["id"]: draw_value(rng, f) for f in feats}
        rows.append(["%s %d" % (spec["noun"], i + 1), [v[f["id"]] for f in feats], spec["rule"](v)])
    return rows[:spec["n_train"]], rows[spec["n_train"]:]


def public_features(spec):
    out = []
    for f in spec["features"]:
        g = {k: v for k, v in f.items() if k != "p"}
        out.append(g)
    return out


def raw_lesson(spec, train, test, seed):
    return {"id": spec["id"], "kind": spec["kind"], "title": spec["title"], "task": spec["task"], "noun": spec["noun"], "bins": list(spec["bins"]),
            "features": public_features(spec), "train": train, "test": test, "target": spec["target"],
            "start": list(spec["start"]) if spec["start"] else [f["id"] for f in spec["features"]], "gentle": spec["gentle"],
            "needs": list(spec["needs"]), "shortcuts": [], "mislabelled": [], "learned": spec["learned"], "seed": seed}


def balanced(rows, n_bins):
    counts = [0] * n_bins
    for _, _, label in rows:
        counts[label] += 1
    floor = 0.25 if n_bins == 2 else 0.15
    return all(c >= floor * len(rows) for c in counts)


def proof_problem(lesson, scores):
    """None if the lesson passes the proof for its kind, otherwise a short reason."""
    fids = lesson["fids"]
    need = lesson["need"]
    needs = tuple(f for f in fids if f in lesson["needs"])
    best, best_score = subsets.best_set(lesson, scores)
    if best != needs:
        return "best set %s is not the needed set %s" % (best, needs)
    if scores[needs] < need:
        return "needed set scores %d < %d" % (scores[needs], need)
    start = tuple(f for f in fids if f in lesson["start"])
    if lesson["kind"] == "basic":
        if lesson["gentle"] and scores[tuple(fids)] < need:
            return "gentle lesson: all switches do not clear"
        if not lesson["gentle"] and scores[start] >= need:
            return "the starting switches already clear it"
    elif lesson["kind"] == "two":
        if any(scores[(f,)] >= need for f in fids):
            return "one feature alone clears it"
        if scores[start] >= need:
            return "the starting switches already clear it"
    elif lesson["kind"] == "distract":
        if tuple(lesson["start"]) != tuple(fids):
            return "a distraction lesson must start with every switch on"
        if scores[tuple(fids)] >= need:
            return "all switches on still clear it (the noise does not bite)"
        if any(scores[tuple(f for f in fids if f != x)] >= need for x in needs) is False and False:
            return None
    return None


def build_one(spec, shelf, number):
    last = None
    for seed in range(1, MAX_SEEDS + 1):
        train, test = draw_tables(spec, seed)
        if not (balanced(train, len(spec["bins"])) and balanced(test, len(spec["bins"]))):
            continue
        raw = raw_lesson(spec, train, test, seed)
        lesson = lessonkit.prepare(raw, shelf, number)
        scores = subsets.all_scores(lesson)
        last = proof_problem(lesson, scores)
        if last is None:
            best, best_score = subsets.best_set(lesson, scores)
            tree = lessonkit.fit(lesson, set(best))
            by_id = lesson["by_id"]
            raw["best"] = list(best)
            raw["best_score"] = best_score
            raw["golden"] = [line["text"] for line in learner.tree_lines(tree, by_id, lesson["bins"])]
            return raw
    raise SystemExit("could not prove lesson %s in %d seeds (last problem: %s)" % (spec["id"], MAX_SEEDS, last))


def render(shelf_index, raws):
    lines = ['"""GENERATED by tools/build_lessons.py from tools/lesson_specs.py -- do not edit by hand."""', "", "LESSONS = ["]
    for raw in raws:
        lines.append("    " + pprint.pformat(raw, width=150, sort_dicts=False, compact=True).replace("\n", "\n    ") + ",")
    lines.append("]")
    return "\n".join(lines) + "\n"


def build_all():
    out = {}
    for shelf in sorted({s["shelf"] for s in lesson_specs.SPECS}):
        specs = [s for s in lesson_specs.SPECS if s["shelf"] == shelf]
        raws = [build_one(spec, shelf, i + 1) for i, spec in enumerate(specs)]
        out["lessons_s%d.py" % (shelf + 1)] = render(shelf, raws)
    return out


def main():
    files = build_all()
    check = "--check" in sys.argv
    for name, text in files.items():
        path = GAME_DIR / name
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                raise SystemExit("%s is out of date" % name)
        else:
            path.write_text(text, encoding="utf-8")
            print("wrote", name)
    if check:
        print("all lesson files are current")


if __name__ == "__main__":
    main()
