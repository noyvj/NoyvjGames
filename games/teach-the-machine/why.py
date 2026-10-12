"""Teach the Machine -- the Why panel: the path a wrong answer took, and which kind of mistake it was.

Every wrong answer on the unseen table gets EXACTLY ONE of five categories, by explicit rules checked in this order. Each rule is a
counterfactual a person can follow ("train again with this one change: does Pip now get THIS case right?"), so the category is never a
guess and the Why panel's path is the very path the learner walked (learner.trace):

  1 mislabelled   the lesson has training examples flagged as carrying the wrong label, and training without them gets this case right
  2 missing       some feature the lesson really needs is switched off, and switching the needed ones on gets this case right
  3 shortcut      a switched-on feature the lesson flags as a shortcut, and switching those off gets this case right
  4 distracting   Pip is looking at features the lesson does not need (and at least one it does), and looking only at the needed ones
                  gets this case right
  5 too_few       none of the above: the right things, no flaw in the data, and the training table simply left a gap near the line
                  between the bins, so Pip drew the line in the wrong place

Shelves 1 to 3 have no shortcut and no mislabelled lessons (those come with shelves 4 and 5), but the rules are all here and tested on
small made-up lessons.
"""

import learner
import lessonkit

CATEGORIES = (
    {"id": "missing", "name": "Missing feature", "about": "Pip was not looking at something that mattered, so it could not tell the cases apart.",
     "example": "Pip is asked which doors are safe but can only see the handle shape. The heat decides it, and Pip never saw the heat, so it guesses from handles."},
    {"id": "too_few", "name": "Too few examples", "about": "Pip looked at the right things, but its training table left a gap near the line between two bins, so the line landed in the wrong place.",
     "example": "The training crates glow 4 or 7, never 5 or 6. Pip draws its line at 6. A crate that glows 5 falls on the wrong side."},
    {"id": "distracting", "name": "Distracting feature", "about": "Pip also looked at something with nothing to do with the answer, and in a small training table it happened to line up.",
     "example": "Door numbers have nothing to do with heat. But three of the hot doors in the training table had numbers over 70, so Pip started asking about door numbers."},
    {"id": "shortcut", "name": "Shortcut", "about": "A feature matched the answer in the training table only by habit, and Pip leaned on it instead of the real reason.",
     "example": "Every ripe crate in training came off the east dock. Pip learned 'east dock means ripe', which stops being true as soon as another dock sends a ripe crate."},
    {"id": "mislabelled", "name": "Mislabelled example", "about": "One training example carried the wrong label, and Pip believed it.",
     "example": "A cracked pipe was filed as 'Sound' in the training table. Pip trusted the label and learned that cracked pipes ring true."},
)
CATEGORY_IDS = tuple(c["id"] for c in CATEGORIES)
BY_ID = {c["id"]: c for c in CATEGORIES}
MAX_NEIGHBOURS = 3

_cache = {}


def _tree(lesson, on, drop=False):
    key = (lesson["id"], tuple(lessonkit.order_set(lesson, on)), drop)
    if key not in _cache:
        if len(_cache) > 4000:
            _cache.clear()
        _cache[key] = lessonkit.fit(lesson, set(on), drop_flagged=drop)
    return _cache[key]


def _right(lesson, on, case, drop=False):
    return learner.predict(_tree(lesson, on, drop), case) == case["label"]


def checks(lesson, on, case):
    """The four counterfactual rules in order: [(category id, True/False)]. The fifth, too_few, is whatever none of these catch."""
    on = set(on)
    needs = set(lesson["needs"])
    shortcuts = set(lesson["shortcuts"])
    return [
        ("mislabelled", bool(lesson["mislabelled"]) and _right(lesson, on, case, drop=True)),
        ("missing", bool(needs - on) and _right(lesson, on | needs, case)),
        ("shortcut", bool(on & shortcuts) and _right(lesson, on - shortcuts, case)),
        ("distracting", bool(on - needs) and bool(on & needs) and _right(lesson, on & needs, case)),
    ]


def categorise(lesson, on, case):
    """The one category of a wrong answer."""
    for cid, hit in checks(lesson, on, case):
        if hit:
            return cid
    return "too_few"


def _neighbours(lesson, on, tree, case, key):
    same = []
    for t in lesson["train_cases"]:
        steps, _ = learner.trace(tree, lesson["by_id"], t)
        if learner.leaf_key(steps) == key:
            same.append((learner.distance(lesson["features"], on, case, t), t))
    same.sort(key=lambda pair: pair[0])
    return [t for _, t in same[:MAX_NEIGHBOURS]]


def chips(lesson, on, case):
    return [{"feature": f["id"], "label": f["label"], "text": learner.chip_text(f, case["v"][f["id"]]), "on": f["id"] in on} for f in lesson["features"]]


def _because(lesson, on, category, steps, case):
    noun = lesson["noun"].lower()
    by_id = lesson["by_id"]
    looked = [by_id[f]["label"] for f in lesson["fids"] if f in on]
    if category == "mislabelled":
        return "One of the training %ss carried the wrong label and Pip believed it. Train again without it and Pip gets this one right." % noun
    if category == "missing":
        return "Pip could only look at %s. Something else about this %s mattered, and Pip could not see it." % (", ".join(looked) or "nothing", noun)
    if category == "shortcut":
        names = [by_id[f]["label"] for f in lesson["fids"] if f in on and f in lesson["shortcuts"]]
        return "%s lined up with the answer in the training table, and Pip leaned on it. It does not hold for this %s." % (" and ".join(names), noun)
    if category == "distracting":
        extra = [by_id[f]["label"] for f in lesson["fids"] if f in on and f not in lesson["needs"]]
        return ("Pip was also looking at %s, which %s nothing to do with this job. Looking only at what matters gives a tree that gets this "
                "%s right." % (", ".join(extra), "has" if len(extra) == 1 else "have", noun))
    return ("Pip was looking at the right things, but the training table left a gap near the line between the bins. This %s fell in the "
            "gap, and Pip's line was in the wrong place." % noun)


def explain(lesson, on, tree, case):
    """Everything the Why panel shows for one wrong answer."""
    by_id = lesson["by_id"]
    steps, leaf = learner.trace(tree, by_id, case)
    category = categorise(lesson, on, case)
    bins = lesson["bins"]
    neighbours = _neighbours(lesson, on, tree, case, learner.leaf_key(steps))
    decisive = None
    if steps:
        last = steps[-1]
        decisive = {"feature": by_id[last["test"]["f"]]["label"], "question": last["question"], "answer": last["answer"]}
    return {
        "case": case["id"], "name": case["name"], "chips": chips(lesson, on, case),
        "pip": bins[leaf["label"]], "truth": bins[case["label"]],
        "steps": [{"question": s["question"], "value": s["value"], "answer": s["answer"]} for s in steps],
        "decisive": decisive,
        "group": {"n": leaf["n"], "counts": [{"bin": bins[i], "n": n} for i, n in enumerate(leaf["counts"])]},
        "neighbours": [{"name": t["name"], "chips": chips(lesson, on, t), "label": bins[t["label"]]} for t in neighbours],
        "category": category, "category_name": BY_ID[category]["name"],
        "because": _because(lesson, on, category, steps, case),
        "looking_at": [by_id[f]["label"] for f in lesson["fids"] if f in on],
    }
